"""Checkout totals, worked out by ERPNext on the Sales Order the checkout would place."""

import json
import math
from collections.abc import Callable

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money

from shop.storefront import shipping as shipping_module

GATEWAY = "gateway"
BANK = "bank"
SWIFT = "swift"
BANK_METHODS = (BANK, SWIFT)
ACCOUNT = "account"
COD = "cod"


def settings():
	return frappe.get_cached_doc("Shop Settings")


def company_currency() -> str:
	return frappe.get_cached_value("Company", settings().company, "default_currency")


def company_country() -> str:
	return frappe.get_cached_value("Company", settings().company, "country")


def tax_template_for(address: frappe._dict | None) -> str | None:
	"""The sales tax template for an order going to this address: the ERPNext Tax Rule for the
	shopping cart that matches it, else the store's Export Tax Template for orders shipped abroad,
	else the store's Tax Template."""
	from erpnext.accounts.doctype.tax_rule.tax_rule import get_tax_template
	from frappe.utils import nowdate

	from shop.storefront import pricing

	s = settings()
	country = (address or {}).get("country") or company_country()
	args = {
		"tax_type": "Sales",
		"company": s.company,
		"use_for_shopping_cart": 1,
		"shipping_country": country,
		"billing_country": country,
	}
	customer = pricing.session_customer()
	if customer:
		group, category = frappe.get_cached_value("Customer", customer, ["customer_group", "tax_category"])
		args.update(customer_group=group, tax_category=category or "")
	else:
		# a guest is priced, and so taxed, as a new customer of the default Customer Group
		args["customer_group"] = frappe.db.get_single_value("Selling Settings", "customer_group")
	rule = get_tax_template(nowdate(), args)
	if rule:
		return rule
	if is_export(address) and s.get("export_tax_template"):
		return s.export_tax_template
	return s.tax_template


def is_export(address: frappe._dict | None) -> bool:
	return bool(address and address.get("country") and address.country != company_country())


def gateway_rows() -> list:
	"""The store's online payment gateways with a Payment Gateway Account for its company."""
	return [row for row in settings().get("payment_gateways") or [] if gateway_accounts(row.payment_gateway)]


def gateway_available() -> bool:
	return bool(gateway_rows())


def gateway_accounts(gateway: str) -> list[frappe._dict]:
	"""The gateway's Payment Gateway Accounts paying into the store company's accounts."""
	company = settings().company
	return [
		account
		for account in frappe.get_all(
			"Payment Gateway Account",
			filters={"payment_gateway": gateway},
			fields=["name", "currency", "payment_account"],
			order_by="is_default desc, creation",
		)
		if not account.payment_account
		or frappe.get_cached_value("Account", account.payment_account, "company") == company
	]


def gateway_account(gateway: str, currency: str | None = None) -> frappe._dict | None:
	"""The Payment Gateway Account an order is paid through: the gateway's account in the order's
	currency, or else in the store's currency."""
	accounts = gateway_accounts(gateway)
	for wanted in (currency, company_currency()):
		for account in accounts:
			if wanted and account.currency == wanted:
				return account
	return None


def gateway_method(gateway: str) -> str:
	return f"{GATEWAY}:{gateway}"


def is_gateway(method: str | None) -> bool:
	return bool(method) and (method == GATEWAY or method.startswith(f"{GATEWAY}:"))


def gateway_row(method_or_gateway: str | None):
	"""The store's online gateway for a checkout payment method (or a Payment Gateway's name). A
	plain "gateway" is the first one."""
	rows = gateway_rows()
	if not method_or_gateway or not rows:
		return None
	if method_or_gateway == GATEWAY:
		return rows[0]
	name = method_or_gateway.removeprefix(f"{GATEWAY}:")
	return next((row for row in rows if row.payment_gateway == name), None)


def resolve_method(method: str | None) -> str | None:
	"""A plain "gateway" is the store's first online gateway."""
	if method == GATEWAY:
		row = gateway_row(GATEWAY)
		return gateway_method(row.payment_gateway) if row else method
	return method


def gateway_label(row) -> str:
	return row.label or row.payment_gateway


def fee_label(row) -> str:
	return (row.fee_label if row else None) or _("Card fee")


def payment_methods(export: bool = False, swift: bool = False) -> list[dict]:
	"""How a shopper can pay. At checkout an international (Swift) transfer is chosen under bank
	transfer, so it is listed on its own only when `swift` is asked for."""
	s = settings()
	methods = [
		{
			"method": gateway_method(row.payment_gateway),
			"label": gateway_label(row),
			"fee_note": card_fee_note(export, row),
		}
		for row in gateway_rows()
	]
	if s.get("enable_bank_transfer") and bank_accounts():
		methods.append({"method": BANK, "label": _("Bank transfer"), "fee_note": ""})
		if swift and bank_accounts(SWIFT):
			methods.append(
				{"method": SWIFT, "label": _("International bank transfer (Swift)"), "fee_note": ""}
			)
	if s.enable_cod:
		methods.append({"method": COD, "label": _("Cash on Delivery"), "fee_note": ""})
	terms = on_account_terms()
	if terms:
		methods.insert(0, {"method": ACCOUNT, "label": _("Pay on account (invoice)"), "fee_note": terms})
	return methods


