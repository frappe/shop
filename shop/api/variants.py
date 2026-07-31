import frappe
from frappe import _
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.api.products import item_group, receive_stock, save_product, set_price, unique_item_code
from shop.storefront import pricing, stock


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
	base = "".join(part[0] for part in value.split())[:3].upper() or value[:3].upper()
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
		return {"has_variants": False, "options": [], "variants": [], "can_add_options": can_add_options(doc.item)}
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
	return {
		"has_variants": True,
		"options": product_options(doc),
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
	"""Options can only be introduced before an item has any stock or sales history."""
	if frappe.db.exists("Stock Ledger Entry", {"item_code": item_code, "is_cancelled": 0}):
		return False
	return not frappe.db.exists("Sales Order Item", {"item_code": item_code, "docstatus": ["<", 2]})


@frappe.whitelist(methods=["POST"])
def set_options(product: str, options: list) -> dict:
	"""Define which option sets a product varies by, then build the combinations."""
	only_managers()
	doc = frappe.get_doc("Shop Product", product)
	item = frappe.get_doc("Item", doc.item)
	if not item.has_variants and not can_add_options(item.name):
		frappe.throw(_("This product already has stock or orders, so options cannot be added now"))
	for option in options:
		save_attribute(option["attribute"], option.get("values") or [])
	item.has_variants = 1
	item.attributes = []
	for option in options:
		item.append("attributes", {"attribute": option["attribute"]})
	item.flags.ignore_permissions = True
	item.save(ignore_permissions=True)
	store_options(doc, options)
	frappe.db.set_value("Shop Product", product, "has_variants", 1)
	return generate(product)


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
	for combination in missing_combinations(doc):
		from erpnext.controllers.item_variant import create_variant

		variant = create_variant(doc.item, combination)
		variant.flags.ignore_permissions = True
		variant.insert(ignore_permissions=True)
		if template_price:
			set_price(variant.name, template_price)
		if flt(opening_stock) > 0:
			receive_stock(variant.name, flt(opening_stock), template_price or 1, settings)
	return get_variants(product)


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
def update_variant(
	item_code: str,
	price: float | None = None,
	stock: float | None = None,
	disabled: bool | None = None,
	image: str | None = None,
) -> dict:
	only_managers()
	product = frappe.db.get_value("Shop Product", {"item": frappe.db.get_value("Item", item_code, "variant_of")})
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
			"item_group": item_group(),
			"stock_uom": "Nos",
			"is_stock_item": 1,
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
