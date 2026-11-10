"""Shipping options at checkout: the store's flat rate and the rates of the shipping apps listed
in the `shop_shipping_rate_providers` hook (see docs/extending.md). Amounts are in the company
currency, and the option charged is the one the server quoted, never one sent by the browser."""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money, now_datetime, time_diff_in_seconds

FLAT_RATE_ID = "flat"
QUOTE_TTL_SECONDS = 30 * 60
ADDRESS_KEYS = ("address_line1", "address_line2", "city", "state", "pincode", "country")


def normalize_address(address: dict | None) -> frappe._dict:
	address = frappe._dict(address or {})
	clean = frappe._dict({key: (address.get(key) or "").strip() for key in ADDRESS_KEYS})
	if clean.country:
		clean.country = valid_country(clean.country)
	clean.country_code = (
		(frappe.db.get_value("Country", clean.country, "code") or "").upper() if clean.country else ""
	)
	return clean


def valid_country(country: str) -> str:
	if frappe.db.exists("Country", country):
		return country
	by_code = frappe.db.get_value("Country", {"code": country.lower()})
	if by_code:
		return by_code
	frappe.throw(_("{0} is not a country we know").format(frappe.bold(country)))


def is_complete(address: frappe._dict) -> bool:
	return bool(address.address_line1 and address.city and address.country)


def quote_key(cart, address: frappe._dict, parcel: frappe._dict | None = None) -> str:
	if parcel:
		items = sorted((row["item_code"], flt(row["qty"])) for row in parcel["items"])
		origin = [parcel.warehouse, parcel.ship_from, parcel.provider]
	else:
		items = sorted((row.item_code, flt(row.qty)) for row in cart.items)
		origin = []
	raw = json.dumps([items, [address.get(key) for key in ADDRESS_KEYS], origin], sort_keys=True)
	return hashlib.sha256(raw.encode()).hexdigest()[:20]


def parcels(order) -> list[frappe._dict]:
	"""The goods of an order that are sent, by the warehouse they are sent from (in the store's
	order): one parcel each, quoted on its own."""
	from shop.storefront.stock import is_stock_item, location, warehouses
	from shop.storefront.totals import is_charge_item

	groups: dict = {}
	for row in order.items:
		if not is_charge_item(row.item_code):
			groups.setdefault(row.warehouse or None, []).append(row)
	order_of = {name: index for index, name in enumerate(warehouses())}
	result = []
	for warehouse in sorted(groups, key=lambda name: order_of.get(name, len(order_of))):
		rows = groups[warehouse]
		if not any(is_stock_item(row.item_code) for row in rows):
			continue  # nothing in it is sent
		place = location(warehouse)
		result.append(
			frappe._dict(
				key=warehouse or "",
				warehouse=warehouse,
				provider=place.provider if place else None,
				ship_from=place.ship_from if place else None,
				items=[
					{"item_code": row.item_code, "item_name": row.item_name, "qty": flt(row.qty), "rate": flt(row.rate)}
					for row in rows
				],
				subtotal=sum(flt(row.base_net_amount) for row in rows),
			)
		)
	return result


def get_options(
	cart,
	address: frappe._dict,
	subtotal: float,
	refresh: bool = False,
	parcel: frappe._dict | None = None,
	first: bool = True,
) -> dict:
	"""Shipping options for this cart and address: {"options": [...], "messages": [...]}.

	Rates from shipping providers are cached on the cart for half an hour, keyed by the items and
	address; an answer without rates (a provider busy or down) is asked again next time. The store's
	flat rate depends on the order value, so it is worked out every time."""
	if not is_complete(address):
		return {"options": [], "messages": [], "pending": True}
	if not parcel and not ships(cart):
		return {
			"options": [
				{"id": FLAT_RATE_ID, "label": _("No delivery needed"), "amount": 0.0, "tax_included": True}
			],
			"messages": [],
		}
	held = unsendable(parcel["items"] if parcel else cart.items, address.country)
	if held:
		pickup = pickup_option(parcel)
		return {
			"options": [pickup] if pickup else [],
			"messages": [_("{0} can't be sent to {1}.").format(", ".join(held), _(address.country))],
		}
	key = quote_key(cart, address, parcel)
	cached = cached_quotes(cart).get(key) or {}
	if not refresh and fresh(cached):
		options, messages, active = cached["options"], cached.get("messages", []), cached.get("active", False)
	else:
		options, messages, active = provider_options(cart, address, subtotal, parcel)
		if options:
			store_quotes(
				cart,
				key,
				{
					"created": str(now_datetime()),
					"options": options,
					"messages": messages,
					"active": active,
				},
			)
	options = list(options)
	flat = flat_rate_option(subtotal)
	if flat:
		# the flat rate is for the order: further parcels go at no extra charge
		options.append(flat if first else dict(flat, amount=0.0))
	options = with_surcharges(
		options,
		address,
		parcel_goods(parcel["items"] if parcel else cart.items, parcel.subtotal if parcel else subtotal),
	)
	pickup = pickup_option(parcel)
	if pickup:
		options.append(pickup)
	if not options and not active and not messages:
		# a store with no shipping set up ships for free
		options.append({"id": FLAT_RATE_ID, "label": _("Free shipping"), "amount": 0.0, "tax_included": True})
	options.sort(key=lambda option: option["amount"])
	return {"options": options, "messages": messages}