def on_account_terms(customer: str | None = None) -> str | None:
	"""The customer's payment terms, when they may pay on account (the signed-in shopper's
	customer by default)."""
	from shop.storefront.pricing import session_customer

	customer = customer or session_customer()
	if not customer or not frappe.get_meta("Customer").has_field("shop_allow_on_account"):
		return None
	allowed, terms = frappe.db.get_value("Customer", customer, ["shop_allow_on_account", "payment_terms"])
	return terms if allowed and terms else None


def card_fee_rates(export: bool, row=None) -> tuple[float, float]:
	"""An online gateway's fee: percent of the total and a fixed amount in the store's currency."""
	if not settings().get("card_fee_item") or not row:
		return 0.0, 0.0
	if export and (row.fee_percent_international or row.fee_fixed_international):
		return flt(row.fee_percent_international) / 100, flt(row.fee_fixed_international)
	return flt(row.fee_percent) / 100, flt(row.fee_fixed)


def card_fee_note(export: bool, row=None) -> str:
	percent, fixed = card_fee_rates(export, row)
	if not percent and not fixed:
		return ""
	parts = []
	if percent:
		parts.append(f"{flt(percent * 100, 2):g}%")
	if fixed:
		from shop.storefront.pricing import with_code

		# in the store's currency, said so when shoppers can see prices in others
		parts.append(with_code(fmt_money(fixed, currency=company_currency()), company_currency()))
	return _("{0} {1}, added to the total").format(fee_label(row), " + ".join(parts))


def branch_code_label(currency: str) -> str:
	"""What a bank branch code is usually called where the currency is used, when the store hasn't
	named it on the bank account."""
	return {
		"USD": _("ACH routing number"),
		"AUD": _("BSB"),
		"GBP": _("Sort code"),
		"CAD": _("Transit number"),
	}.get(currency, _("Branch code"))


def bank_accounts(method: str = BANK) -> list[frappe._dict]:
	"""The store's accounts for a bank transfer method: ERPNext company Bank Accounts with the
	currency of their account, the details customers pay to and the fee the bank takes from a
	payment. Swift transfers need the Bank's SWIFT code."""
	rows = []
	for row in settings().get("bank_accounts") or []:
		if not row.bank_account:
			continue
		account = frappe.get_cached_doc("Bank Account", row.bank_account)
		if account.disabled:
			continue
		currency = (
			frappe.get_cached_value("Account", account.account, "account_currency")
			if account.account
			else None
		)
		swift = frappe.get_cached_value("Bank", account.bank, "swift_number") if account.bank else None
		if not currency or (method == SWIFT and not swift):
			continue
		rows.append(
			frappe._dict(
				bank_account=row.bank_account,
				currency=currency,
				label=row.label or currency,
				conversion_fee_percent=flt(row.conversion_fee_percent),
				transfer_fee=flt(row.swift_transfer_fee if method == SWIFT else row.local_transfer_fee),
				details=bank_account_details(account, currency, method, row.get("branch_code_label"))
				+ [line.strip() for line in (row.instructions or "").splitlines() if line.strip()],
			)
		)
	return rows


def bank_account_details(
	account, currency: str, method: str = BANK, branch_code_name: str | None = None
) -> list[str]:
	"""The lines a customer needs to pay into a Bank Account: from a bank in its own country, or
	by Swift from anywhere."""
	bank = frappe.get_cached_doc("Bank", account.bank) if account.bank else None
	# a company bank account is held by the company
	holder = (
		frappe.get_cached_value("Company", account.company, "company_name")
		if account.company
		else account.account_name
	)
	lines = [
		(_("Account name"), holder),
		(_("Bank"), bank.bank_name if bank else None),
		(branch_code_name or branch_code_label(currency), account.branch_code if method == BANK else None),
		(_("Account number"), account.bank_account_no),
		(_("IBAN"), account.iban),
		(_("BIC/SWIFT"), bank.swift_number if bank else None),
	]
	return [f"{label}: {value}" for label, value in lines if value]


def bank_currencies(method: str = BANK) -> list[str]:
	return list(dict.fromkeys(row.currency for row in bank_accounts(method)))


def bank_account(currency: str, method: str = BANK) -> frappe._dict | None:
	for row in bank_accounts(method):
		if row.currency == currency:
			return row
	return None


def bank_routes(currency: str, tax_factor: float = 1) -> list[dict]:
	"""Where a bank transfer in this currency can come from, with what its fee adds to the order
	(with tax when prices are shown with tax)."""
	routes = []
	for method, label in (
		(BANK, _("Local transfer")),
		(SWIFT, _("Swift transfer")),
	):
		account = bank_account(currency, method)
		if account:
			if account.transfer_fee:
				label = _("{0} +{1}").format(label, money(account.transfer_fee * tax_factor, currency))
			routes.append({"method": method, "label": label})
	return routes


