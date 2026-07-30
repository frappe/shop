import frappe
from frappe.utils import cint

from shop.storefront import cart, catalog, checkout, orders, product

PAGE_SIZE = 24


@frappe.whitelist(allow_guest=True)
def home() -> dict:
	return {
		"store": store_details(),
		"collections": catalog.get_collections(),
		"featured_products": catalog.get_products(limit=8)["products"],
	}


@frappe.whitelist(allow_guest=True)
def listing() -> dict:
	form = frappe.form_dict
	page = max(cint(form.get("page")) or 1, 1)
	price_min, price_max = parse_price_bucket(form.get("price"))
	collections = catalog.get_collections()
	result = catalog.get_products(
		collection=form.get("collection"),
		search=form.get("search"),
		sort=form.get("sort") or "ranking",
		start=(page - 1) * PAGE_SIZE,
		limit=PAGE_SIZE,
		price_min=price_min,
		price_max=price_max,
		in_stock=form.get("stock") == "in",
	)
	return {
		"store": store_details(),
		"collections": collections,
		"filters": listing_filters(form, collections),
		"search": form.get("search") or "",
		"page": page,
		"has_more": page * PAGE_SIZE < result["total"],
		**result,
	}


PRICE_BUCKETS = [
	("0-500", "Under {0}", (None, 500)),
	("500-1000", "{0} to {1}", (500, 1000)),
	("1000-2000", "{0} to {1}", (1000, 2000)),
	("2000-", "Over {0}", (2000, None)),
]

SORT_OPTIONS = [
	("ranking", "Featured"),
	("newest", "Newest"),
	("name", "Name"),
	("price_asc", "Price, low to high"),
	("price_desc", "Price, high to low"),
]


def parse_price_bucket(bucket: str | None):
	for key, _label, (low, high) in PRICE_BUCKETS:
		if bucket == key:
			return low, high
	return None, None


def listing_filters(form, collections) -> list[dict]:
	def option(label, param, value):
		current = form.get(param)
		active = (current or "") == (value or "")
		return {"label": label, "url": filter_url(form, {param: value}), "active": "true" if active else "false"}

	from frappe.utils import fmt_money

	currency = frappe.get_cached_doc("Shop Settings").currency
	money = lambda amount: fmt_money(amount, currency=currency, precision=0)
	return [
		{
			"label": "Collection",
			"options": [
				option("All", "collection", None),
				*[option(row.title, "collection", row.slug) for row in collections],
			],
		},
		{
			"label": "Price",
			"options": [
				option("Any price", "price", None),
				*[
					option(label.format(money(low or high), money(high or low)), "price", key)
					for key, label, (low, high) in PRICE_BUCKETS
				],
			],
		},
		{
			"label": "Availability",
			"options": [option("All", "stock", None), option("In stock", "stock", "in")],
		},
		{
			"label": "Sort",
			"options": [option(label, "sort", None if key == "ranking" else key) for key, label in SORT_OPTIONS],
		},
	]


def filter_url(form, changes: dict) -> str:
	from urllib.parse import urlencode

	params = {
		key: form.get(key) for key in ("collection", "search", "sort", "price", "stock") if form.get(key)
	}
	for key, value in changes.items():
		if value:
			params[key] = value
		else:
			params.pop(key, None)
	return "/products" + (f"?{urlencode(params)}" if params else "")


@frappe.whitelist(allow_guest=True)
def product_page() -> dict:
	detail = product.get_product(frappe.form_dict.slug)
	detail["image"] = detail["images"][0]["image"] if detail["images"] else None
	detail["buy_item_code"] = detail.get("default_item_code") or detail["item"]
	detail["description_text"] = frappe.utils.strip_html(detail.get("description") or "")
	detail["attribute_options"] = [
		{
			"attribute": option["attribute"],
			"values": [{"attribute": option["attribute"], "value": value} for value in option["values"]],
		}
		for option in detail.get("attributes", [])
	]
	return {
		"store": store_details(),
		"product": detail,
		"related_products": related_products(detail),
	}


def related_products(detail: dict) -> list:
	collections = detail.get("collections") or []
	if collections:
		result = catalog.get_products(collection=collections[0]["slug"], limit=5)["products"]
	else:
		result = catalog.get_products(limit=5)["products"]
	return [product for product in result if product.slug != detail["slug"]][:4]


@frappe.whitelist(allow_guest=True)
def collection_page() -> dict:
	slug = frappe.form_dict.slug
	collection = frappe.db.get_value(
		"Shop Collection",
		{"slug": slug, "published": 1},
		["title", "slug", "description", "image"],
		as_dict=True,
	)
	if not collection:
		frappe.throw(frappe._("Collection not found"), frappe.DoesNotExistError)
	return {
		"store": store_details(),
		"collection": collection,
		**catalog.get_products(collection=slug, limit=PAGE_SIZE),
	}


@frappe.whitelist(allow_guest=True)
def basic() -> dict:
	return {"store": store_details()}


@frappe.whitelist(allow_guest=True)
def cart_page() -> dict:
	return {"store": store_details(), "cart": cart.get_cart()}


@frappe.whitelist(allow_guest=True)
def checkout_page() -> dict:
	return {"store": store_details(), **checkout.get_checkout_summary()}


@frappe.whitelist(allow_guest=True)
def order_confirmation() -> dict:
	form = frappe.form_dict
	return {
		"store": store_details(),
		"order": orders.get_order_summary(form.order_id, form.get("token")),
	}


@frappe.whitelist()
def account_orders() -> dict:
	return {"store": store_details(), "orders": orders.get_orders()}


def store_details() -> dict:
	settings = frappe.get_cached_doc("Shop Settings")
	return {
		"name": settings.store_name,
		"logo": settings.store_logo,
		"currency": settings.currency,
	}
