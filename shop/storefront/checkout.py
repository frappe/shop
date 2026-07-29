import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, flt, nowdate, validate_email_address

from shop.storefront import cart as cart_module
from shop.storefront import pricing, stock


@frappe.whitelist(allow_guest=True)
def get_checkout_summary() -> dict:
	cart = cart_module.resolve_cart()
	settings = frappe.get_cached_doc("Shop Settings")
	methods = []
	if settings.enable_cod:
		methods.append({"method": "cod", "label": _("Cash on Delivery")})
	if settings.payment_gateway_account:
		methods.append({"method": "gateway", "label": _("Pay Online")})
	return {
		"cart": cart_module.cart_payload(cart),
		"payment_methods": methods,
		"currency": settings.currency,
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60)
def place_order(customer: dict, address: dict, payment_method: str = "cod") -> dict:
	cart = cart_module.resolve_cart()
	validate_order(cart, customer, payment_method)
	party = get_or_create_customer(customer)
	shipping_address = create_address(party, customer, address)
	sales_order = create_sales_order(cart, party, shipping_address)
	convert_cart(cart, sales_order)
	response = {
		"sales_order": sales_order.name,
		"confirmation_url": f"/order-confirmation/{sales_order.name}?token={cart.token}",
	}
	if payment_method == "gateway":
		response["payment_url"] = create_payment_request(sales_order, customer)
	return response


def validate_order(cart, customer: dict, payment_method: str):
	if not cart or not cart.items:
		frappe.throw(_("Your cart is empty"))
	settings = frappe.get_cached_doc("Shop Settings")
	if payment_method == "cod" and not settings.enable_cod:
		frappe.throw(_("Cash on Delivery is not available"))
	if payment_method == "gateway" and not settings.payment_gateway_account:
		frappe.throw(_("Online payment is not available"))
	validate_email_address(customer.get("email"), throw=True)
	if not customer.get("full_name"):
		frappe.throw(_("Name is required"))
	validate_stock(cart)


def validate_stock(cart):
	settings = frappe.get_cached_doc("Shop Settings")
	for row in cart.items:
		cart_module.validate_purchasable(row.item_code)
		if settings.allow_out_of_stock:
			continue
		if not frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
			continue
		available = stock.get_stock([row.item_code]).get(row.item_code, 0)
		if available < flt(row.qty):
			frappe.throw(_("Only {0} of {1} left in stock").format(int(available), row.item_code))


def get_or_create_customer(customer: dict) -> str:
	email = customer["email"].strip().lower()
	existing = find_customer_by_email(email)
	if existing:
		return existing
	party = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer["full_name"],
			"customer_type": "Individual",
		}
	).insert(ignore_permissions=True)
	create_contact(party.name, customer, email)
	return party.name


def find_customer_by_email(email: str) -> str | None:
	contact = frappe.db.get_value("Contact Email", {"email_id": email}, "parent")
	if not contact:
		return None
	return frappe.db.get_value(
		"Dynamic Link",
		{"parenttype": "Contact", "parent": contact, "link_doctype": "Customer"},
		"link_name",
	)


def create_contact(party: str, customer: dict, email: str):
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": customer["full_name"],
			"links": [{"link_doctype": "Customer", "link_name": party}],
		}
	)
	contact.add_email(email, is_primary=True)
	if customer.get("phone"):
		contact.add_phone(customer["phone"], is_primary_mobile_no=True)
	contact.insert(ignore_permissions=True)


def create_address(party: str, customer: dict, address: dict):
	doc = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": customer["full_name"],
			"address_type": "Shipping",
			"address_line1": address.get("address_line1"),
			"address_line2": address.get("address_line2"),
			"city": address.get("city"),
			"state": address.get("state"),
			"country": address.get("country") or frappe.db.get_default("country"),
			"pincode": address.get("pincode"),
			"phone": customer.get("phone"),
			"email_id": customer.get("email"),
			"links": [{"link_doctype": "Customer", "link_name": party}],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def create_sales_order(cart, party: str, shipping_address):
	settings = frappe.get_cached_doc("Shop Settings")
	cart_module.refresh_rates(cart)
	sales_order = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"company": settings.company,
			"customer": party,
			"delivery_date": add_days(nowdate(), 3),
			"selling_price_list": settings.price_list,
			"currency": settings.currency,
			"customer_address": shipping_address.name,
			"shipping_address_name": shipping_address.name,
			"items": [
				{
					"item_code": row.item_code,
					"qty": row.qty,
					"rate": row.rate,
					"warehouse": settings.default_warehouse,
				}
				for row in cart.items
			],
		}
	)
	apply_taxes(sales_order, settings)
	sales_order.flags.ignore_permissions = True
	sales_order.run_method("set_missing_values")
	sales_order.insert(ignore_permissions=True)
	sales_order.submit()
	return sales_order


def apply_taxes(sales_order, settings):
	if not settings.tax_template:
		return
	from erpnext.accounts.services.taxes import get_taxes_and_charges

	sales_order.taxes_and_charges = settings.tax_template
	for tax in get_taxes_and_charges("Sales Taxes and Charges Template", settings.tax_template) or []:
		sales_order.append("taxes", tax)


def convert_cart(cart, sales_order):
	cart.status = "Converted"
	cart.sales_order = sales_order.name
	cart.save(ignore_permissions=True)


def create_payment_request(sales_order, customer: dict) -> str | None:
	from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

	settings = frappe.get_cached_doc("Shop Settings")
	payment_request = make_payment_request(
		dt="Sales Order",
		dn=sales_order.name,
		recipient_id=customer.get("email"),
		payment_gateway_account=settings.payment_gateway_account,
		submit_doc=1,
		mute_email=1,
		return_doc=1,
	)
	return payment_request.get_payment_url()