def fee_factor(export: bool, shown_factor: float = 1) -> float:
	"""What a transfer fee adds to the order per unit of the fee the store keeps: fees are grossed up
	by the tax on the fee item at home, so a store showing prices with tax shows the fee with it."""
	s = settings()
	if export or not (s.prices_include_tax or s.get("show_prices_with_tax")):
		return 1
	from shop.storefront import pricing

	return max(shown_factor, 1 + pricing.item_tax_rate(s.get("transfer_fee_item")) / 100)


def suggested_bank_method(address: frappe._dict | None, currency: str) -> str:
	"""Swift for a payer abroad: one whose country doesn't use the account's currency."""
	from frappe.geo.country_info import get_country_info

	if not address or not address.get("country") or not bank_account(currency, SWIFT):
		return BANK
	local = (get_country_info(address.country) or {}).get("currency")
	return BANK if local == currency else SWIFT


def suggested_currency(address: frappe._dict | None) -> str:
	"""The customer's own currency when the store has an account in it, else the company's."""
	options = bank_currencies()
	if address and address.get("country"):
		from frappe.geo.country_info import get_country_info

		currency = (get_country_info(address.country) or {}).get("currency")
		if currency in options:
			return currency
	return company_currency()


def preferred_bank_currency(address: frappe._dict | None) -> str:
	"""The currency the shopper picked for prices, when the store takes bank transfers in it;
	otherwise the currency of where the order is going."""
	from shop.storefront import pricing

	chosen = pricing.chosen_currency()
	return chosen if chosen in bank_currencies() else suggested_currency(address)


def exchange_rate(from_currency: str, to_currency: str) -> float:
	if from_currency == to_currency:
		return 1.0
	from erpnext.setup.utils import get_exchange_rate

	rate = flt(get_exchange_rate(from_currency, to_currency))
	if not rate:
		frappe.throw(_("No exchange rate from {0} to {1} is available").format(from_currency, to_currency))
	return rate


def money(amount: float, currency: str) -> str:
	return fmt_money(amount, currency=currency)


def compute(
	cart,
	address: dict | None = None,
	shipping_option: str | None = None,
	payment_method: str | None = None,
	currency: str | None = None,
	refresh_shipping: bool = False,
	collected: bool = False,
) -> frappe._dict:
	"""The order as it stands, priced, taxed and totalled by ERPNext on an unsaved Sales Order, so
	the total shown is the total charged. Amounts are in the order currency. An order the customer
	collects from the store is taxed where it is collected, whatever their address."""
	from shop.storefront import cart as cart_module
	from shop.storefront import pricing

	address = shipping_module.normalize_address(address)
	taxed_at = frappe._dict(country=company_country()) if collected else address
	export = is_export(taxed_at)
	template = tax_template_for(taxed_at)
	method = resolve_method(payment_method)
	if method == SWIFT and currency in bank_currencies() and not bank_account(currency, SWIFT):
		method = BANK
	currency = order_currency(method, currency, address)

	cart_module.refresh_rates(cart)
	order = new_order(cart, pricing.session_customer(), currency, template)
	# a parcel sent abroad carries no tax from its carrier
	order.flags.shop_export = is_export(address) and not collected
	coupon = apply_coupon(order)
	calculate(order)

	subtotal = flt(order.base_total) - flt(order.base_discount_amount)
	choice = shipping_module.parse_choice(shipping_option or cart.get("shipping_rate"))
	parcels = shipping_module.parcels(order)
	groups = []
	for index, parcel in enumerate(parcels or [None]):
		options = shipping_module.get_options(
			cart, address, subtotal, refresh_shipping, parcel, first=index == 0
		)
		wanted = (
			choice.get(parcel.key if parcel else "") if isinstance(choice, dict) else (choice if index == 0 else None)
		)
		# delivery, not collection, unless the customer picks collection
		chosen = shipping_module.find_option(options["options"], wanted) or next(
			(option for option in options["options"] if not shipping_module.is_pickup(option)),
			next(iter(options["options"]), None),
		)
		if chosen and parcel:
			chosen = dict(chosen, warehouse=parcel.warehouse, parcel=parcel.key)
			if len(parcels) > 1:
				chosen["label"] = _("{0} (parcel {1} of {2})").format(chosen["label"], index + 1, len(parcels))
		if chosen:
			add_shipping(order, chosen)
		groups.append(frappe._dict(parcel=parcel, options=options, chosen=chosen))
	first = groups[0]
	if (
		not collected
		and export
		and parcels
		and all(group.chosen and shipping_module.is_pickup(group.chosen) for group in groups)
	):
		return compute(cart, address, shipping_option, payment_method, currency, collected=True)
	# goods collected are taxed where they are handed over, goods sent abroad aren't: one order is
	# either collected or sent
	partly_collected = (
		not collected
		and export
		and any(group.chosen and shipping_module.is_pickup(group.chosen) for group in groups)
	)
	messages = list(
		dict.fromkeys(message for group in groups for message in group.options.get("messages") or [])
	)
	if partly_collected:
		messages.append(
			_(
				"An order sent abroad is either all collected or all sent: choose collection or delivery for every parcel."
			)
		)

	fees = []
	if order.flags.shop_export:
		sent = [
			group
			for group in groups
			if group.parcel and not (group.chosen and shipping_module.is_pickup(group.chosen))
		]
		fees += add_duties(order, address.get("country"), len(sent))
	if is_gateway(method):
		fees += add_card_fee(order, export, gateway_row(method))
	elif method in BANK_METHODS:
		account = bank_account(currency, method)
		if currency != order.company_currency:
			fees += add_conversion_fee(order, account)
		fees += add_transfer_fee(order, account, method)
	calculate(order)

	return frappe._dict(
		order=order,
		currency=currency,
		company_currency=company_currency(),
		exchange_rate=1 / flt(order.conversion_rate),
		export=export,
		address=address,
		payment_method=method,
		tax_template=template,
		coupon=coupon,
		# the order ships when every parcel has a service
		shipping=frappe._dict(first.chosen)
		if all(group.chosen for group in groups) and not partly_collected
		else None,
		shippings=[frappe._dict(group.chosen) for group in groups if group.chosen],
		shipping_options=[
			dict(option, customer_amount=shipping_line_amount(order, option)) for option in first.options["options"]
		],
		shipping_groups=[
			frappe._dict(
				key=group.parcel.key if group.parcel else "",
				parcel=group.parcel,
				items=group.parcel["items"] if group.parcel else [],
				chosen=group.chosen,
				options=[
					dict(option, customer_amount=shipping_line_amount(order, option))
					for option in group.options["options"]
				],
			)
			for group in groups
		],
		shipping_messages=messages,
		shipping_pending=any(group.options.get("pending") for group in groups),
		fees=fees,
		total=order_total(order),
	)


