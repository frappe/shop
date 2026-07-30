import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.website.utils import cleanup_page_name

from shop.api import only_managers
from shop.storefront import pricing, stock


@frappe.whitelist()
def get_products(
	search: str | None = None, status: str | None = None, start: int = 0, limit: int = 20
) -> dict:
	only_managers()
	filters = {}
	if status == "published":
		filters["published"] = 1
	elif status == "draft":
		filters["published"] = 0
	or_filters = None
	if search:
		term = f"%{search.strip()}%"
		or_filters = [["product_name", "like", term], ["slug", "like", term], ["item", "like", term]]
	products = frappe.get_all(
		"Shop Product",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "product_name", "slug", "item", "published", "ranking", "has_variants"],
		order_by="ranking desc, modified desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 100),
	)
	decorate(products)
	return {"products": products, "total": frappe.db.count("Shop Product", filters=filters)}


def decorate(products: list) -> None:
	for product in products:
		product["image"] = frappe.db.get_value(
			"Shop Product Image", {"parent": product.name}, "image", order_by="idx"
		)
		codes = sellable_codes(product.item, product.has_variants)
		prices = pricing.get_prices(codes)
		rates = [entry["rate"] for entry in prices.values()]
		product["formatted_price"] = pricing.format_amount(min(rates)) if rates else None
		product["stock"] = sum(stock.get_stock(codes).values())


def sellable_codes(item: str, has_variants: bool) -> list[str]:
	if has_variants:
		return frappe.get_all("Item", filters={"variant_of": item}, pluck="name")
	return [item]


@frappe.whitelist()
def get_product(name: str) -> dict:
	only_managers()
	doc = frappe.get_doc("Shop Product", name)
	codes = sellable_codes(doc.item, doc.has_variants)
	prices = pricing.get_prices(codes)
	stock_map = stock.get_stock(codes)
	return {
		"name": doc.name,
		"item": doc.item,
		"product_name": doc.product_name,
		"slug": doc.slug,
		"published": doc.published,
		"ranking": doc.ranking,
		"short_description": doc.short_description,
		"description": doc.description,
		"compare_at_price": doc.compare_at_price,
		"highlights": doc.highlights,
		"has_variants": doc.has_variants,
		"images": [{"image": row.image, "alt_text": row.alt_text} for row in doc.images],
		"collections": [row.collection for row in doc.collections],
		"price": prices.get(doc.item, {}).get("rate") if not doc.has_variants else None,
		"variants": [
			{
				"item_code": code,
				"price": prices.get(code, {}).get("rate"),
				"stock": stock_map.get(code, 0),
			}
			for code in codes
		],
		"stock": sum(stock_map.values()),
	}


@frappe.whitelist(methods=["POST"])
def save_product(payload: dict) -> dict:
	only_managers()
	doc = (
		frappe.get_doc("Shop Product", payload["name"])
		if payload.get("name")
		else frappe.new_doc("Shop Product")
	)
	if not payload.get("name"):
		doc.item = payload["item"]
	doc.product_name = payload.get("product_name") or doc.product_name
	doc.short_description = payload.get("short_description")
	doc.description = payload.get("description")
	doc.compare_at_price = flt(payload.get("compare_at_price")) or None
	doc.highlights = payload.get("highlights")
	doc.ranking = cint(payload.get("ranking"))
	doc.published = 1 if payload.get("published") else 0
	if payload.get("slug"):
		doc.slug = cleanup_page_name(payload["slug"])
	set_images(doc, payload.get("images"))
	set_collections(doc, payload.get("collections"))
	doc.save(ignore_permissions=True) if doc.get("name") and not doc.is_new() else doc.insert(
		ignore_permissions=True
	)
	if payload.get("price") is not None and not doc.has_variants:
		set_price(doc.item, flt(payload["price"]))
	return get_product(doc.name)


def set_images(doc, images) -> None:
	if images is None:
		return
	doc.images = []
	for image in images:
		url = image if isinstance(image, str) else image.get("image")
		if url:
			doc.append("images", {"image": url, "alt_text": doc.product_name})