def shipping_restriction(item_code: str):
	"""Where an item can be sent: its own Shop Shipping Restriction, else its template's, else the
	nearest Item Group's up the tree."""
	item = frappe.get_cached_value(
		"Item", item_code, ["shop_shipping_restriction", "variant_of", "item_group"], as_dict=True
	)
	if not item:
		return None
	name = item.shop_shipping_restriction
	if not name and item.variant_of:
		name = frappe.get_cached_value("Item", item.variant_of, "shop_shipping_restriction")
	group = item.item_group
	while not name and group:
		name, group = frappe.get_cached_value(
			"Item Group", group, ["shop_shipping_restriction", "parent_item_group"]
		) or (None, None)
	return frappe.get_cached_doc("Shop Shipping Restriction", name) if name else None


def can_send(item_code: str, country: str | None) -> bool:
	"""Whether the item, and every part of it when it is a Product Bundle, can be sent there."""
	from shop.storefront.stock import bundle_parts

	for code in [item_code, *(part for part, _qty in bundle_parts(item_code))]:
		restriction = shipping_restriction(code)
		if restriction and not restriction.allows(country):
			return False
	return True


def unsendable(rows, country: str | None) -> list[str]:
	"""The names of the goods among these rows that are sent but can't be sent to the country."""
	from shop.storefront.stock import is_stock_item

	names = []
	for row in rows:
		code = row.get("item_code")
		if is_stock_item(code) and not can_send(code, country):
			names.append(row.get("item_name") or frappe.get_cached_value("Item", code, "item_name") or code)
	return list(dict.fromkeys(names))


def surcharges() -> list:
	"""The store's enabled shipping surcharges."""
	return [
		frappe.get_cached_doc("Shop Shipping Surcharge", name)
		for name in frappe.get_all(
			"Shop Shipping Surcharge", filters={"enabled": 1}, pluck="name", order_by="surcharge_name"
		)
	]


def parcel_goods(rows, value: float) -> dict:
	"""What surcharges look at in a parcel: the weight of its goods and their value."""
	weight = sum(
		flt(row.get("qty")) * flt(frappe.get_cached_value("Item", row.get("item_code"), "weight_per_unit"))
		for row in rows
	)
	return {"weight": weight, "value": flt(value)}


def with_surcharges(options: list[dict], address: frappe._dict, goods: dict) -> list[dict]:
	"""Delivery options with the surcharges that match them added to their price and named in
	their label."""
	rules = surcharges()
	if not rules:
		return options
	settings = frappe.get_cached_doc("Shop Settings")
	home = frappe.get_cached_value("Company", settings.company, "country")
	from shop.storefront.totals import added_rate, included_rate

	rate = (included_rate if settings.prices_include_tax else added_rate)(settings.tax_template)
	tax_factor = 1 + rate / 100
	result = []
	for option in options:
		applied = [rule for rule in rules if rule.matches(address, home, goods, option)]
		if not applied:
			result.append(option)
			continue
		extra = sum(rule.charge(option, tax_factor) for rule in applied)
		result.append(
			dict(
				option,
				amount=flt(option["amount"]) + extra,
				label=_("{0} (incl. {1})").format(option["label"], ", ".join(rule.label for rule in applied)),
				surcharges=[rule.name for rule in applied],
			)
		)
	return result


def ships(cart) -> bool:
	"""Whether anything in the cart is sent: services aren't (a Product Bundle is sent when any of
	its parts is)."""
	from shop.storefront.stock import is_stock_item

	return any(is_stock_item(row.item_code) for row in cart.items)