def parcel_label(group, index: int, count: int) -> str:
	"""Parcel 1 of 2, and where it comes from when the store names the location for customers."""
	from shop.storefront.stock import location

	place = location(group.parcel.warehouse) if group.get("parcel") else None
	if place and place.named:
		return _("Parcel {0} of {1} from {2}").format(index, count, place.label)
	return _("Parcel {0} of {1}").format(index, count)


def order_currency(method: str | None, currency: str | None, address: frappe._dict | None) -> str:
	"""Orders are in the company currency, except bank transfers to an account in another currency
	and online payments through a gateway account in the currency the shopper picked."""
	base = company_currency()
	if is_gateway(method):
		from shop.storefront.pricing import display_currency

		row = gateway_row(method)
		account = row and gateway_account(row.payment_gateway, currency or display_currency())
		return account.currency if account else base
	options = bank_currencies(method) if method in BANK_METHODS else []
	if not options:
		return base
	if currency in options:
		return currency
	preferred = preferred_bank_currency(address)
	if preferred in options:
		return preferred
	return base if base in options else options[0]


def new_order(cart, customer: str | None, currency: str, template: str | None):
	"""An unsaved Sales Order for the cart, priced by ERPNext as a desk order for this customer
	would be. Guests are priced as a new customer of the store's default Customer Group."""
	from frappe.utils import add_days, nowdate

	from shop.storefront import pricing

	s = settings()
	order = frappe.new_doc("Sales Order")
	order.update(
		{
			"company": s.company,
			"order_type": "Sales",
			"transaction_date": nowdate(),
			"delivery_date": add_days(nowdate(), cint(s.delivery_days)),
			"customer": customer,
			"currency": currency,
			"conversion_rate": exchange_rate(currency, company_currency()),
			"selling_price_list": pricing.customer_price_list(customer) if customer else s.price_list,
		}
	)
	# the group decides which Pricing Rules apply, so it is set before ERPNext prices the order
	order.customer_group = (
		frappe.get_cached_value("Customer", customer, "customer_group")
		if customer
		else frappe.db.get_single_value("Selling Settings", "customer_group")
	)
	# ERPNext applies the coupon's Pricing Rule, which says who and what it is for
	order.coupon_code = cart.get("coupon_code")
	from shop.storefront.stock import allocate

	lines = [(row.item_code, flt(row.qty)) for row in cart.items]
	allocated = allocate(lines)
	# each line is priced whole, so quantity breaks apply to all of it, then sent from the first
	# of the store's warehouses that has it
	splits = []
	for code, qty in lines:
		parts = []
		while allocated and allocated[0].item_code == code and sum(part.qty for part in parts) < qty:
			parts.append(allocated.pop(0))
		row = order.append(
			"items",
			{
				"item_code": code,
				"qty": qty,
				# the store prices, shows and stocks items in their stock unit; ERPNext would
				# otherwise sell in the item's Sales UOM (a box of ten at the price of one)
				"uom": frappe.get_cached_value("Item", code, "stock_uom"),
				"conversion_factor": 1,
				"warehouse": parts[0].warehouse if parts else None,
				"delivery_date": order.delivery_date,
			},
		)
		if len(parts) > 1:
			splits.append((row, parts))
	if template:
		from shop.compat import get_sales_taxes

		order.taxes_and_charges = template
		for tax in get_sales_taxes(template):
			order.append("taxes", tax)
	order.set_missing_values(for_validate=True)
	if not order.ignore_pricing_rule:
		from erpnext.accounts.doctype.pricing_rule.utils import apply_pricing_rule_on_transaction

		# rules for the whole order (a coupon's minimum amount) look at its totals
		calculate(order)
		apply_pricing_rule_on_transaction(order)
	for row, parts in splits:
		split_row(order, row, parts)
	order.flags.shop_split_lines = bool(splits)
	remove_included_tax(order, template)
	return order


