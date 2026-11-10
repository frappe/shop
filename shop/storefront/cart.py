import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, add_to_date, cint, flt, now_datetime, nowdate, validate_email_address

from shop.storefront import pricing, stock

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
	if flt(qty) <= 0:
		frappe.throw(_("Enter how many you want."))
	shop_product = validate_purchasable(item_code)
	cart = resolve_cart(create=True)
	row = find_row(cart, item_code)
	wanted = (flt(row.qty) if row else 0) + flt(qty)
	check_available(item_code, wanted)
	if row:
		row.qty = wanted
	elif len(cart.items) >= MAX_CART_ITEMS:
		frappe.throw(_("Cart is full"))
	else:
		cart.append("items", {"item_code": item_code, "shop_product": shop_product, "qty": wanted})
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
			check_available(item_code, flt(qty))
			row.qty = flt(qty)
		else:
			cart.remove(row)
		save_cart(cart)
	return cart_payload(cart)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60)
def apply_coupon(code: str) -> dict:
	from shop.storefront import coupons

	cart = resolve_cart()
	if not cart or not cart.items:
		frappe.throw(_("Your cart is empty"))
	refresh_rates(cart)
	coupon = coupons.resolve(code)
	coupons.check_minimum(coupon, sum(flt(row.rate) * flt(row.qty) for row in cart.items))
	cart.coupon_code = coupon.name
	if not preview_coupon(cart)[0]:
		frappe.throw(_("That coupon doesn't apply to your order"))
	cart.save(ignore_permissions=True)
	return cart_payload(cart)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def remove_coupon() -> dict:
	cart = resolve_cart()
	if cart and cart.coupon_code:
		cart.coupon_code = None
		cart.save(ignore_permissions=True)
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
		name = token_cart(token, "Active")
		if name:
			return frappe.get_doc("Shop Cart", name)
	if not is_guest():
		name = frappe.db.get_value("Shop Cart", {"user": frappe.session.user, "status": "Active"})
		if name:
			return frappe.get_doc("Shop Cart", name)
	return None


def save_cart(cart):
	refresh_rates(cart)
	cart.save(ignore_permissions=True)
	set_cart_cookie(cart)


def refresh_rates(cart):
	qtys = {}
	for row in cart.items:
		qtys[row.item_code] = qtys.get(row.item_code, 0) + flt(row.qty)
	# the shopper's own prices, with quantity breaks
	prices = pricing.get_prices([row.item_code for row in cart.items], qtys=qtys)
	for row in cart.items:
		row.rate = prices.get(row.item_code, {}).get("rate", 0)


def cart_payload(cart, exact: bool = False) -> dict:
	"""The cart for display. Amounts are shown in the shopper's chosen currency (approximate), with
	each item's tax when the store shows prices with tax, or exactly in the store currency, as
	checkout does."""

	def money(amount, tax_rate=None):
		return pricing.store_amount(amount) if exact else pricing.display_amount(amount, tax_rate)

	if not cart or not cart.items:
		return {
			"items": [],
			"item_count": 0,
			"is_empty": True,
			"subtotal": 0,
			"formatted_subtotal": money(0),
			"coupon": None,
			"discount": 0,
			"total": 0,
			"formatted_total": money(0),
		}
	products = product_details(cart)
	items = []
	subtotal = tax = 0.0
	for row in cart.items:
		amount = flt(row.rate) * flt(row.qty)
		tax_rate = pricing.item_tax_rate(row.item_code)
		subtotal += amount
		tax += amount * tax_rate
		items.append(
			{
				"item_code": row.item_code,
				"qty": display_qty(row.qty),
				"rate": row.rate,
				"formatted_rate": money(row.rate, tax_rate),
				"amount": amount,
				"formatted_amount": money(amount, tax_rate),
				**products.get(row.shop_product, {}),
				**variant_name(row.item_code, products.get(row.shop_product, {}).get("product_name")),
			}
		)
	# the items' rates together; a discount comes off each item, its tax with it
	cart_rate = tax / subtotal if subtotal else None
	coupon, discount = applied_discount(cart, subtotal, cart_rate)
	shipping = shipping_charge(subtotal - discount)
	total = subtotal - discount + shipping
	total_tax = (subtotal - discount) * flt(cart_rate) + shipping * pricing.domestic_tax_rate()
	total_rate = total_tax / total if total else None
	return {
		"items": items,
		"item_count": display_qty(sum(flt(row.qty) for row in cart.items)),
		"is_empty": False,
		"subtotal": subtotal,
		"formatted_subtotal": money(subtotal, cart_rate),
		"coupon": coupon,
		"discount": discount,
		"formatted_discount": money(discount, cart_rate),
		"shipping": shipping,
		"formatted_shipping": money(shipping) if shipping else _("Free"),
		"total": total,
		"formatted_total": money(total, total_rate),
	}


