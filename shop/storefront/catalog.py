import frappe
from frappe.utils import cint, flt

from shop.storefront import pricing, stock

MAX_PAGE_SIZE = 60
MAX_CATALOG_SIZE = 500

SORT_ORDERS = {
	"ranking": "ranking desc, modified desc",
	"newest": "creation desc",
	"name": "product_name asc",
	"price_asc": None,
	"price_desc": None,
}


@frappe.whitelist(allow_guest=True)
def get_products(
	collection: str | None = None,
	search: str | None = None,
	sort: str = "ranking",
	start: int = 0,
	limit: int = 24,
	price_min: float | None = None,
	price_max: float | None = None,
	in_stock: bool = False,
) -> dict:
	filters = {"published": 1}
	if collection:
		filters["name"] = ["in", collection_members(collection)]
	products = frappe.get_all(
		"Shop Product",
		filters=filters,
		or_filters=search_filters(search),
		fields=[
			"name",
			"product_name",
			"slug",
			"short_description",
			"has_variants",
			"item",
			"compare_at_price",
		],
		order_by=SORT_ORDERS.get(sort) or SORT_ORDERS["ranking"],
		limit=MAX_CATALOG_SIZE,
	)
	decorate(products)
	products = apply_post_filters(products, price_min, price_max, in_stock)
	if sort in ("price_asc", "price_desc"):
		products.sort(key=lambda p: p.price if p.price is not None else float("inf"))
		if sort == "price_desc":
			products.reverse()
	start = cint(start)
	limit = min(cint(limit) or 24, MAX_PAGE_SIZE)
	return {"products": products[start : start + limit], "total": len(products)}


def apply_post_filters(products, price_min, price_max, in_stock):
	def keep(product):
		if price_min is not None and (product.price is None or product.price < flt(price_min)):
			return False
		if price_max is not None and (product.price is None or product.price >= flt(price_max)):
			return False
		if in_stock and not product.in_stock:
			return False
		return True

	return [product for product in products if keep(product)]


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
		row.image_css = tile_background(row.image)
	return collections


def tile_background(image: str | None) -> str | None:
	if not image:
		return None
	return f"url('{image}')"


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
	from shop.storefront import reviews

	images = first_images([p.name for p in products])
	prices = display_prices(products)
	availability = display_stock(products)
	ratings = reviews.summaries([p.name for p in products])
	for product in products:
		product.route = f"/product/{product.slug}"
		product.image = images.get(product.name)
		price = prices.get(product.item, {})
		product.price = price.get("rate")
		product.formatted_price = price.get("formatted")
		product.in_stock = availability.get(product.item, False)
		apply_compare_at(product, product.price)
		rating = ratings.get(product.name)
		product.rating_average = rating["average"] if rating else None
		product.rating_count = rating["count"] if rating else 0
		product.rating_stars = star_string(rating["average"]) if rating else None


def apply_compare_at(target, price) -> None:
	compare_at = flt(target.get("compare_at_price"))
	if not price or compare_at <= flt(price):
		target["compare_at_price"] = None
		return
	target["formatted_compare_at"] = pricing.format_amount(compare_at)
	target["discount_pct"] = round((compare_at - flt(price)) * 100 / compare_at)
	target["formatted_savings"] = pricing.format_amount(compare_at - flt(price))


def star_string(average: float) -> str:
	full = int(flt(average) + 0.5)
	return "★" * full + "☆" * (5 - full)


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