def split_row(order, row, parts) -> None:
	"""One priced line sent from several warehouses, as one row per warehouse at the line's rate."""
	keep = {
		key: value
		for key, value in row.as_dict().items()
		if key not in ("name", "idx", "qty", "stock_qty", "warehouse")
		and key not in frappe.model.default_fields
	}
	factor = flt(row.conversion_factor) or 1
	row.update({"qty": parts[0].qty, "stock_qty": parts[0].qty * factor, "warehouse": parts[0].warehouse})
	position = order.items.index(row)
	for offset, part in enumerate(parts[1:], 1):
		extra = order.append(
			"items", dict(keep, qty=part.qty, stock_qty=part.qty * factor, warehouse=part.warehouse)
		)
		order.items.remove(extra)
		order.items.insert(position + offset, extra)
	for idx, item in enumerate(order.items, 1):
		item.idx = idx
	calculate(order)


def keep_prices(order) -> None:
	"""An order with a line split across warehouses is saved at the prices it was given. ERPNext
	prices each row at its own quantity when the order, or a Delivery Note or invoice made from it,
	is saved, which would lose a quantity break given to the whole line. With Ignore Pricing Rule the
	rows keep their rates; they don't name the rules, which ERPNext would then take off them."""
	if not order.flags.get("shop_split_lines"):
		return
	order.ignore_pricing_rule = 1
	order.set("pricing_rules", [])
	for row in order.items:
		row.pricing_rules = ""


def remove_included_tax(order, template: str | None) -> None:
	"""Prices that include the store's own tax charge an order with other taxes (e.g. an export)
	without it: the store's tax is taken off each price and the order's own included tax put on."""
	s = settings()
	if not s.prices_include_tax or template == s.tax_template:
		return
	from shop.storefront import pricing

	other = 1 + included_rate(template) / 100
	for item in order.items:
		# the store's tax on this item, which its Item Tax Template sets (none on a zero-rated one)
		factor = other / (1 + pricing.item_tax_rate(item.item_code) / 100)
		if factor == 1:
			continue
		for field in ("price_list_rate", "rate", "discount_amount"):
			item.set(field, flt(flt(item.get(field)) * factor, item.precision(field)))


def included_rate(template: str | None) -> float:
	if not template:
		return 0.0
	from shop.compat import get_sales_taxes

	return sum(
		flt(row.get("rate"))
		for row in get_sales_taxes(template)
		if row.get("charge_type") == "On Net Total" and row.get("included_in_print_rate")
	)


def apply_coupon(order) -> dict | None:
	"""The order's coupon, when ERPNext applied its Pricing Rule; a coupon that doesn't apply to this
	order is taken off it."""
	from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules

	if not order.get("coupon_code"):
		return None
	code, rule = frappe.db.get_value("Coupon Code", order.coupon_code, ["coupon_code", "pricing_rule"])
	applied = {row.pricing_rule for row in order.get("pricing_rules") or []}
	for item in order.items:
		applied.update(get_applied_pricing_rules(item.get("pricing_rules")))
	if rule not in applied:
		order.coupon_code = None
		return None
	return {"code": code, "name": order.coupon_code}


def coupon_discount(order) -> float:
	"""What the coupon takes off the order, in the order currency."""
	from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules

	rule = frappe.db.get_value("Coupon Code", order.coupon_code, "pricing_rule")
	discount = flt(order.discount_amount)
	for item in order.items:
		if rule in get_applied_pricing_rules(item.get("pricing_rules")):
			discount += (flt(item.price_list_rate) - flt(item.rate)) * flt(item.qty)
	return discount


def calculate(order) -> None:
	order.calculate_taxes_and_totals()


def order_total(order) -> float:
	"""What the customer pays: the rounded total, unless rounding is turned off."""
	return flt(order.rounded_total) or flt(order.grand_total)


def shipping_line_amount(order, option: dict) -> float:
	"""A shipping option's price as an order line, in the order currency.

	A price that includes tax includes what the carrier charges for that parcel: the store's own tax
	for a parcel sent within its country, none for one sent abroad (carriers zero-rate international
	transport). So the store's cost is the price without its own tax at home, the whole price for an
	export; the order then charges its own tax on that cost."""
	s = settings()
	amount = flt(option["amount"])
	home = (
		1 + included_rate(s.tax_template) / 100
		if s.prices_include_tax
		else 1 + added_rate(s.tax_template) / 100
	)
	if option.get("tax_included") and not order.flags.get("shop_export"):
		amount /= home
	if s.prices_include_tax:
		amount *= 1 + included_rate(order.taxes_and_charges) / 100
	return flt(amount / flt(order.conversion_rate), order.precision("grand_total"))


def added_rate(template: str | None) -> float:
	if not template:
		return 0.0
	from shop.compat import get_sales_taxes

	return sum(
		flt(row.get("rate"))
		for row in get_sales_taxes(template)
		if row.get("charge_type") == "On Net Total" and not row.get("included_in_print_rate")
	)


