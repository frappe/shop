import re

import frappe
from frappe import _
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.api.products import default_item_group, receive_stock, save_product, set_price, unique_item_code
from shop.storefront import pricing, stock
from shop.storefront.checkout import elevated


@frappe.whitelist()
def get_attributes() -> list[dict]:
	"""Every reusable option set, e.g. Size with Small/Medium/Large."""
	only_managers()
	attributes = frappe.get_all("Item Attribute", pluck="name")
	return [
		{
			"attribute": attribute,
			"values": frappe.get_all(
				"Item Attribute Value",
				filters={"parent": attribute},
				order_by="idx",
				pluck="attribute_value",
			),
		}
		for attribute in attributes
	]


@frappe.whitelist(methods=["POST"])
def save_attribute(attribute: str, values: list) -> dict:
	only_managers()
	attribute = attribute.strip()
	doc = (
		frappe.get_doc("Item Attribute", attribute)
		if frappe.db.exists("Item Attribute", attribute)
		else frappe.new_doc("Item Attribute")
	)
	doc.attribute_name = attribute
	existing = {row.attribute_value: row for row in doc.item_attribute_values}
	used_abbr = {row.abbr for row in doc.item_attribute_values}
	for value in values:
		value = str(value).strip()
		if not value or value in existing:
			continue
		doc.append("item_attribute_values", {"attribute_value": value, "abbr": unique_abbr(value, used_abbr)})
	doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)
	return {"attribute": doc.name, "values": [row.attribute_value for row in doc.item_attribute_values]}


def unique_abbr(value: str, used: set) -> str:
	"""The value's abbreviation for variant codes: the value itself when it is short ("10 m" -> 10M),
	else its initials ("Extra Large" -> EL)."""
	compact = re.sub(r"[^A-Za-z0-9]", "", value).upper()
	base = (
		compact
		if len(compact) <= 5
		else "".join(part[0] for part in value.split())[:3].upper() or compact[:3]
	)
	abbr = base
	suffix = 1
	while abbr in used:
		suffix += 1
		abbr = f"{base}{suffix}"
	used.add(abbr)
	return abbr


@frappe.whitelist()
def get_variants(product: str) -> dict:
	only_managers()
	doc = frappe.get_doc("Shop Product", product)
	if not doc.has_variants:
		return {
			"has_variants": False,
			"options": [],
			"variants": [],
			"has_history": not can_add_options(doc.item),
		}
	items = frappe.get_all(
		"Item",
		filters={"variant_of": doc.item},
		fields=["name", "item_name", "disabled", "image"],
		order_by="name",
	)
	codes = [item.name for item in items]
	prices = pricing.get_prices(codes)
	quantities = stock.get_stock(codes)
	attribute_rows = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", codes]},
		fields=["parent", "attribute", "attribute_value"],
	)
	combos = {}
	for row in attribute_rows:
		combos.setdefault(row.parent, {})[row.attribute] = row.attribute_value
	from shop.storefront.product import option_order, variant_position

	options = option_order(doc.item, doc)
	items.sort(key=lambda item: variant_position({"attributes": combos.get(item.name, {})}, options))
	return {
		"has_variants": True,
		"options": product_options(doc),
		"default_variant": doc.default_variant,
		"track_stock": bool(frappe.get_cached_value("Item", doc.item, "is_stock_item")),
		"variants": [
			{
				"item_code": item.name,
				"item_name": item.item_name,
				"attributes": combos.get(item.name, {}),
				"price": prices.get(item.name, {}).get("rate"),
				"formatted_price": prices.get(item.name, {}).get("formatted"),
				"stock": quantities.get(item.name, 0),
				"disabled": item.disabled,
				"image": item.image,
			}
			for item in items
		],
		"missing_combinations": len(missing_combinations(doc)),
	}


def product_options(doc) -> list[dict]:
	"""Option values this product varies by, which is narrower than the global attribute."""
	if doc.options:
		return [
			{"attribute": row.attribute, "values": split_values(row.values)}
			for row in doc.options
			if split_values(row.values)
		]
	return options_from_variants(doc.item) or template_attribute_values(doc.item)


def split_values(raw: str | None) -> list[str]:
	return [value.strip() for value in (raw or "").split(",") if value.strip()]


def options_from_variants(template: str) -> list[dict]:
	codes = variant_codes(template)
	if not codes:
		return []
	rows = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", codes]},
		fields=["attribute", "attribute_value"],
		order_by="idx",
	)
	grouped = {}
	for row in rows:
		values = grouped.setdefault(row.attribute, [])
		if row.attribute_value not in values:
			values.append(row.attribute_value)
	order = frappe.get_all(
		"Item Variant Attribute", filters={"parent": template}, order_by="idx", pluck="attribute"
	)
	return [
		{"attribute": attribute, "values": order_values(attribute, grouped[attribute])}
		for attribute in order
		if attribute in grouped
	]