def set_collections(doc, collections) -> None:
	if collections is None:
		return
	doc.collections = []
	for collection in collections:
		doc.append("collections", {"collection": collection})


def set_price(item_code: str, rate: float) -> None:
	settings = frappe.get_cached_doc("Shop Settings")
	name = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": settings.price_list})
	if name:
		frappe.db.set_value("Item Price", name, "price_list_rate", rate)
		return
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": item_code,
			"price_list": settings.price_list,
			"price_list_rate": rate,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def create_product(
	product_name: str,
	price: float,
	description: str | None = None,
	short_description: str | None = None,
	compare_at_price: float | None = None,
	opening_stock: float = 0,
	images: list | None = None,
	collections: list | None = None,
	published: bool = True,
) -> dict:
	"""Create the ERPNext Item, its price and stock, and the storefront product in one step."""
	only_managers()
	settings = frappe.get_cached_doc("Shop Settings")
	item_code = unique_item_code(product_name)
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": product_name,
			"item_group": item_group(),
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"description": short_description or product_name,
		}
	).insert(ignore_permissions=True)
	set_price(item_code, flt(price))
	if flt(opening_stock) > 0:
		receive_stock(item_code, flt(opening_stock), flt(price), settings)
	return save_product(
		{
			"item": item_code,
			"product_name": product_name,
			"short_description": short_description,
			"description": description,
			"compare_at_price": compare_at_price,
			"images": images or [],
			"collections": collections or [],
			"published": published,
		}
	)


def unique_item_code(product_name: str) -> str:
	base = cleanup_page_name(product_name).upper()[:30] or "PRODUCT"
	code = base
	suffix = 2
	while frappe.db.exists("Item", code):
		code = f"{base}-{suffix}"
		suffix += 1
	return code


def item_group() -> str:
	for group in ("Products", "All Item Groups"):
		if frappe.db.exists("Item Group", group):
			return group
	return frappe.db.get_value("Item Group", {}, "name")


def receive_stock(item_code: str, qty: float, rate: float, settings) -> None:
	entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": settings.company,
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"t_warehouse": settings.default_warehouse,
					"basic_rate": rate * 0.6,
					"allow_zero_valuation_rate": 1,
				}
			],
		}
	)
	entry.flags.ignore_permissions = True
	entry.submit()


@frappe.whitelist(methods=["POST"])
def set_published(name: str, published: bool) -> None:
	only_managers()
	frappe.db.set_value("Shop Product", name, "published", 1 if published else 0)


@frappe.whitelist(methods=["POST"])
def delete_product(name: str) -> None:
	only_managers()
	for review in frappe.get_all("Shop Review", filters={"product": name}, pluck="name"):
		frappe.delete_doc("Shop Review", review, ignore_permissions=True, force=True)
	frappe.delete_doc("Shop Product", name, ignore_permissions=True)


@frappe.whitelist()
def get_collections() -> list[dict]:
	only_managers()
	collections = frappe.get_all(
		"Shop Collection",
		fields=["name", "title", "slug", "description", "image", "published", "ranking"],
		order_by="ranking desc, title asc",
	)
	for collection in collections:
		collection["product_count"] = frappe.db.count(
			"Shop Product Collection", {"collection": collection.name}
		)
	return collections


@frappe.whitelist(methods=["POST"])
def save_collection(payload: dict) -> None:
	only_managers()
	doc = (
		frappe.get_doc("Shop Collection", payload["name"])
		if payload.get("name")
		else frappe.new_doc("Shop Collection")
	)
	doc.title = payload["title"]
	doc.description = payload.get("description")
	doc.image = payload.get("image")
	doc.ranking = cint(payload.get("ranking"))
	doc.published = 1 if payload.get("published") else 0
	doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def delete_collection(name: str) -> None:
	only_managers()
	frappe.delete_doc("Shop Collection", name, ignore_permissions=True)