def provider_options(
	cart, address: frappe._dict, subtotal: float, parcel: frappe._dict | None = None
) -> tuple[list[dict], list[str], bool]:
	"""Rates from the shop_shipping_rate_providers hooks, the messages they gave, and whether any
	of them is switched on. A parcel is quoted with its own goods, from its warehouse and address,
	and says who sends it (location_provider), so a rate provider quotes only what it sends."""
	settings = frappe.get_cached_doc("Shop Settings")
	context = frappe._dict(
		cart_items=[
			{"item_code": row["item_code"], "qty": flt(row["qty"]), "rate": flt(row["rate"])}
			for row in parcel["items"]
		]
		if parcel
		else [{"item_code": row.item_code, "qty": flt(row.qty), "rate": flt(row.rate)} for row in cart.items],
		address=address,
		subtotal=parcel.subtotal if parcel else subtotal,
		company=settings.company,
		currency=frappe.get_cached_value("Company", settings.company, "default_currency"),
		warehouse=parcel.warehouse if parcel else None,
		ship_from=parcel.ship_from if parcel else None,
		location_provider=parcel.provider if parcel else None,
	)
	options, messages = [], []
	active = False  # a provider that is switched off returns None
	for path in frappe.get_hooks("shop_shipping_rate_providers") or []:
		try:
			result = frappe.get_attr(path)(context)
			if result is None:
				continue
			active = True
		except frappe.ValidationError as error:
			messages.append(str(error))
			frappe.clear_messages()
			continue
		except Exception:
			frappe.log_error(title=f"Shipping rates failed: {path}")
			continue
		if isinstance(result, dict):
			messages.extend(result.get("messages") or [])
			result = result.get("options") or []
		for option in result or []:
			options.append(clean_option(option))
	return options, list(dict.fromkeys(messages)), active


def clean_option(option: dict) -> dict:
	return {
		"id": str(option["id"])[:140],
		"label": str(option.get("label") or option["id"])[:140],
		"amount": flt(option.get("amount"), 2),
		"tax_included": bool(option.get("tax_included")),
		"carrier": option.get("carrier"),
		"service": option.get("service"),
		"eta": option.get("eta"),
		"meta": option.get("meta") or {},
	}


def free_shipping_note() -> str | None:
	settings = frappe.get_cached_doc("Shop Settings")
	threshold = flt(settings.get("free_shipping_above"))
	if not threshold or not flat_rate_option(0):
		return None
	return _("Free shipping on orders over {0}").format(fmt_money(threshold, currency=settings.currency))


PICKUP_PREFIX = "pickup:"


def pickup_option(parcel: frappe._dict | None) -> dict | None:
	"""Collecting the parcel from its location, when the store lets customers collect there."""
	from shop.storefront.stock import location

	place = location(parcel.warehouse) if parcel else None
	if not place or not place.allow_pickup:
		return None
	return {
		"id": PICKUP_PREFIX + place.warehouse,
		"label": _("Collect from {0}").format(place.label),
		"amount": 0.0,
		"tax_included": True,
		"carrier": None,
		"service": None,
		"eta": None,
		"meta": {"pickup": place.warehouse},
	}


def is_pickup(option: dict | None) -> bool:
	return bool(option) and str(option.get("id") or "").startswith(PICKUP_PREFIX)


def flat_rate_option(subtotal: float) -> dict | None:
	settings = frappe.get_cached_doc("Shop Settings")
	rate = flt(settings.get("flat_shipping_rate"))
	if not rate or not (settings.get("shipping_account") or settings.get("shipping_item")):
		return None
	threshold = flt(settings.get("free_shipping_above"))
	free = bool(threshold and subtotal >= threshold)
	return {
		"id": FLAT_RATE_ID,
		"label": _("Free shipping") if free else _("Standard shipping"),
		"amount": 0.0 if free else rate,
		# the flat rate is entered the same way as the store's prices
		"tax_included": bool(settings.get("prices_include_tax")),
		"carrier": None,
		"service": None,
		"eta": None,
		"meta": {},
	}


def cached_quotes(cart) -> dict:
	"""The cart's recent quotes, by quote key (one per parcel and address)."""
	try:
		cached = json.loads(cart.get("shipping_quotes") or "{}")
	except ValueError:
		return {}
	if "key" in cached:
		# one quote, as kept before parcels
		return {cached["key"]: cached}
	return cached


def fresh(cached: dict) -> bool:
	created = cached.get("created")
	return bool(created) and time_diff_in_seconds(now_datetime(), created) < QUOTE_TTL_SECONDS


def store_quotes(cart, key: str, quote: dict) -> None:
	quotes = {k: v for k, v in cached_quotes(cart).items() if fresh(v)}
	quotes[key] = quote
	cart.shipping_quotes = json.dumps(quotes, default=str)
	if not cart.is_new():
		cart.db_set("shipping_quotes", cart.shipping_quotes, update_modified=False)


def find_option(options: list[dict], option_id: str | None) -> dict | None:
	for option in options:
		if option["id"] == option_id:
			return option
	return None


def remember_choice(cart, choice: str | dict | None) -> None:
	"""The shopper's shipping choice: an option id, or one per parcel {warehouse: option id}."""
	value = json.dumps(choice, sort_keys=True) if isinstance(choice, dict) else choice
	if cint(bool(value)) and cart.get("shipping_rate") != value:
		cart.db_set("shipping_rate", value, update_modified=False)


def parse_choice(value) -> dict | str | None:
	"""A shipping choice as the browser or the cart has it: an option id, or {parcel key: id}."""
	if isinstance(value, dict):
		return value
	if isinstance(value, str) and value.startswith("{"):
		try:
			return json.loads(value)
		except ValueError:
			return None
	return value or None