def add_shipping(order, option: dict) -> None:
	"""Shipping as the store's shipping item, or as a charge on its shipping account."""
	s = settings()
	amount = shipping_line_amount(order, option)
	if not amount:
		return
	label = option.get("label") or _("Shipping")
	if s.get("shipping_item"):
		add_line(order, s.shipping_item, amount, label)
	elif s.get("shipping_account"):
		order.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": s.shipping_account,
				"description": label,
				"tax_amount": amount,
			},
		)


def add_line(order, item_code: str, rate: float, description: str):
	"""A charge line: its details from ERPNext, with no rate yet, so working out a quote never saves
	an Item Price for it."""
	row = order.append(
		"items",
		{"item_code": item_code, "qty": 1, "description": description, "delivery_date": order.delivery_date},
	)
	order.set_missing_item_details(for_validate=True)
	set_charge(row, rate)
	return row


def set_charge(row, rate: float) -> None:
	"""A charge line is charged at its own amount, not as a discount on a list price."""
	row.update({"price_list_rate": rate, "rate": rate, "discount_percentage": 0, "discount_amount": 0})


def import_duty(country: str | None):
	"""The store's import duties for a country it sends orders to duties paid."""
	s = settings()
	if not country or not s.get("duties_item"):
		return None
	return next((row for row in s.import_duties if row.country == country), None)


def add_duties(order, country: str | None, parcel_count: int) -> list[frappe._dict]:
	"""The country's duty on the goods, the carrier's fee on that duty and its fee per parcel, as one
	line on the order. Goods worth no more than the country's duty-free value pay none."""
	s = settings()
	duty = import_duty(country)
	if not duty or not parcel_count:
		return []
	calculate(order)
	goods = [item for item in order.items if not is_charge_item(item.item_code)]
	free_up_to = flt(duty.duty_free_up_to)
	if free_up_to and sum(flt(item.base_net_amount) for item in goods) <= free_up_to:
		return []
	amount = sum(flt(item.net_amount) for item in goods) * flt(duty.duty_rate) / 100
	amount += amount * flt(duty.fee_on_duty) / 100
	amount += flt(duty.fee_per_parcel) * parcel_count / flt(order.conversion_rate)
	if amount <= 0:
		return []
	label = frappe.get_cached_value("Item", s.duties_item, "item_name") or _("Duties and import fees")
	add_line(order, s.duties_item, flt(amount, order.precision("grand_total")), label)
	return [frappe._dict(kind="duties", label=label, item=s.duties_item)]


def add_card_fee(order, export: bool, gateway=None) -> list[frappe._dict]:
	"""The online gateway's fee as a line on the order. What the store keeps of it, after any tax on
	the fee, pays the provider's charge on the final total: percent of the total plus the fixed
	amount."""
	s = settings()
	percent, fixed = card_fee_rates(export, gateway)
	calculate(order)
	if not (percent or fixed) or order_total(order) <= 0:
		return []
	before = flt(order.grand_total)
	label = fee_label(gateway)
	row, gross, net = probe_line(order, s.card_fee_item, label)
	# named as the gateway's fee on the order and its invoice, whatever the item is called
	row.item_name = label
	kept = (percent * before + fixed / flt(order.conversion_rate)) / (1 - percent * gross / net)
	set_charge(row, round_up(kept / net, row.precision("rate")))
	return [frappe._dict(kind="card_fee", label=label, item=s.card_fee_item)]


def add_conversion_fee(order, account: frappe._dict | None) -> list[frappe._dict]:
	"""The bank account's currency conversion fee: the store keeps its percent of the order total."""
	s = settings()
	percent = flt(account.conversion_fee_percent) / 100 if account else 0
	calculate(order)
	if not percent or not s.get("conversion_fee_item") or order_total(order) <= 0:
		return []
	before = flt(order.grand_total)
	label = _("Currency conversion")
	row, _gross, net = probe_line(order, s.conversion_fee_item, label)
	set_charge(row, round_up(percent * before / net, row.precision("rate")))
	return [frappe._dict(kind="conversion_fee", label=label, item=s.conversion_fee_item)]


def add_transfer_fee(order, account: frappe._dict | None, method: str) -> list[frappe._dict]:
	"""The fixed fee the bank takes from a transfer into the account: the store keeps that much."""
	s = settings()
	fee = flt(account.transfer_fee) if account else 0
	calculate(order)
	if not fee or not s.get("transfer_fee_item") or order_total(order) <= 0:
		return []
	label = _("International transfer fee (Swift)") if method == SWIFT else _("Bank transfer fee")
	row, _gross, net = probe_line(order, s.transfer_fee_item, label)
	set_charge(row, round_up(fee / net, row.precision("rate")))
	return [frappe._dict(kind="transfer_fee", label=label, item=s.transfer_fee_item)]


