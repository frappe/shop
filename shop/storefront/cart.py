import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, flt, nowdate

from shop.storefront import pricing

CART_COOKIE = "shop_cart_token"
MAX_CART_ITEMS = 50
ABANDON_AFTER_DAYS = 30
DELETE_AFTER_DAYS = 90


@frappe.whitelist(allow_guest=True)
def get_cart() -> dict:
	return cart_payload(resolve_cart())


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def add_item(item_code: str, qty: float = 1) -> dict:
	shop_product = validate_purchasable(item_code)
	cart = resolve_cart(create=True)
	row = find_row(cart, item_code)
	if row:
		row.qty += max(flt(qty), 1)
	elif len(cart.items) >= MAX_CART_ITEMS:
		frappe.throw(_("Cart is full"))
	else:
		cart.append("items", {"item_code": item_code, "shop_product": shop_product, "qty": max(flt(qty), 1)})
	save_cart(cart)
	return cart_payload(cart)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def set_qty(item_code: str, qty: float) -> dict:
	cart = resolve_cart()
	if not cart:
		return cart_payload(None)
	row = find_row(cart, item_code)
	if row:
		if flt(qty) > 0:
			row.qty = flt(qty)
		else:
			cart.remove(row)
		save_cart(cart)
	return cart_payload(cart)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def clear() -> dict:
	cart = resolve_cart()
	if cart:
		cart.items = []
		save_cart(cart)
	return cart_payload(cart)


def resolve_cart(create: bool = False):
	cart = find_cart()
	if cart or not create:
		return cart
	cart = frappe.new_doc("Shop Cart")
	if not is_guest():
		cart.user = frappe.session.user
	cart.insert(ignore_permissions=True)
	set_cart_cookie(cart)
	return cart


def find_cart():
	token = request_token()
	if token:
		name = frappe.db.get_value("Shop Cart", {"token": token, "status": "Active"})
		if name:
			return frappe.get_doc("Shop Cart", name)
	if not is_guest():
		name = frappe.db.get_value(
			"Shop Cart", {"user": frappe.session.user, "status": "Active"}
		)
		if name:
			return frappe.get_doc("Shop Cart", name)
	return None


def save_cart(cart):
	refresh_rates(cart)
	cart.save(ignore_permissions=True)
	set_cart_cookie(cart)


def refresh_rates(cart):
	prices = pricing.get_prices([row.item_code for row in cart.items])
	for row in cart.items:
		row.rate = prices.get(row.item_code, {}).get("rate", 0)


def cart_payload(cart) -> dict:
	if not cart or not cart.items:
		return {"items": [], "item_count": 0, "total": 0, "formatted_total": pricing.format_amount(0)}
	products = product_details(cart)
	items = []
	total = 0.0
	for row in cart.items:
		amount = flt(row.rate) * flt(row.qty)
		total += amount
		items.append(
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"rate": row.rate,
				"formatted_rate": pricing.format_amount(row.rate),
				"amount": amount,
				"formatted_amount": pricing.format_amount(amount),
				**products.get(row.shop_product, {}),
			}
		)
	return {
		"items": items,
		"item_count": sum(flt(row.qty) for row in cart.items),
		"total": total,
		"formatted_total": pricing.format_amount(total),
	}


def product_details(cart) -> dict:
	names = [row.shop_product for row in cart.items if row.shop_product]
	if not names:
		return {}
	details = {}
	for product in frappe.get_all(
		"Shop Product", filters={"name": ["in", names]}, fields=["name", "product_name", "slug"]
	):
		details[product.name] = {
			"product_name": product.product_name,
			"slug": product.slug,
			"image": first_image(product.name),
		}
	return details


def first_image(shop_product: str) -> str | None:
	return frappe.db.get_value(
		"Shop Product Image", {"parent": shop_product}, "image", order_by="idx"
	)


def validate_purchasable(item_code: str) -> str:
	item = frappe.db.get_value(
		"Item", item_code, ["has_variants", "variant_of", "disabled"], as_dict=True
	)
	if not item or item.disabled or item.has_variants:
		frappe.throw(_("Item {0} is not available").format(item_code))
	published_item = item.variant_of or item_code
	shop_product = frappe.db.get_value(
		"Shop Product", {"item": published_item, "published": 1}
	)
	if not shop_product:
		frappe.throw(_("Item {0} is not available").format(item_code))
	return shop_product


def find_row(cart, item_code: str):
	for row in cart.items:
		if row.item_code == item_code:
			return row
	return None


def set_cart_cookie(cart):
	if hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.set_cookie(
			CART_COOKIE, cart.token, httponly=True, samesite="Lax"
		)


def request_token() -> str | None:
	if not hasattr(frappe.local, "request") or not frappe.local.request:
		return None
	return frappe.local.request.cookies.get(CART_COOKIE)


def is_guest() -> bool:
	return frappe.session.user in ("Guest", None)


def merge_guest_cart(login_manager=None):
	token = request_token()
	if not token or is_guest():
		return
	name = frappe.db.get_value("Shop Cart", {"token": token, "status": "Active"})
	if not name:
		return
	guest_cart = frappe.get_doc("Shop Cart", name)
	user_cart_name = frappe.db.get_value(
		"Shop Cart",
		{"user": frappe.session.user, "status": "Active", "name": ["!=", name]},
	)
	if not user_cart_name:
		guest_cart.user = frappe.session.user
		guest_cart.save(ignore_permissions=True)
		return
	user_cart = frappe.get_doc("Shop Cart", user_cart_name)
	for row in guest_cart.items:
		existing = find_row(user_cart, row.item_code)
		if existing:
			existing.qty += row.qty
		else:
			user_cart.append(
				"items", {"item_code": row.item_code, "shop_product": row.shop_product, "qty": row.qty}
			)
	save_cart(user_cart)
	guest_cart.delete(ignore_permissions=True)


def cleanup_carts():
	frappe.db.set_value(
		"Shop Cart",
		{"status": "Active", "last_active": ["<", add_days(nowdate(), -ABANDON_AFTER_DAYS)]},
		"status",
		"Abandoned",
		update_modified=False,
	)
	for name in frappe.get_all(
		"Shop Cart",
		filters={"status": "Abandoned", "modified": ["<", add_days(nowdate(), -DELETE_AFTER_DAYS)]},
		pluck="name",
	):
		frappe.delete_doc("Shop Cart", name, ignore_permissions=True, delete_permanently=True)
