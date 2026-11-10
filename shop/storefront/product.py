import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import flt

from shop.storefront import pricing, stock


def specifications(doc) -> list[dict]:
	"""The product's specifications as the page lists them, each value with its unit."""
	units = dict(
		frappe.get_all(
			"Shop Specification",
			filters={"name": ["in", [row.specification for row in doc.specifications] or [""]]},
			fields=["name", "unit"],
			as_list=True,
		)
	)
	return [
		{
			"label": row.specification,
			"value": f"{row.value} {units[row.specification]}" if units.get(row.specification) else row.value,
		}
		for row in doc.specifications
	]


@frappe.whitelist(allow_guest=True)
def get_product(slug: str) -> dict:
	name = frappe.db.get_value("Shop Product", {"slug": slug, "published": 1})
	if not name:
		frappe.throw(frappe._("Product not found"), frappe.DoesNotExistError)
	doc = frappe.get_doc("Shop Product", name)
	from shop.storefront import reviews

	payload = {
		"name": doc.name,
		"product_name": doc.product_name,
		"slug": doc.slug,
		"item": doc.item,
		"short_description": doc.short_description,
		"description": doc.description,
		"has_variants": doc.has_variants,
		"compare_at_price": doc.compare_at_price,
		"highlights": [
			{"label": line.strip()} for line in (doc.highlights or "").splitlines() if line.strip()
		],
		"images": [{"image": row.image, "alt_text": row.alt_text} for row in doc.images],
		"specifications": specifications(doc) or None,
		"collections": product_collections(doc),
		"rating": reviews.summary(doc.name),
	}
	if doc.has_variants:
		payload.update(variant_details(doc.item, doc.compare_at_price, doc))
	else:
		price = pricing.get_price(doc.item) or {}
		if price.get("retail"):  # a trade or customer price: show the store price struck through
			payload["compare_at_price"] = max(flt(doc.compare_at_price), flt(price["retail"]))
		available = stock.availability(doc.item, priced=price.get("rate") is not None)
		payload.update(
			{
				"price": price.get("rate"),
				"formatted_price": price.get("display"),
				"price_note": price.get("display_excl"),
				"in_stock": available["purchasable"],
				**available,
			}
		)
	from shop.storefront.catalog import apply_compare_at, star_string

	apply_compare_at(payload, payload.get("price"))
	if payload["rating"]["count"]:
		payload["rating"]["stars"] = star_string(payload["rating"]["average"])
	return payload


def product_collections(doc) -> list[dict]:
	collections = [row.collection for row in doc.collections]
	if not collections:
		return []
	return frappe.get_all(
		"Shop Collection",
		filters={"name": ["in", collections], "published": 1},
		fields=["title", "slug"],
	)


def variant_details(template: str, compare_at: float | None = None, doc=None) -> dict:
	"""A product's variants in the order of its option values, and the one its page opens on: the
	product's default variant when it can be bought, else the first that can."""
	options = option_order(template, doc)
	variants = sorted(load_variants(template, compare_at), key=lambda v: variant_position(v, options))
	rates = [v["price"] for v in variants if v["price"] is not None]
	chosen = next((v for v in variants if doc and v["item_code"] == doc.get("default_variant")), None)
	default = (
		chosen
		if chosen and chosen["purchasable"]
		else next((v for v in variants if v["purchasable"]), variants[0] if variants else None)
	)
	return {
		"attributes": [
			{
				"attribute": attribute,
				"values": [v for v in values if any(x["attributes"].get(attribute) == v for x in variants)],
			}
			for attribute, values in options
		],
		"variants": variants,
		"price": min(rates) if rates else None,
		"formatted_price": pricing.display_price(min(rates), pricing.item_tax_rate(template))
		if rates
		else None,
		"price_note": pricing.display_price_without_tax(min(rates), pricing.item_tax_rate(template))
		if rates
		else None,
		"in_stock": any(v["purchasable"] for v in variants),
		"purchasable": bool(default and default["purchasable"]),
		"stock_status": default["stock_status"] if default else _("Not available online"),
		"stock_state": default["stock_state"] if default else "unavailable",
		"stock_locations_html": default.get("stock_locations_html") if default else None,
		"shipping_note": default.get("shipping_note") if default else None,
		"default_item_code": default["item_code"] if default else None,
		"unavailable_label": _("Not available"),
	}


def option_order(template: str, doc=None) -> list[tuple[str, list[str]]]:
	"""The product's options and their values in the order the store set them."""
	if doc:
		from shop.api.variants import product_options

		return [(row["attribute"], row["values"]) for row in product_options(doc)]
	return [(row["attribute"], row["values"]) for row in attribute_options(template, [])]


