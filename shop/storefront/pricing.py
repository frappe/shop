"""Storefront prices: the store's price list for guests; for a signed-in customer their own price
list with ERPNext's pricing rules applied. format_amount is the store-currency amount for staff
screens, display_amount what shoppers see (optionally with tax, or in another currency)."""

from urllib.parse import unquote

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import flt, fmt_money, getdate, nowdate

CURRENCY_COOKIE = "shop_currency"


def get_prices(item_codes: list[str], qtys: dict | None = None, customer: str | None = "session") -> dict:
	if not item_codes:
		return {}
	retail = store_prices(item_codes)
	if customer == "session":
		customer = session_customer()
	if not customer:
		# a guest sees the Pricing Rules everyone gets (the store's customer group), as checkout charges
		return guest_prices(retail, qtys or {})
	price_list = customer_price_list(customer)
	prices = {}
	for code in item_codes:
		qty = flt((qtys or {}).get(code)) or 1
		rate = customer_rate(code, customer, price_list, qty)
		if rate is None:
			# a customer's own price list is the one their orders use: what isn't on it isn't for sale to them
			if code in retail and price_list == frappe.get_cached_doc("Shop Settings").price_list:
				prices[code] = retail[code]
			continue
		entry = {"rate": rate, "formatted": format_amount(rate), **display_fields(rate, code)}
		base = retail.get(code, {}).get("rate")
		if base and rate < flt(base) - 0.004:
			entry.update(retail=base, formatted_retail=format_amount(base))
		prices[code] = entry
	return prices


def store_prices(item_codes: list[str]) -> dict:
	"""The store's price list rates that apply to anyone today (not a customer's own price)."""
	settings = frappe.get_cached_doc("Shop Settings")
	today = getdate()
	rates = {}
	for row in frappe.get_all(
		"Item Price",
		filters={
			"item_code": ["in", item_codes],
			"price_list": settings.price_list,
			"customer": ["is", "not set"],
		},
		fields=["item_code", "price_list_rate", "valid_from", "valid_upto"],
		order_by="valid_from desc",
	):
		if row.item_code in rates:
			continue
		if (row.valid_from and getdate(row.valid_from) > today) or (
			row.valid_upto and getdate(row.valid_upto) < today
		):
			continue
		rates[row.item_code] = row.price_list_rate
	return {
		code: {"rate": rate, "formatted": format_amount(rate), **display_fields(rate, code)}
		for code, rate in rates.items()
	}


def display_fields(rate: float, item_code: str | None = None) -> dict:
	tax_rate = item_tax_rate(item_code)
	return {
		"display": display_price(rate, tax_rate),
		"display_excl": display_price_without_tax(rate, tax_rate),
	}


def get_price(item_code: str) -> dict | None:
	return get_prices([item_code]).get(item_code)


def format_amount(amount: float) -> str:
	settings = frappe.get_cached_doc("Shop Settings")
	return fmt_money(amount, currency=settings.currency)


def document_amount(amount: float, currency: str) -> str:
	"""An amount in a document's own currency, with the code when that isn't the store's."""
	formatted = fmt_money(amount, currency=currency)
	return formatted if currency == store_currency() else f"{formatted} {currency}"


def store_amount(amount: float) -> str:
	"""An exact store-currency amount, with the currency code when the store shows several."""
	return with_code(format_amount(amount), store_currency())


def with_code(formatted: str, currency: str) -> str:
	return f"{formatted} {currency}" if len(display_currencies()) > 1 else formatted


def store_currency() -> str:
	return frappe.get_cached_doc("Shop Settings").currency


def display_currencies() -> list[str]:
	"""The store currency, then the other currencies the store can be paid in."""
	from shop.storefront import totals

	cache = request_cache("shop_display_currencies")
	if "all" not in cache:
		cache["all"] = list(dict.fromkeys([store_currency(), *totals.bank_currencies()]))
	return cache["all"]


def chosen_currency() -> str | None:
	"""The currency the shopper picked, else their Billing Currency, when the store offers it."""
	options = display_currencies()
	request = getattr(frappe.local, "request", None)
	picked = request.cookies.get(CURRENCY_COOKIE) if request is not None else None
	if picked in options:
		return picked
	customer = session_customer()
	if customer:
		billing = frappe.get_cached_value("Customer", customer, "default_currency")
		if billing in options:
			return billing
	return None


def display_currency() -> str:
	return chosen_currency() or store_currency()