def order_values(attribute: str, values: list[str]) -> list[str]:
	catalogue = frappe.get_all(
		"Item Attribute Value", filters={"parent": attribute}, order_by="idx", pluck="attribute_value"
	)
	return [value for value in catalogue if value in values]


def template_attribute_values(template: str) -> list[dict]:
	rows = frappe.get_all(
		"Item Variant Attribute", filters={"parent": template}, fields=["attribute"], order_by="idx"
	)
	return [
		{
			"attribute": row.attribute,
			"values": frappe.get_all(
				"Item Attribute Value",
				filters={"parent": row.attribute},
				order_by="idx",
				pluck="attribute_value",
			),
		}
		for row in rows
	]


def can_add_options(item_code: str) -> bool:
	"""Whether the item can itself become the template: it has no stock or sales history."""
	if frappe.db.exists("Stock Ledger Entry", {"item_code": item_code, "is_cancelled": 0}):
		return False
	return not frappe.db.exists("Sales Order Item", {"item_code": item_code, "docstatus": ["<", 2]})


@frappe.whitelist(methods=["POST"])
def set_options(product: str, options: list, current: dict | None = None) -> dict:
	"""Define which option sets a product varies by, then build the combinations.

	A product with one version that has stock or sales stays that version: its item becomes the
	variant current names, under a new template. A new option gives the versions that exist the
	value current names for it. Either way their stock and history stay as they are."""
	only_managers()
	# ERPNext's variant code checks Item permissions, which the Shop Manager role doesn't have in Desk
	with elevated():
		doc = frappe.get_doc("Shop Product", product)
		item = frappe.get_doc("Item", doc.item)
		current = current or {}
		for option in options:
			save_attribute(option["attribute"], option.get("values") or [])
		if not item.has_variants and not can_add_options(item.name):
			values = {option["attribute"]: chosen(option, current) for option in options}
			template = template_from(item, options)
			item.variant_of = template.name
			item.set("attributes", [])
			for option in options:
				item.append(
					"attributes",
					{"attribute": option["attribute"], "attribute_value": values[option["attribute"]]},
				)
			item.flags.ignore_permissions = True
			try:
				item.save(ignore_permissions=True)
			except frappe.CannotChangeConstantError:
				frappe.throw(
					_(
						"This version of ERPNext can't make an item with stock or sales a variant. Update ERPNext to add options to this product."
					)
				)
			doc.item = template.name
			doc.default_variant = item.name
		else:
			existing = variant_codes(item.name) if item.has_variants else []
			known = {row.attribute for row in item.get("attributes")}
			added = [option for option in options if option["attribute"] not in known]
			values = {option["attribute"]: chosen(option, current) for option in added} if existing else {}
			item.has_variants = 1
			item.set("attributes", [])
			for option in options:
				item.append("attributes", {"attribute": option["attribute"]})
			item.flags.ignore_permissions = True
			item.save(ignore_permissions=True)
			for code in existing:
				variant = frappe.get_doc("Item", code)
				for attribute, value in values.items():
					variant.append("attributes", {"attribute": attribute, "attribute_value": value})
				if values:
					variant.flags.ignore_permissions = True
					variant.save(ignore_permissions=True)
		doc.has_variants = 1
		store_options(doc, options)
		return generate(product)


def chosen(option: dict, current: dict) -> str:
	"""The value an option takes on the versions that exist, from those it offers."""
	value = current.get(option["attribute"])
	if not value or value not in (option.get("values") or []):
		frappe.throw(_("Choose the {0} of the version you sell now").format(frappe.bold(option["attribute"])))
	return value


def template_from(item, options: list):
	"""A new template for an item with stock or sales: a copy of it, with the options and a code of
	its own, so the item keeps its code, stock and history as one of its variants."""
	template = frappe.copy_doc(item)
	code = f"{item.name}-V"
	suffix = 1
	while frappe.db.exists("Item", code):
		suffix += 1
		code = f"{item.name}-V{suffix}"
	template.update(
		{
			"item_code": code,
			"item_name": item.item_name,
			"has_variants": 1,
			"variant_of": None,
			"variant_based_on": "Item Attribute",
			"opening_stock": 0,
			"valuation_rate": 0,
		}
	)
	template.set("barcodes", [])
	template.set("attributes", [{"attribute": option["attribute"]} for option in options])
	template.flags.ignore_permissions = True
	return template.insert(ignore_permissions=True)