def probe_line(order, item_code: str, label: str):
	"""Add a fee line and measure, per unit of its rate, what ERPNext adds to the grand total and
	what the store keeps (the net amount, after any tax the item carries)."""
	gross_before, net_before = flt(order.grand_total), flt(order.net_total)
	row = add_line(order, item_code, 100, label)
	calculate(order)
	gross = (flt(order.grand_total) - gross_before) / 100 or 1
	net = (flt(order.net_total) - net_before) / 100 or 1
	return row, gross, net


def round_up(amount: float, precision: int = 2) -> float:
	factor = 10**precision
	return math.ceil(round(amount * factor, 6)) / factor


def tax_name(description: str | None) -> str:
	"""A tax's short name from its description: "GST @ 15.0" -> "GST", "VAT 20% (included)" -> "VAT"."""
	import re

	name = re.split(r"[@(]", description or "")[0]
	return re.sub(r"\s*\d+(\.\d+)?\s*%?\s*$", "", name).strip()


def summary_lines(order) -> tuple[list[dict], list[str]]:
	"""An order's lines as a receipt shows them: subtotal, discount, shipping, fees, taxes added on
	top, rounding, plus notes for taxes included in the prices. Amounts are in the order currency."""
	product_lines = [item for item in order.items if not is_charge_item(item.item_code)]
	lines = [
		{
			"kind": "subtotal",
			"label": _("Subtotal"),
			"amount": sum(flt(item.amount) for item in product_lines),
		}
	]
	if flt(order.discount_amount):
		lines.append({"kind": "discount", "label": _("Discount"), "amount": -flt(order.discount_amount)})
	s = settings()
	kinds = {
		s.get("shipping_item"): "shipping",
		s.get("card_fee_item"): "card_fee",
		s.get("conversion_fee_item"): "conversion_fee",
		s.get("transfer_fee_item"): "transfer_fee",
		s.get("duties_item"): "duties",
	}
	for item in order.items:
		if is_charge_item(item.item_code):
			lines.append(
				{
					"kind": kinds.get(item.item_code, "charge"),
					"label": item.description or item.item_name,
					"amount": flt(item.amount),
					"row": item.idx,
				}
			)
	notes = []
	if any(line["kind"] == "duties" for line in lines):
		notes.append(_("Duties are paid before delivery: there is nothing more to pay when it arrives."))
	for tax in order.taxes:
		amount = flt(tax.tax_amount_after_discount_amount)
		if not amount:
			continue
		if tax.charge_type == "Actual":
			lines.append({"kind": "shipping", "label": tax.description, "amount": amount})
		elif tax.included_in_print_rate:
			notes.append(
				_("Includes {0}: {1}").format(
					tax_name(tax.description) or tax.description, money(amount, order.currency)
				)
			)
		else:
			lines.append({"kind": "tax", "label": tax.description, "amount": amount})
	if flt(order.rounding_adjustment) and flt(order.rounded_total):
		lines.append({"kind": "rounding", "label": _("Rounding"), "amount": flt(order.rounding_adjustment)})
	return lines, notes


def row_tax_rate(order, row=None) -> float:
	"""Percent of tax the order adds on top of a row's amount, as ERPNext works it out: its taxes on
	the net total, at the rates of the row's Item Tax Template where it has one. Without a row, the
	order's own rates."""
	from erpnext.stock.get_item_details import NOT_APPLICABLE_TAX

	item_rates = json.loads(row.item_tax_rate or "{}") if row else {}
	rates = [
		item_rates.get(tax.account_head, tax.rate)
		for tax in order.taxes
		if tax.charge_type == "On Net Total" and not tax.included_in_print_rate
	]
	return sum(flt(rate) for rate in rates if rate != NOT_APPLICABLE_TAX)


def shown_with_tax(lines: list[dict], order) -> list[dict]:
	"""Lines with the tax added on top spread into them, for stores that show prices with tax; the
	subtotal takes any rounding difference so the lines still add up to the total."""
	if not any(line["kind"] == "tax" for line in lines):
		return lines
	rows = {row.idx: row for row in order.items}

	def with_tax(amount, row=None):
		return amount * (1 + row_tax_rate(order, row) / 100)

	# a discount on the Grand Total includes the tax already
	discount_has_tax = order.apply_discount_on == "Grand Total"
	shown = [dict(line) for line in lines if line["kind"] != "tax"]
	for line in shown[1:]:
		if line["kind"] == "rounding" or (line["kind"] == "discount" and discount_has_tax):
			continue
		if line["kind"] == "discount":
			# the tax is on what is left of each row after the discount
			amount = -sum(with_tax(flt(row.amount) - flt(row.net_amount), row) for row in order.items)
		elif line.get("row"):
			amount = with_tax(line["amount"], rows[line["row"]])
		else:
			continue
		line["amount"] = flt(amount, order.precision("grand_total"))
	shown[0]["amount"] = flt(
		order_total(order) - sum(line["amount"] for line in shown[1:]), order.precision("grand_total")
	)
	return shown