def display_rate(currency: str) -> float | None:
	"""Store currency to this currency at ERPNext's rate, once per request; None when unknown."""
	cache = request_cache("shop_display_rates")
	if currency not in cache:
		from shop.storefront import totals
		from shop.storefront.checkout import elevated

		try:
			# ERPNext lets only staff fetch a day's rate from its provider (it then caches it).
			# Checkout does the same; at most the store's few bank currencies are fetched, once a day.
			with elevated():
				cache[currency] = totals.exchange_rate(store_currency(), currency)
		except Exception:
			frappe.clear_messages()
			cache[currency] = None
	return cache[currency]


def domestic_taxes() -> list:
	"""The rows of the store's own tax template, read once per request.

	Read directly: ERPNext's template lookup is for staff, and these pages are public."""
	cache = request_cache("shop_domestic_taxes")
	template = frappe.get_cached_doc("Shop Settings").tax_template or ""
	if template not in cache:
		cache[template] = (
			frappe.get_all(
				"Sales Taxes and Charges",
				filters={
					"parent": template,
					"parenttype": "Sales Taxes and Charges Template",
					"charge_type": "On Net Total",
				},
				fields=["account_head", "rate", "description"],
				order_by="idx",
			)
			if template
			else []
		)
	return cache[template]


def domestic_tax_rate() -> float:
	"""Percent of the store's own tax, whether its prices include it or not."""
	return sum(flt(row.rate) for row in domestic_taxes())


def item_tax_rate(item_code: str | None) -> float:
	"""Percent of the store's own tax on an item: the Item Tax Template ERPNext picks for it (from the
	item or its Item Group) changes the rate of the taxes it names."""
	if not item_code:
		return domestic_tax_rate()
	settings = frappe.get_cached_doc("Shop Settings")
	return shared("item_tax_rates", (settings.tax_template, item_code), lambda: work_out_tax_rate(item_code))


def work_out_tax_rate(item_code: str) -> float:
	from erpnext.stock.get_item_details import NOT_APPLICABLE_TAX, get_item_tax_map, get_item_tax_template

	settings = frappe.get_cached_doc("Shop Settings")
	taxes = domestic_taxes()
	ctx = {
		"company": settings.company,
		"transaction_date": nowdate(),
		"tax_category": settings.tax_template
		and frappe.get_cached_value(
			"Sales Taxes and Charges Template", settings.tax_template, "tax_category"
		),
	}
	template = get_item_tax_template(ctx, frappe.get_cached_doc("Item", item_code))
	rates = get_item_tax_map(
		doc={"company": settings.company, "taxes": [dict(row) for row in taxes]},
		tax_template=template,
		as_json=False,
	)
	return sum(
		flt(rates.get(row.account_head)) for row in taxes if rates.get(row.account_head) != NOT_APPLICABLE_TAX
	)


def tax_name() -> str:
	"""The short name of the store's tax, from its tax template."""
	from shop.storefront.totals import tax_name as short_name

	rows = domestic_taxes()
	return (short_name(rows[0].description) if rows else "") or _("tax")


def shows_tax() -> bool:
	"""Whether prices are shown with the store's tax, the price without tax under them."""
	return bool(frappe.get_cached_doc("Shop Settings").get("show_prices_with_tax") and domestic_tax_rate())


def with_and_without_tax(amount: float, tax_rate: float | None = None) -> tuple[float, float]:
	"""A price-list amount as (including tax, excluding tax) at the store's own tax rate, or at the
	item's (item_tax_rate)."""
	factor = 1 + (domestic_tax_rate() if tax_rate is None else tax_rate) / 100
	if frappe.get_cached_doc("Shop Settings").prices_include_tax:
		return flt(amount), flt(amount) / factor
	return flt(amount) * factor, flt(amount)


def shown_amount(amount: float, tax_rate: float | None = None) -> float:
	"""A price-list amount as the store shows it in its own currency: with tax when it shows prices
	with tax."""
	return with_and_without_tax(amount, tax_rate)[0] if shows_tax() else flt(amount)


def shows_store_currency() -> bool:
	currency = display_currency()
	return currency == store_currency() or not display_rate(currency)


def display_amount(amount: float, tax_rate: float | None = None) -> str:
	"""A price-list amount as the shopper sees it: in the store currency as the price list has it,
	or with tax when the store shows prices with tax. In another currency the buyer pays no local
	tax unless the store shows other currencies with tax: converted at ERPNext's rate and marked
	approximate."""
	including, excluding = with_and_without_tax(amount, tax_rate)
	if shows_store_currency():
		shown = including if shows_tax() else flt(amount)
		return with_code(fmt_money(flt(shown, 2), currency=store_currency()), store_currency())
	currency = display_currency()
	shown = including if other_currencies_with_tax() else excluding
	return f"≈ {fmt_money(shown * display_rate(currency), currency=currency)} {currency}"


def other_currencies_with_tax() -> bool:
	return bool(frappe.get_cached_doc("Shop Settings").get("other_currencies_with_tax"))