def forget_coupon(cart) -> None:
	"""Drop a coupon that no longer applies. Page renders are read-only requests,
	so the write has to be committed explicitly or the cart keeps a dead code."""
	cart.db_set("coupon_code", None, update_modified=False)
	cart.coupon_code = None
	if frappe.request and frappe.request.method == "GET":
		frappe.db.commit()


def shipping_charge(order_value: float) -> float:
	"""The store's flat rate as checkout charges it, once per order."""
	from shop.storefront.shipping import flat_rate_option

	option = flat_rate_option(order_value)
	return flt(option["amount"]) if option else 0.0


def applied_discount(cart, subtotal: float, tax_rate: float | None = None):
	if not cart.coupon_code:
		return None, 0.0
	from shop.storefront import coupons

	try:
		coupons.resolve(frappe.db.get_value("Coupon Code", cart.coupon_code, "coupon_code") or "")
		coupon, discount = preview_coupon(cart)
	except Exception:
		frappe.clear_messages()
		forget_coupon(cart)
		return None, 0.0
	if not coupon:
		return None, 0.0
	return dict(coupon, formatted_discount=pricing.display_amount(discount, tax_rate)), discount


def preview_coupon(cart):
	"""The cart's coupon and what it takes off, as ERPNext prices the order for the shopper."""
	from shop.storefront import totals
	from shop.storefront.checkout import elevated

	customer, currency = pricing.session_customer(), totals.company_currency()
	# priced with the store's tax, as checkout prices it, so a discount on the Grand Total is right
	template = totals.tax_template_for(None)
	with elevated():
		order = totals.new_order(cart, customer, currency, template)
		totals.calculate(order)
		coupon = totals.apply_coupon(order)
		if not coupon:
			return None, 0.0
		code, cart.coupon_code = cart.coupon_code, None
		try:
			without = totals.new_order(cart, customer, currency, template)
		finally:
			cart.coupon_code = code
		totals.calculate(without)
	# what comes off the cart's subtotal, which includes tax when the store's prices do
	field = "grand_total" if frappe.get_cached_doc("Shop Settings").prices_include_tax else "net_total"
	return coupon, flt(flt(without.get(field)) - flt(order.get(field)), order.precision(field))


def display_qty(qty: float) -> float | int:
	return int(qty) if qty == int(qty) else qty


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


def variant_name(item_code: str, product_name: str | None) -> dict:
	"""A variant's line names its options after the product's name and an en dash, such as
	"Product \u2013 Medium / Blue"."""
	values = frappe.get_all(
		"Item Variant Attribute", filters={"parent": item_code}, pluck="attribute_value", order_by="idx asc"
	)
	if not values or not product_name:
		return {}
	return {"product_name": f"{product_name} \u2013 {' / '.join(values)}"}


def first_image(shop_product: str) -> str | None:
	return frappe.db.get_value("Shop Product Image", {"parent": shop_product}, "image", order_by="idx asc")


def validate_purchasable(item_code: str) -> str:
	item = frappe.db.get_value(
		"Item", item_code, ["item_name", "has_variants", "variant_of", "disabled"], as_dict=True
	)
	if not item or item.disabled or item.has_variants:
		frappe.throw(_("{0} is no longer available").format(item.item_name if item else item_code))
	published_item = item.variant_of or item_code
	shop_product = frappe.db.get_value("Shop Product", {"item": published_item, "published": 1})
	if not shop_product:
		frappe.throw(_("{0} is no longer available").format(item.item_name))
	return shop_product


