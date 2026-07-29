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
	result = catalog.get_products(
		collection=form.get("collection"),
		search=form.get("search"),
		sort=form.get("sort") or "ranking",
		start=(page - 1) * PAGE_SIZE,
		limit=PAGE_SIZE,
	)
	return {
		"store": store_details(),
		"collections": catalog.get_collections(),
		"search": form.get("search") or "",
		"page": page,
		"has_more": page * PAGE_SIZE < result["total"],
		**result,
	}


@frappe.whitelist(allow_guest=True)
def product_page() -> dict:
	return {"store": store_details(), "product": product.get_product(frappe.form_dict.slug)}


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