def display_price(amount: float, tax_rate: float | None = None) -> str:
	"""A product's headline price: display_amount, saying whether it includes tax."""
	shown = display_amount(amount, tax_rate)
	if tax_rate == 0 or not domestic_tax_rate():
		return shown
	if shows_store_currency():
		return _("{0} incl. {1}").format(shown, tax_name()) if shows_tax() else shown
	if other_currencies_with_tax():
		return _("{0} incl. {1}").format(shown, tax_name())
	return _("{0} excl. {1}").format(shown, tax_name())


def display_price_without_tax(amount: float, tax_rate: float | None = None) -> str | None:
	"""The line under a headline price shown with tax: the price without it."""
	if not shows_store_currency() or not shows_tax() or tax_rate == 0:
		return None
	excluding = with_and_without_tax(amount, tax_rate)[1]
	return _("{0} excl. {1}").format(
		with_code(fmt_money(flt(excluding, 2), currency=store_currency()), store_currency()), tax_name()
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60)
def set_currency(currency: str) -> str:
	"""The shopper picks the currency prices are shown in, kept in their browser. A customer's
	Billing Currency in ERPNext is only the starting choice; picking one here doesn't change it."""
	if currency not in display_currencies():
		frappe.throw(_("Prices can't be shown in {0}").format(currency))
	frappe.local.cookie_manager.set_cookie(
		CURRENCY_COOKIE, currency, max_age=60 * 60 * 24 * 365, samesite="Lax"
	)
	return currency


def currency_picker_html() -> str:
	"""A <select> of the currencies prices can be shown in; storefront.js saves the choice."""
	options = display_currencies()
	if len(options) < 2:
		return ""
	current = display_currency()
	esc = frappe.utils.escape_html
	items = "".join(
		f'<option value="{esc(code)}"{" selected" if code == current else ""}>{esc(code)}</option>'
		for code in options
	)
	return (
		f'<label class="currency-picker"><span class="visually-hidden">{esc(_("Currency"))}</span>'
		f'<select data-shop="currency-picker" aria-label="{esc(_("Show prices in"))}">{items}</select></label>'
	)


BUYING_FOR_COOKIE = "shop_buying_for"


def session_customer() -> str | None:
	"""The customer the signed-in shopper buys for: the one they chose, when their login is linked
	to several and the choice is still theirs, else the first."""
	user = shopper()
	if user in ("Guest", None, "Administrator"):
		return None
	cache = request_cache("shop_session_customer")
	if user not in cache:
		from shop.storefront.orders import session_customers

		customers = session_customers(user)
		request = getattr(frappe.local, "request", None)
		chosen = unquote(request.cookies.get(BUYING_FOR_COOKIE) or "") if request else None
		cache[user] = chosen if chosen in customers else (customers[0] if customers else None)
	return cache[user]


@frappe.whitelist(methods=["POST"])
def set_buying_for(customer: str) -> str:
	"""Choose which of the customers the signed-in login is linked to it buys for."""
	from shop.storefront.orders import session_customers

	if customer not in session_customers():
		raise frappe.PermissionError(_("You can't buy for this account"))
	frappe.local.cookie_manager.set_cookie(
		BUYING_FOR_COOKIE, customer, max_age=60 * 60 * 24 * 365, samesite="Lax", httponly=True
	)
	request_cache("shop_session_customer")[shopper()] = customer
	return customer


def buying_for_html() -> str:
	"""Who the signed-in shopper buys for, with a <select> to change it when they can buy for more
	than one customer; storefront.js saves the choice."""
	from shop.storefront.orders import session_customers

	customers = session_customers()
	current = session_customer()
	if not current:
		return ""
	esc = frappe.utils.escape_html
	names = {
		row.name: row.customer_name
		for row in frappe.get_all(
			"Customer", filters={"name": ["in", customers]}, fields=["name", "customer_name"]
		)
	}
	label = esc(_("Buying for"))
	if len(customers) < 2:
		if frappe.db.get_value("Customer", current, "customer_type") != "Company":
			return ""
		return f'<p class="buying-for">{label} <strong>{esc(names.get(current) or current)}</strong></p>'
	options = "".join(
		f'<option value="{esc(name)}"{" selected" if name == current else ""}>{esc(names.get(name) or name)}</option>'
		for name in customers
	)
	return (
		f'<label class="buying-for"><span>{label}</span> '
		f'<select data-shop="buying-for" aria-label="{label}">{options}</select></label>'
	)


def shopper() -> str | None:
	"""The signed-in shopper, also while checkout runs with raised permissions."""
	return getattr(frappe.local, "shop_shopper", None) or frappe.session.user