def variant_position(variant: dict, options: list[tuple[str, list[str]]]) -> tuple:
	position = []
	for attribute, values in options:
		value = variant["attributes"].get(attribute)
		position.append(values.index(value) if value in values else len(values))
	return tuple(position)


def load_variants(template: str, compare_at: float | None = None) -> list[dict]:
	rows = frappe.get_all("Item", filters={"variant_of": template, "disabled": 0}, fields=["name", "image"])
	items = [row.name for row in rows]
	images = {row.name: row.image for row in rows if row.image}
	prices = pricing.get_prices(items)
	attributes = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", items]},
		fields=["parent", "attribute", "attribute_value"],
	)
	variants = []
	for item_code in items:
		price = prices.get(item_code, {})
		variants.append(
			{
				"item_code": item_code,
				"attributes": {
					row.attribute: row.attribute_value for row in attributes if row.parent == item_code
				},
				"price": price.get("rate"),
				"formatted_price": price.get("display"),
				"price_note": price.get("display_excl"),
				**stock.availability(item_code, priced=price.get("rate") is not None),
				"image": images.get(item_code),
				**variant_savings(price.get("rate"), compare_at, item_code),
			}
		)
	return variants


def variant_savings(rate: float | None, compare_at: float | None, item_code: str | None = None) -> dict:
	from frappe.utils import flt

	if not rate or not compare_at or flt(compare_at) <= flt(rate):
		return {"formatted_savings": None, "discount_pct": None}
	saved = flt(compare_at) - flt(rate)
	return {
		"formatted_savings": pricing.display_amount(saved, pricing.item_tax_rate(item_code)),
		"discount_pct": round(saved * 100 / flt(compare_at)),
	}


def attribute_options(template: str, variants: list[dict]) -> list[dict]:
	order = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": template},
		fields=["attribute"],
		order_by="idx",
		pluck="attribute",
	)
	options = []
	for attribute in order:
		values = ordered_values(attribute)
		used = {v["attributes"].get(attribute) for v in variants}
		options.append({"attribute": attribute, "values": [v for v in values if v in used or not variants]})
	return options


def ordered_values(attribute: str) -> list[str]:
	return frappe.get_all(
		"Item Attribute Value",
		filters={"parent": attribute},
		order_by="idx",
		pluck="attribute_value",
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def alert_when_in_stock(item_code: str, email: str) -> dict:
	"""Email the shopper once when this item (a product's, or one of its variants) can be bought."""
	from frappe.utils import validate_email_address

	email = (email or "").strip().lower()
	if not validate_email_address(email):
		frappe.throw(_("Please enter a valid email address"))
	product = for_sale(item_code)
	if not product:
		frappe.throw(_("Product not found"), frappe.DoesNotExistError)
	if not frappe.db.exists(
		"Shop Stock Alert", {"email": email, "item_code": item_code, "sent_on": ["is", "not set"]}
	):
		frappe.get_doc(
			{"doctype": "Shop Stock Alert", "email": email, "item_code": item_code, "product": product}
		).insert(ignore_permissions=True)
	return {"message": _("We'll email {0} when it's back in stock.").format(email)}


def for_sale(item_code: str) -> str | None:
	"""The published product an item is sold as: its own, or its template's."""
	template = frappe.db.get_value("Item", item_code, "variant_of")
	return frappe.db.get_value("Shop Product", {"item": template or item_code, "published": 1})


def send_stock_alerts() -> None:
	"""Tell the shoppers waiting for items that can be bought again (Shop: Back in Stock)."""
	from frappe.utils import get_url, now_datetime

	from shop.routes import store_url
	from shop.storefront import emails

	waiting = frappe.get_all(
		"Shop Stock Alert", filters={"sent_on": ["is", "not set"]}, fields=["name", "item_code", "product"]
	)
	for item_code in {row.item_code for row in waiting}:
		if not stock.availability(item_code, priced=pricing.get_price(item_code) is not None).get(
			"purchasable"
		):
			continue
		for row in (row for row in waiting if row.item_code == item_code):
			alert = frappe.get_doc("Shop Stock Alert", row.name)
			slug = frappe.db.get_value("Shop Product", {"name": row.product, "published": 1}, "slug")
			if slug:
				emails.send(
					"back_in_stock",
					alert.email,
					alert,
					item_name=frappe.get_cached_value("Item", item_code, "item_name"),
					product_url=get_url(store_url(f"product/{slug}")),
				)
			alert.db_set("sent_on", now_datetime())