def store_options(doc, options: list) -> None:
	doc.options = []
	for option in options:
		doc.append(
			"options",
			{"attribute": option["attribute"], "values": ", ".join(option.get("values") or [])},
		)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def generate(product: str, price: float | None = None, opening_stock: float = 0) -> dict:
	"""Create every option combination that does not exist yet."""
	only_managers()
	doc = frappe.get_doc("Shop Product", product)
	settings = frappe.get_cached_doc("Shop Settings")
	template_price = flt(price) or fallback_price(doc.item)
	with elevated():
		make_combinations(doc, template_price, opening_stock, settings)
	return get_variants(product)


def make_combinations(doc, template_price: float, opening_stock: float, settings) -> None:
	for combination in missing_combinations(doc):
		from erpnext.controllers.item_variant import create_variant

		variant = create_variant(doc.item, combination)
		variant.flags.ignore_permissions = True
		variant.insert(ignore_permissions=True)
		if template_price:
			set_price(variant.name, template_price)
		if flt(opening_stock) > 0 and variant.is_stock_item:
			receive_stock(variant.name, flt(opening_stock), settings)


def fallback_price(template: str) -> float:
	"""Price new variants from their siblings, or from the item's own price when it has none."""
	rates = [entry["rate"] for entry in pricing.get_prices(variant_codes(template)).values()]
	if rates:
		return min(rates)
	return (pricing.get_price(template) or {}).get("rate") or 0


def variant_codes(template: str) -> list[str]:
	return frappe.get_all("Item", filters={"variant_of": template}, pluck="name")


def missing_combinations(doc) -> list[dict]:
	from itertools import product as cartesian

	options = product_options(doc)
	if not options:
		return []
	existing = set()
	for code in variant_codes(doc.item):
		rows = frappe.get_all(
			"Item Variant Attribute", filters={"parent": code}, fields=["attribute", "attribute_value"]
		)
		existing.add(tuple(sorted((row.attribute, row.attribute_value) for row in rows)))
	combinations = []
	for values in cartesian(*[option["values"] for option in options]):
		combo = dict(zip([option["attribute"] for option in options], values, strict=True))
		if tuple(sorted(combo.items())) not in existing:
			combinations.append(combo)
	return combinations


@frappe.whitelist(methods=["POST"])
def set_default_variant(product: str, item_code: str | None = None) -> dict:
	"""The variant the product page opens on; none opens it on the first available one."""
	only_managers()
	doc = frappe.get_doc("Shop Product", product)
	doc.default_variant = item_code or None
	doc.save(ignore_permissions=True)
	return get_variants(product)


@frappe.whitelist(methods=["POST"])
def update_variant(
	item_code: str,
	price: float | None = None,
	stock: float | None = None,
	disabled: bool | None = None,
	image: str | None = None,
) -> dict:
	only_managers()
	product = frappe.db.get_value(
		"Shop Product", {"item": frappe.db.get_value("Item", item_code, "variant_of")}
	)
	if price is not None:
		set_price(item_code, flt(price))
	if disabled is not None:
		frappe.db.set_value("Item", item_code, "disabled", 1 if disabled else 0)
	if image is not None:
		frappe.db.set_value("Item", item_code, "image", image or None)
	if stock is not None:
		from shop.api.inventory import set_stock

		set_stock(item_code, flt(stock))
	return get_variants(product)


@frappe.whitelist(methods=["POST"])
def create_variant_product(
	product_name: str,
	options: list,
	price: float,
	opening_stock: float = 0,
	short_description: str | None = None,
	description: str | None = None,
	images: list | None = None,
	collections: list | None = None,
	published: bool = True,
	item_group: str | None = None,
	track_stock: bool = True,
) -> dict:
	"""Create a product that varies by options, with every combination ready to sell."""
	only_managers()
	for option in options:
		save_attribute(option["attribute"], option.get("values") or [])
	item_code = unique_item_code(product_name)
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": product_name,
			"item_group": item_group or default_item_group(),
			"stock_uom": "Nos",
			"is_stock_item": 1 if track_stock else 0,
			"has_variants": 1,
			"description": short_description or product_name,
		}
	)
	for option in options:
		item.append("attributes", {"attribute": option["attribute"]})
	item.insert(ignore_permissions=True)
	product = save_product(
		{
			"item": item_code,
			"product_name": product_name,
			"short_description": short_description,
			"description": description,
			"images": images or [],
			"collections": collections or [],
			"published": published,
		}
	)
	store_options(frappe.get_doc("Shop Product", product["name"]), options)
	generate(product["name"], price=flt(price), opening_stock=cint(opening_stock))
	return {"product": product["name"], **get_variants(product["name"])}
