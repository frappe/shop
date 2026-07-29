import frappe
from frappe.utils import cint

from shop.storefront import pricing, stock

MAX_PAGE_SIZE = 60

SORT_ORDERS = {
	"ranking": "ranking desc, modified desc",
	"newest": "creation desc",
	"name": "product_name asc",
}


@frappe.whitelist(allow_guest=True)
def get_products(
	collection: str | None = None,
	search: str | None = None,
	sort: str = "ranking",
	start: int = 0,
	limit: int = 24,
) -> dict:
	filters = {"published": 1}
	if collection:
		filters["name"] = ["in", collection_members(collection)]
	or_filters = search_filters(search)
	kwargs = {
		"filters": filters,
		"or_filters": or_filters,
		"fields": ["name", "product_name", "slug", "short_description", "has_variants", "item"],
	}
	products = frappe.get_all(
		"Shop Product",
		order_by=SORT_ORDERS.get(sort, SORT_ORDERS["ranking"]),
		start=cint(start),
		limit=min(cint(limit) or 24, MAX_PAGE_SIZE),
		**kwargs,
	)
	decorate(products)
	return {
		"products": products,
		"total": frappe.db.count("Shop Product", filters=filters)
		if not or_filters
		else len(frappe.get_all("Shop Product", filters=filters, or_filters=or_filters)),
	}


@frappe.whitelist(allow_guest=True)
def get_collections() -> list[dict]:
	collections = frappe.get_all(
		"Shop Collection",
		filters={"published": 1},
		fields=["name", "title", "slug", "description", "image"],
		order_by="ranking desc, title asc",
	)
	counts = collection_counts([c.name for c in collections])
	for row in collections:
		row.route = f"/collection/{row.slug}"
		row.product_count = counts.get(row.name, 0)
	return collections


def collection_members(slug: str) -> list[str]:
	collection = frappe.db.get_value("Shop Collection", {"slug": slug, "published": 1})
	if not collection:
		return []
	return frappe.get_all(
		"Shop Product Collection", filters={"collection": collection}, pluck="parent"
	)


def collection_counts(collections: list[str]) -> dict:
	if not collections:
		return {}
	from collections import Counter

	rows = frappe.get_all(
		"Shop Product Collection",
		filters={"collection": ["in", collections]},
		pluck="collection",
	)
	return Counter(rows)


def search_filters(search: str | None) -> list | None:
	if not search:
		return None
	term = f"%{search.strip()}%"
	return [
		["product_name", "like", term],
		["short_description", "like", term],
		["item", "like", term],
	]


def decorate(products: list) -> None:
	images = first_images([p.name for p in products])
	prices = display_prices(products)
	availability = display_stock(products)
	for product in products:
		product.route = f"/product/{product.slug}"
		product.image = images.get(product.name)
		price = prices.get(product.item, {})
		product.price = price.get("rate")
		product.formatted_price = price.get("formatted")
		product.in_stock = availability.get(product.item, False)


def first_images(product_names: list[str]) -> dict:
	if not product_names:
		return {}
	rows = frappe.get_all(
		"Shop Product Image",
		filters={"parent": ["in", product_names]},
		fields=["parent", "image"],
		order_by="parent, idx",
	)
	images = {}
	for row in rows:
		images.setdefault(row.parent, row.image)
	return images


def display_prices(products: list) -> dict:
	simple = [p.item for p in products if not p.has_variants]
	templates = [p.item for p in products if p.has_variants]
	prices = pricing.get_prices(simple)
	for template, codes in variants_by_template(templates).items():
		rates = [p["rate"] for code, p in pricing.get_prices(codes).items()]
		if rates:
			prices[template] = {"rate": min(rates), "formatted": pricing.format_amount(min(rates))}
	return prices


def display_stock(products: list) -> dict:
	settings = frappe.get_cached_doc("Shop Settings")
	if settings.allow_out_of_stock:
		return dict.fromkeys([p.item for p in products], True)
	simple = [p.item for p in products if not p.has_variants]
	availability = {code: qty > 0 for code, qty in stock.get_stock(simple).items()}
	templates = [p.item for p in products if p.has_variants]
	for template, codes in variants_by_template(templates).items():
		availability[template] = any(qty > 0 for qty in stock.get_stock(codes).values())
	return availability


def variants_by_template(templates: list[str]) -> dict[str, list[str]]:
	if not templates:
		return {}
	rows = frappe.get_all(
		"Item", filters={"variant_of": ["in", templates]}, fields=["name", "variant_of"]
	)
	grouped = {}
	for row in rows:
		grouped.setdefault(row.variant_of, []).append(row.name)
	return grouped