def customer_price_list(customer: str) -> str:
	settings = frappe.get_cached_doc("Shop Settings")
	own, group = frappe.get_cached_value("Customer", customer, ["default_price_list", "customer_group"])
	price_list = own or (group and frappe.get_cached_value("Customer Group", group, "default_price_list"))
	if price_list and frappe.get_cached_value("Price List", price_list, "currency") == settings.currency:
		return price_list
	return settings.price_list


def guest_prices(retail: dict, qtys: dict) -> dict:
	"""A guest's cart prices: the store's prices with the Pricing Rules for the default Customer Group
	(quantity breaks), as checkout prices the order."""
	group = frappe.db.get_single_value("Selling Settings", "customer_group")
	price_list = frappe.get_cached_doc("Shop Settings").price_list
	prices = {}
	for code, entry in retail.items():
		rate = customer_rate(code, None, price_list, flt(qtys.get(code)) or 1, customer_group=group)
		if rate is None or rate >= flt(entry["rate"]) - 0.004:
			prices[code] = entry
			continue
		prices[code] = {
			"rate": rate,
			"formatted": format_amount(rate),
			**display_fields(rate, code),
			"retail": entry["rate"],
			"formatted_retail": format_amount(entry["rate"]),
		}
	return prices


def customer_rate(
	item_code: str, customer: str | None, price_list: str, qty: float, customer_group: str | None = None
) -> float | None:
	"""The customer's (or, without one, the Customer Group's) net price for one unit at this
	quantity, after pricing rules."""
	return shared(
		"customer_rates",
		(item_code, customer, customer_group, price_list, flt(qty)),
		lambda: work_out_rate(item_code, customer, price_list, qty, customer_group),
	)


def work_out_rate(
	item_code: str, customer: str | None, price_list: str, qty: float, customer_group: str | None
) -> float | None:
	from erpnext.stock.get_item_details import get_item_details

	from shop.storefront.checkout import elevated

	settings = frappe.get_cached_doc("Shop Settings")
	args = frappe._dict(
		item_code=item_code,
		customer=customer,
		customer_group=customer_group,
		company=settings.company,
		currency=settings.currency,
		price_list=price_list,
		price_list_currency=settings.currency,
		plc_conversion_rate=1,
		conversion_rate=1,
		doctype="Sales Order",
		transaction_date=nowdate(),
		qty=qty,
		stock_qty=qty,
		conversion_factor=1,
		transaction_type="selling",
	)
	try:
		with elevated():
			details = get_item_details(args)
	except Exception:
		frappe.clear_messages()
		frappe.log_error(title=f"Customer price failed for {item_code}")
		raise NotKept(None) from None
	list_rate = flt(details.get("price_list_rate"))
	if not list_rate:
		return None
	if flt(details.get("discount_percentage")):
		rate = list_rate * (1 - flt(details.discount_percentage) / 100)
	else:
		rate = list_rate - flt(details.get("discount_amount"))
	return flt(rate, 2)


def forget_rates(doc=None, method=None) -> None:
	"""A change to what prices are worked out from (Item Price, Pricing Rule, the item, its group,
	tax, the customer): rates worked out before, in this request or any, are stale."""
	for name in ("shop_customer_rates", "shop_item_tax_rates", "shop_display_currencies"):
		if hasattr(frappe.local, name):
			delattr(frappe.local, name)
	frappe.cache.set_value(PRICE_VERSION, frappe.generate_hash(length=8))


PRICE_VERSION = "shop:price_version"
# prices are kept a few minutes, also for Pricing Rules that start or end at a date
SHARED_SECONDS = 10 * 60


class NotKept(Exception):
	"""A value worked out this time that isn't kept for others (a lookup that failed)."""

	def __init__(self, value):
		self.value = value


def shared(name: str, key: tuple, work_out):
	"""A value worked out once for every request (in Redis), until prices change."""
	import hashlib

	cache = request_cache(f"shop_{name}")
	if key in cache:
		return cache[key]
	version = frappe.cache.get_value(PRICE_VERSION) or "0"
	digest = hashlib.sha1(frappe.as_json(key, indent=None).encode()).hexdigest()
	redis_key = f"shop:{name}:{version}:{nowdate()}:{digest}"
	kept = frappe.cache.get_value(redis_key)
	if kept is None:
		try:
			kept = {"value": work_out()}
		except NotKept as unkept:
			cache[key] = unkept.value
			return unkept.value
		frappe.cache.set_value(redis_key, kept, expires_in_sec=SHARED_SECONDS)
	cache[key] = kept["value"]
	return cache[key]


def request_cache(name: str) -> dict:
	"""A dict that lives for the current request only."""
	cache = getattr(frappe.local, name, None)
	if cache is None:
		cache = {}
		setattr(frappe.local, name, cache)
	return cache