def check_available(item_code: str, qty: float) -> None:
	"""The shopper can buy this many: the item has a price for them and enough stock."""
	# the store sells in the stock unit, as orders are placed
	name, uom = frappe.get_cached_value("Item", item_code, ["item_name", "stock_uom"]) or (item_code, None)
	if flt(qty) != cint(qty) and frappe.get_cached_value("UOM", uom, "must_be_whole_number"):
		frappe.throw(_("{0} is sold in whole numbers").format(name))
	if item_code not in pricing.get_prices([item_code], {item_code: qty}):
		frappe.throw(_("{0} isn't available online").format(name))
	available = stock.available_qty(item_code)
	if available is None or available >= qty:
		return
	if available <= 0:
		frappe.throw(_("{0} is out of stock").format(name))
	frappe.throw(_("Only {0} of {1} left in stock").format(cint(available), name))


def find_row(cart, item_code: str):
	for row in cart.items:
		if row.item_code == item_code:
			return row
	return None


def set_cart_cookie(cart):
	if hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.set_cookie(CART_COOKIE, cart.token, httponly=True, samesite="Lax")


def request_token() -> str | None:
	# a cart brought back in this request (restore_cart) before its cookie reaches the browser
	restored = getattr(frappe.local, "shop_cart_token", None)
	if restored:
		return restored
	if not hasattr(frappe.local, "request") or not frappe.local.request:
		return None
	return frappe.local.request.cookies.get(CART_COOKIE)


def is_guest() -> bool:
	return frappe.session.user in ("Guest", None)


def merge_guest_cart(login_manager=None):
	token = request_token()
	if not token or is_guest():
		return
	name = token_cart(token, "Active")
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


def token_cart(token: str, status: str) -> str | None:
	"""The browser's cart, unless it is someone else's: the cookie outlives a sign-out on a shared
	computer."""
	cart = frappe.db.get_value(
		"Shop Cart", {"token": token, "status": status}, ["name", "user"], as_dict=True
	)
	from shop.storefront.pricing import shopper

	if not cart or (cart.user and cart.user != shopper()):
		return None
	return cart.name


def forget_cart(login_manager=None):
	"""Signing out leaves the cart with the account, not with the browser."""
	if request_token() and frappe.local.get("cookie_manager"):
		frappe.local.cookie_manager.delete_cookie(CART_COOKIE)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=10 * 60)
def remember_email(email: str) -> None:
	"""The email typed at checkout, so a cart left there can be reminded of (Shop Settings)."""
	email = (email or "").strip().lower()
	cart = find_cart()
	if cart and cart.items and validate_email_address(email):
		frappe.db.set_value("Shop Cart", cart.name, "email", email, update_modified=False)


def remind_left_carts():
	"""Email once about a cart left with items in it, the store's set number of hours after it was
	last changed (Shop Settings); carts older than a week are left alone."""
	from frappe.utils import get_url

	from shop.routes import store_url
	from shop.storefront import emails

	hours = cint(frappe.get_cached_doc("Shop Settings").get("cart_reminder_hours"))
	if not hours:
		return
	now = now_datetime()
	for row in frappe.get_all(
		"Shop Cart",
		filters={
			"status": "Active",
			"reminded": 0,
			"last_active": ["between", [add_to_date(now, days=-7), add_to_date(now, hours=-hours)]],
		},
		fields=["name", "email", "user", "token"],
	):
		email = row.email or (row.user if row.user and "@" in row.user else None)
		cart = frappe.get_doc("Shop Cart", row.name)
		if email and cart.items:
			emails.send(
				"cart_reminder",
				email,
				cart,
				lines_html=cart_lines_html(cart),
				cart_url=get_url(store_url(f"cart?restore={row.token}")),
			)
		frappe.db.set_value("Shop Cart", row.name, "reminded", 1, update_modified=False)


def cart_lines_html(cart) -> str:
	esc = frappe.utils.escape_html
	return "".join(
		f'<div class="order-item"><span>{esc(frappe.get_cached_value("Item", row.item_code, "item_name") or row.item_code)}</span>'
		f'<span class="order-qty">{display_qty(row.qty)}</span></div>'
		for row in cart.items
	)


def restore_cart(token: str) -> None:
	"""A reminder's link brings its cart back to the browser that follows it."""
	name = token and token_cart(token, "Active")
	if name:
		set_cart_cookie(frappe.get_doc("Shop Cart", name))
		frappe.local.shop_cart_token = token


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