def shown_lines(order, export: bool = False) -> tuple[list[dict], list[str], Callable]:
	"""An order's lines as the shopper sees them everywhere (checkout, order page, emails, quotes):
	with the tax spread into them when the store shows prices with tax, rounding part of the
	subtotal. Also factor(row), which turns a row's amount into its shown amount (without a row:
	an amount the order would add, like a shipping option)."""
	lines, notes = summary_lines(order)
	if order.get("coupon_code"):
		code = frappe.db.get_value("Coupon Code", order.coupon_code, "coupon_code")
		for line in lines:
			if line["kind"] == "discount":
				line["label"] = _("Discount ({0})").format(code)
	taxes_added = [line for line in lines if line["kind"] == "tax"]

	def factor(row=None):
		return 1

	if settings().get("show_prices_with_tax") and taxes_added and not export:
		lines = shown_with_tax(lines, order)

		def factor(row=None):
			return 1 + row_tax_rate(order, row) / 100

		notes.insert(
			0,
			_("Includes {0}: {1}").format(
				", ".join(tax_name(line["label"]) or line["label"] for line in taxes_added),
				money(sum(line["amount"] for line in taxes_added), order.currency),
			),
		)
	elif export and order.taxes_and_charges != settings().tax_template:
		notes.append(_("Tax-free export"))
	# rounding to the payable total is part of the subtotal for the shopper
	for rounding in [line for line in lines if line["kind"] == "rounding"]:
		lines.remove(rounding)
		lines[0]["amount"] = flt(lines[0]["amount"] + rounding["amount"], order.precision("grand_total"))
	return lines, notes, factor


def payload(quote: frappe._dict) -> dict:
	"""The quote for the browser: lines and totals already formatted."""
	from shop.storefront import pricing

	order = quote.order
	currency = quote.currency
	lines, notes, factor = shown_lines(order, quote.export)
	for line in lines:
		line["formatted"] = money(line["amount"], currency) if line["amount"] else _("Free")
	if is_gateway(quote.payment_method):
		picked = pricing.display_currency()
		if picked != currency:
			notes.append(
				_(
					"Online payments are charged in {0}. Your card provider converts it to {1}, usually at a small cost. "
					"To pay in {1}, choose bank transfer."
				).format(currency, picked)
				if picked in bank_currencies()
				else _("Online payments are charged in {0}. Your card provider converts it.").format(currency)
			)
	if quote.currency != quote.company_currency:
		notes.append(
			_("Converted from {0} at {1}").format(
				quote.company_currency,
				f"1 {quote.company_currency} = {flt(quote.exchange_rate, 4):g} {quote.currency}",
			)
		)

	def option_amount(option):
		amount = option["customer_amount"]
		if amount:
			amount = flt(amount * factor(), order.precision("grand_total"))
		return money(amount, currency) if amount else _("Free")

	# each product's amount as the summary lists it: in the order currency, with tax when shown so,
	# a line sent from several warehouses counted once
	amounts: dict[str, float] = {}
	for row in order.items:
		if not is_charge_item(row.item_code):
			amounts[row.item_code] = amounts.get(row.item_code, 0) + flt(row.amount) * factor(row)

	return {
		"currency": currency,
		"export": quote.export,
		"lines": lines,
		"items": [
			{"item_code": code, "formatted_amount": money(amount, currency)}
			for code, amount in amounts.items()
		],
		"notes": notes,
		"total": quote.total,
		"formatted_total": money(quote.total, currency),
		"shipping_options": [
			{
				"id": option["id"],
				"label": option["label"],
				"eta": option.get("eta"),
				"formatted": option_amount(option),
				"selected": bool(quote.shipping and option["id"] == quote.shipping["id"]),
			}
			for option in quote.shipping_options
		],
		# an order sent in more than one parcel: a service is chosen for each
		"shipping_groups": [
			{
				"key": group.key,
				"label": parcel_label(group, index, len(quote.shipping_groups)),
				"items": ", ".join(f"{row['item_name']} \u00d7 {flt(row['qty']):g}" for row in group["items"]),
				"options": [
					{
						"id": option["id"],
						"label": option["label"],
						"eta": option.get("eta"),
						"formatted": option_amount(option),
						"selected": bool(group.chosen and option["id"] == group.chosen["id"]),
					}
					for option in group.options
				],
			}
			for index, group in enumerate(quote.shipping_groups, start=1)
		]
		if len(quote.shipping_groups) > 1
		else [],
		"shipping_messages": quote.shipping_messages,
		"shipping_pending": quote.shipping_pending,
		"can_ship": bool(quote.shipping),
		"payment_methods": payment_methods(quote.export),
		"payment_method": quote.payment_method,
		# every currency the store takes bank transfers in; one without Swift details is paid locally
		"bank_currencies": [
			{"currency": row.currency, "label": row.label or row.currency} for row in bank_accounts()
		],
		"bank_routes": bank_routes(currency, fee_factor(quote.export, factor()))
		if quote.payment_method in BANK_METHODS
		else [],
		"suggested_bank_method": suggested_bank_method(quote.address, currency)
		if quote.payment_method in BANK_METHODS
		else None,
	}


def is_charge_item(item_code: str) -> bool:
	"""Shipping and fee lines, which are not products."""
	s = settings()
	charges = ("shipping_item", "card_fee_item", "conversion_fee_item", "transfer_fee_item", "duties_item")
	return item_code in {s.get(field) for field in charges} - {None, ""}
