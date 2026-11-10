import json
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, flt, nowdate, validate_email_address

from shop.routes import store_url
from shop.storefront import cart as cart_module
from shop.storefront import pricing, shipping, stock, totals


@frappe.whitelist(allow_guest=True)
def get_checkout_summary() -> dict:
	cart = cart_module.resolve_cart()
	settings = frappe.get_cached_doc("Shop Settings")
	return {
		"cart": cart_module.cart_payload(cart, exact=True),
		"payment_methods": totals.payment_methods(),
		"currency": settings.currency,
		"prefill": checkout_prefill(),
		"addresses": saved_addresses(),
		"has_addresses": "true" if saved_addresses_exist() else None,
		"countries": countries(),
		"default_country": totals.company_country(),
		"terms": terms_details(),
		"bank_currency_note": bank_currency_note(),
		"quotes_enabled": "true" if settings.get("allow_quote_requests") else None,
		"waiting_order": None if cart and cart.items else waiting_order(),
		"buying_for_html": pricing.buying_for_html() or None,
	}


def waiting_order() -> dict | None:
	"""The order this browser placed last when it is still waiting for its online payment, so a
	shopper who came back from the payment page can find it."""
	from shop.storefront import orders

	token = cart_module.request_token()
	cart = token and cart_module.token_cart(token, "Converted")
	name = cart and frappe.db.get_value("Shop Cart", cart, "sales_order")
	if not name:
		return None
	order = frappe.get_doc("Sales Order", name)
	url = order.docstatus == 1 and not orders.is_cancelled(order) and orders.pay_url(order)
	if not url:
		return None
	return {
		"note": _("Your order {0} is waiting for payment.").format(name),
		"pay_url": url,
		"order_url": orders.order_url(name),
	}


def bank_currency_note() -> str | None:
	"""Explains the bank transfer currency choice, with the conversion fee the store charges."""
	accounts = totals.bank_accounts()
	if len(accounts) < 2:
		return None
	fees = sorted({flt(row.conversion_fee_percent) for row in accounts if flt(row.conversion_fee_percent)})
	note = _("We give you local bank details for the currency you choose.")
	if fees:
		fee = f"{fees[-1]:g}%" if len(fees) == 1 else _("up to {0}%").format(f"{fees[-1]:g}")
		settings = frappe.get_cached_doc("Shop Settings")
		if settings.prices_include_tax and pricing.item_tax_rate(settings.get("conversion_fee_item")):
			# the fee is grossed up by the tax on it at home
			fee = _("{0} plus tax where it applies").format(fee)
		note += " " + _("Paying in another currency than {0} adds {1} to cover converting the money.").format(
			totals.company_currency(), fee
		)
	return note


def countries() -> list[dict]:
	"""ERPNext's countries, the store's own first: a select starts on its first option."""
	default = totals.company_country()
	names = frappe.get_all("Country", pluck="name", order_by="name")
	return [{"name": name} for name in sorted(names, key=lambda name: name != default)]


def terms_details() -> dict | None:
	from shop.storefront import terms

	return terms.details()


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def quote(
	address: dict | None = None,
	shipping_option: str | None = None,
	payment_method: str | None = None,
	currency: str | None = None,
) -> dict:
	"""Totals for the checkout as the shopper fills it in: shipping options, fees, tax and total."""
	cart = cart_module.resolve_cart()
	if not cart or not cart.items:
		frappe.throw(_("Your cart is empty"))
	with elevated():
		result = totals.compute(cart, address, shipping_option, payment_method, currency)
		if result.shippings:
			shipping.remember_choice(
				cart,
				{row.parcel: row.id for row in result.shippings}
				if len(result.shippings) > 1
				else result.shippings[0].id,
			)
		return totals.payload(result)


PREFILL_FIELDS = (
	"email",
	"full_name",
	"phone",
	"address_line1",
	"address_line2",
	"city",
	"state",
	"country",
	"pincode",
)


def checkout_prefill() -> dict:
	"""Signed-in customers get their details back instead of an empty form."""
	prefill = dict.fromkeys(PREFILL_FIELDS, "")
	user = frappe.session.user
	if user in ("Guest", None, "Administrator"):
		return prefill
	prefill["email"] = user
	prefill["full_name"] = frappe.db.get_value("User", user, "full_name") or ""
	customer = pricing.session_customer()
	if not customer:
		return prefill
	customers = [customer]
	prefill["phone"] = contact_phone(user) or ""
	address = last_shipping_address(customers)
	for field, value in (address or {}).items():
		prefill[field] = value or ""
	return prefill


def contact_phone(user: str) -> str | None:
	contact = frappe.db.get_value("Contact Email", {"email_id": user}, "parent")
	if not contact:
		return None
	return frappe.db.get_value("Contact", contact, "mobile_no") or frappe.db.get_value(
		"Contact", contact, "phone"
	)


ADDRESS_FIELDS = ("address_line1", "address_line2", "city", "state", "country", "pincode")


def saved_addresses_exist() -> bool:
	return len(saved_addresses()) > 1


def saved_addresses() -> list[dict]:
	"""Every address the customer the shopper buys for has shipped to, newest first, plus a blank
	entry."""
	if frappe.session.user in ("Guest", None, "Administrator"):
		return []
	customer = pricing.session_customer()
	if not customer:
		return []
	customers = [customer]
	links = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": ["in", customers]},
		pluck="parent",
	)
	if not links:
		return []
	rows = frappe.get_all(
		"Address",
		filters={"name": ["in", links]},
		fields=["name", *ADDRESS_FIELDS],
		order_by="modified desc",
		limit=6,
	)
	for row in rows:
		row.line = frappe.utils.escape_html(
			", ".join(str(row[field]) for field in ("address_line1", "city", "pincode") if row.get(field))
		)
	rows.append(frappe._dict({"name": "", "line": _("Enter a new address")}))
	return rows


def last_shipping_address(customers: list[str]) -> dict | None:
	links = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": ["in", customers]},
		pluck="parent",
	)
	if not links:
		return None
	rows = frappe.get_all(
		"Address",
		filters={"name": ["in", links]},
		fields=["address_line1", "address_line2", "city", "state", "country", "pincode"],
		order_by="modified desc",
		limit=1,
	)
	return rows[0] if rows else None


@frappe.whitelist(allow_guest=True, methods=["POST"])
# generous enough for shoppers sharing an office or campus network
@rate_limit(limit=30, seconds=60)
def place_order(
	customer: dict,
	address: dict,
	payment_method: str = "cod",
	shipping_option: str | None = None,
	currency: str | None = None,
	accept_terms: int = 0,
	business_buyer: int = 0,
	expected_total: float | None = None,
	po_no: str | None = None,
	order_note: str | None = None,
) -> dict:
	customer, address = plain_text(customer), plain_text(address)
	payment_method = totals.resolve_method(payment_method)
	cart = cart_module.resolve_cart()
	validate_order(cart, customer, payment_method, accept_terms)
	with elevated():
		lock_cart(cart)
		order_quote = totals.compute(cart, address, shipping_option, payment_method, currency)
		validate_quote(order_quote, expected_total)
		party = get_or_create_customer(customer)
		limit_unpaid_orders(party, payment_method)
		shipping_address = create_address(party, customer, order_quote.address or address)
		sales_order = create_sales_order(
			cart,
			party,
			shipping_address,
			order_quote,
			terms_accepted=frappe.utils.cint(accept_terms),
			business_buyer=frappe.utils.cint(business_buyer),
			email=customer["email"].strip().lower(),
			po_no=po_no,
			order_note=order_note,
		)
		convert_cart(cart, sales_order)
		count_unpaid_order(payment_method)
		confirmation_url = store_url(f"order-confirmation/{sales_order.name}?token={cart.token}")
		response = {
			"sales_order": sales_order.name,
			"confirmation_url": confirmation_url,
		}
		if totals.is_gateway(payment_method) and totals.order_total(sales_order) > 0:
			# the confirmation goes out once the payment succeeds (ShopPaymentRequest)
			response["payment_url"] = create_payment_request(sales_order, customer)
		else:
			send_confirmation_for(sales_order, confirmation_url)
	return response


# an order waiting for a bank transfer holds its stock, so no one can hold much of it unpaid
UNPAID_ORDERS_PER_CUSTOMER = 2
UNPAID_ORDERS_PER_VISITOR_A_DAY = 5


def limit_unpaid_orders(party: str, payment_method: str) -> None:
	if payment_method not in totals.BANK_METHODS or is_staff(pricing.shopper()):
		return
	waiting = frappe.db.count(
		"Sales Order",
		{
			"customer": party,
			"docstatus": 1,
			"shop_payment_method": ["in", totals.BANK_METHODS],
			"advance_paid": 0,
			"per_billed": 0,
			"status": ["not in", ["Closed", "Completed"]],
		},
	)
	if waiting >= UNPAID_ORDERS_PER_CUSTOMER or unpaid_orders_today() >= UNPAID_ORDERS_PER_VISITOR_A_DAY:
		frappe.throw(
			_("You have orders waiting for a bank transfer. Please pay them, or choose another way to pay."),
			title=_("Orders waiting for payment"),
		)


def unpaid_orders_key() -> str | None:
	ip = getattr(frappe.local, "request_ip", None)
	return ip and frappe.cache.make_key(f"shop:unpaid_orders:{ip}:{nowdate()}")


def unpaid_orders_today() -> int:
	key = unpaid_orders_key()
	return int(frappe.cache.get(key) or 0) if key else 0


def count_unpaid_order(payment_method: str) -> None:
	key = unpaid_orders_key()
	if key and payment_method in totals.BANK_METHODS:
		frappe.cache.incrby(key, 1)
		frappe.cache.expire(key, 2 * 24 * 60 * 60)


def lock_cart(cart) -> None:
	"""Hold the cart for this order, so a second submit can't order it twice."""
	status = frappe.db.get_value("Shop Cart", cart.name, "status", for_update=True)
	if status != "Active":
		frappe.throw(_("This cart has already been ordered. Check your email for the order."))


def send_confirmation_for(sales_order, confirmation_url: str) -> None:
	"""Orders not waiting on an online payment: invoice on-account orders, treat an order with
	nothing to pay as paid, then email the confirmation."""
	from shop.storefront import payment

	method = sales_order.get("shop_payment_method")
	if method == totals.ACCOUNT:
		invoice_on_account(sales_order)
	elif method in (totals.GATEWAY, *totals.BANK_METHODS) and totals.order_total(sales_order) <= 0:
		payment.order_paid(sales_order)
	queue_confirmation_email(sales_order, sales_order.contact_email, confirmation_url)


def invoice_on_account(sales_order) -> str:
	"""Invoice an order paid on account and send it to fulfilment straight away."""
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

	from shop.fulfillment.service import auto_send

	invoice = make_sales_invoice(sales_order.name)
	invoice.flags.ignore_permissions = True
	invoice.insert(ignore_permissions=True)
	invoice.submit()
	sales_order.add_comment("Info", _("Invoiced on account: {0}.").format(invoice.name))
	auto_send(sales_order.name)
	return invoice.name


def send_confirmation(order_name: str) -> None:
	"""Email the order confirmation for an order placed through the store."""
	from shop.storefront.orders import access_token, order_url

	email = frappe.db.get_value("Sales Order", order_name, "contact_email")
	if not email or not access_token(order_name):
		return
	queue_confirmation_email(frappe.get_doc("Sales Order", order_name), email, order_url(order_name))


def validate_quote(order_quote, expected_total: float | None) -> None:
	if not order_quote.shipping:
		if order_quote.shipping_messages:
			frappe.throw("<br>".join(order_quote.shipping_messages))
		frappe.throw(_("We can't ship to this address. Check the address, or contact us."))
	for item in order_quote.order.items:
		# an item with no price, not one a discount makes free
		unpriced = not flt(item.rate) and not flt(item.price_list_rate)
		if unpriced and not item.get("is_free_item") and not totals.is_charge_item(item.item_code):
			frappe.throw(
				_("{0} can't be ordered right now. Remove it to continue.").format(
					item.item_name or item.item_code
				)
			)
	if expected_total is not None and abs(flt(expected_total) - order_quote.total) > 0.009:
		frappe.throw(
			_("The total is {0}. Check your order and place it again.").format(
				totals.money(order_quote.total, order_quote.currency)
			),
			title=_("Total changed"),
		)


def queue_confirmation_email(sales_order, email: str, confirmation_url: str):
	try:
		from shop.storefront import emails, payment

		bank = payment.method(sales_order) in totals.BANK_METHODS and not payment.is_paid(sales_order)
		emails.send(
			"order_payment_instructions" if bank else "order_confirmed",
			email,
			sales_order,
			attachments=payment.invoice_attachments(payment.order_invoice(sales_order.name)),
			**order_email_parts(sales_order, confirmation_url),
		)
	except Exception:
		frappe.log_error(title="Order confirmation email failed")


def order_email_parts(sales_order, confirmation_url: str) -> dict:
	"""The pieces the order emails' templates show: lines and totals, how to pay, links, terms."""
	from shop.storefront import payment

	esc = frappe.utils.escape_html

	def fmt(amount):
		return frappe.utils.fmt_money(amount, currency=sales_order.currency)

	def row(label, amount, bold=False):
		style = "padding:6px 0" + (";font-weight:bold;border-top:1px solid #ddd" if bold else "")
		return (
			f"<tr><td style='{style}'>{esc(label)}</td>"
			f"<td style='{style};text-align:right'>{esc(amount)}</td></tr>"
		)

	lines, notes, factor = totals.shown_lines(sales_order)
	rows = "".join(
		row(
			f"{line.item_name} \u00d7 {cart_module.display_qty(line.qty)}",
			fmt(flt(line.amount) * factor(line)),
		)
		for line in sales_order.items
		if not totals.is_charge_item(line.item_code)
	)
	rows += "".join(row(line["label"], fmt(line["amount"])) for line in lines[1:])
	rows += row(_("Total"), f"{fmt(totals.order_total(sales_order))} {sales_order.currency}", bold=True)
	tax_note = "".join(f"<p style='color:#666;font-size:13px'>{esc(note)}</p>" for note in notes)
	pay = ""
	if sales_order.get("shop_payment_method") == totals.ACCOUNT:
		invoice = payment.order_invoice(sales_order.name)
		if invoice:
			due = frappe.db.get_value("Sales Invoice", invoice, "due_date")
			pay = f"<p>{esc(_('Invoice {0} is attached, due {1}.').format(invoice, frappe.utils.formatdate(due)))}</p>"
			link = payment.invoice_pay_url(invoice)
			if link:
				pay += f"<p><a href='{esc(link)}'>{esc(_('Pay invoice {0} online').format(invoice))}</a></p>"
	elif payment.is_paid(sales_order) and payment.order_invoice(sales_order.name):
		pay = f"<p>{esc(_('Paid. Your invoice {0} is attached.').format(payment.order_invoice(sales_order.name)))}</p>"
	if sales_order.get("shop_payment_method") == totals.GATEWAY and not payment.is_paid(sales_order):
		pay = (
			f"<p>{esc(_('If you did not finish paying, you can pay from your order page:'))} "
			f"<a href='{frappe.utils.get_url(confirmation_url)}'>{esc(_('View your order'))}</a></p>"
		)
	terms = ""
	from shop.storefront import terms as store_terms

	terms_url = store_terms.url()
	if sales_order.get("shop_terms_version") and terms_url:
		terms = (
			f"<p style='color:#666;font-size:13px'>{esc(_('You accepted our terms and conditions ({0}):').format(sales_order.shop_terms_version))} "
			f"<a href='{frappe.utils.get_url(terms_url)}'>{esc(frappe.utils.get_url(terms_url))}</a></p>"
		)
	return {
		"lines_html": f"<table style='width:100%;max-width:520px;border-collapse:collapse'>{rows}</table>{tax_note}",
		"payment_html": payment.bank_instructions_html(sales_order) + pay,
		"order_url": frappe.utils.get_url(confirmation_url),
		"terms_html": terms,
	}


@contextmanager
def elevated():
	"""Run as Administrator for the storefront's own reads and writes: ERPNext's Sales Order,
	Quotation and pricing code needs permissions no shopper role has. Callers check what the
	shopper may do before entering it."""
	# set_user changes session.sid and data in place, so the whole identity is restored, or the
	# response would reissue a broken sid cookie and sign the shopper out
	session = frappe.local.session
	original = (session.user, session.sid, session.data)
	form_dict = frappe.local.form_dict
	# who is shopping, so their prices and accounts still apply while elevated
	outer = getattr(frappe.local, "shop_shopper", None)
	frappe.local.shop_shopper = outer or session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.local.shop_shopper = outer
		session.user, session.sid, session.data = original
		frappe.local.form_dict = form_dict
		frappe.local.cache = {}
		frappe.local.role_permissions = {}
		# what set_user cached for Administrator
		frappe.local.user_perms = None
		frappe.local.new_doc_templates = {}
		frappe.local.jenv_restricted = None
		frappe.local.jenv_unrestricted = None


def validate_order(cart, customer: dict, payment_method: str, accept_terms: int = 0):
	if not cart or not cart.items:
		frappe.throw(_("Your cart is empty"))
	settings = frappe.get_cached_doc("Shop Settings")
	if payment_method not in [method["method"] for method in totals.payment_methods(swift=True)]:
		frappe.throw(_("This payment method is not available"))
	if settings.get("require_terms") and not frappe.utils.cint(accept_terms):
		frappe.throw(_("Please accept the terms and conditions"))
	validate_email_address(customer.get("email"), throw=True)
	if not customer.get("full_name"):
		frappe.throw(_("Name is required"))
	validate_stock(cart)


def lock_stock(item_codes: list[str]) -> None:
	"""Two checkouts at once can't both take the last one: the second waits for the first."""
	parts = [part for code in item_codes for part, _qty in stock.bundle_parts(code)]
	if item_codes:
		frappe.db.sql(
			"select name from `tabBin` where item_code in %(codes)s and warehouse in %(warehouses)s for update",
			{"codes": [*item_codes, *parts], "warehouses": stock.warehouses() or [""]},
		)


def validate_stock(cart):
	lock_stock([row.item_code for row in cart.items])
	for row in cart.items:
		cart_module.validate_purchasable(row.item_code)
	validate_quantities([(row.item_code, flt(row.qty)) for row in cart.items])


def validate_quantities(lines: list[tuple[str, float]]) -> None:
	"""The store has enough of every stock item the lines take together, a Product Bundle counted by
	its parts."""
	if frappe.get_cached_doc("Shop Settings").allow_out_of_stock:
		return
	need = stock.demand(lines)
	available = stock.get_stock(list(need), sellable=True)
	for part, qty in need.items():
		if available.get(part, 0) < qty:
			name = frappe.get_cached_value("Item", part, "item_name") or part
			frappe.throw(_("Only {0} of {1} left in stock").format(int(max(available.get(part, 0), 0)), name))


def get_or_create_customer(customer: dict) -> str:
	signed_in = pricing.session_customer()
	if signed_in:
		return signed_in  # a signed-in shopper always orders on their own account
	email = customer["email"].strip().lower()
	existing = find_customer_by_email(email)
	if existing:
		# no one else can place orders on someone's account, or see its prices and addresses: not a
		# guest, nor someone signed in without a customer of their own. Staff may, for a customer
		# who phoned the order through
		shopper = pricing.shopper()
		if (
			email != shopper
			and not is_staff(shopper)
			and frappe.db.exists("User", {"name": email, "enabled": 1})
		):
			frappe.throw(
				_("There is an account for {0}. Please sign in to order with it.").format(email),
				title=_("Sign in"),
			)
		# anyone can type an email: a guest's earlier orders are kept together, but an order is
		# never put on a customer the store didn't make for a guest (made in Desk, or with terms)
		if earlier_guest(existing):
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


def is_staff(user: str) -> bool:
	return bool(
		{"Shop Manager", "System Manager", "Sales User", "Sales Manager"} & set(frappe.get_roles(user))
	)


def earlier_guest(customer: str) -> bool:
	"""A customer the store made for a guest's order: in the store's customer group, without a
	login, payment terms, price list or credit limit of its own."""
	doc = frappe.get_cached_doc("Customer", customer)
	return (
		(doc.customer_group or "") == (frappe.db.get_single_value("Selling Settings", "customer_group") or "")
		and not doc.get("portal_users")
		and not doc.payment_terms
		and not doc.default_price_list
		and not doc.get("credit_limits")
	)


def find_customer_by_email(email: str) -> str | None:
	"""The customer an email belongs to: a Customer it is a Portal User of, else one linked to any
	Contact with that email."""
	portal = frappe.db.get_value("Portal User", {"parenttype": "Customer", "user": email}, "parent")
	if portal:
		return portal
	contacts = frappe.get_all("Contact Email", filters={"email_id": email}, pluck="parent")
	if not contacts:
		return None
	return frappe.db.get_value(
		"Dynamic Link",
		{"parenttype": "Contact", "parent": ["in", contacts], "link_doctype": "Customer"},
		"link_name",
	)


def create_contact(party: str, customer: dict, email: str):
	first_name, _space, last_name = customer["full_name"].strip().partition(" ")
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name,
			"last_name": last_name.strip() or None,
			"links": [{"link_doctype": "Customer", "link_name": party}],
		}
	)
	contact.add_email(email, is_primary=True)
	if customer.get("phone"):
		contact.add_phone(customer["phone"], is_primary_mobile_no=True)
	contact.insert(ignore_permissions=True)
	set_primary_contact(party, contact)


def set_primary_contact(party: str, contact) -> None:
	"""Make the first contact the customer's Customer Primary Contact, as the desk would.

	ERPNext reads the customer's email from it, for statements and other emails."""
	if frappe.db.get_value("Customer", party, "customer_primary_contact"):
		return
	frappe.db.set_value(
		"Customer",
		party,
		{
			"customer_primary_contact": contact.name,
			"email_id": contact.email_id,
			"mobile_no": contact.mobile_no,
		},
	)


def plain_text(values: dict | None) -> dict:
	"""What a customer typed, without markup, as staff see it in the admin, Desk and emails."""
	return {
		key: frappe.utils.strip_html(value).replace("<", "").replace(">", "").strip()
		if isinstance(value, str)
		else value
		for key, value in (values or {}).items()
	}


def create_address(party: str, customer: dict, address: dict):
	existing = find_address(party, address)
	if existing:
		# bump modified so saved addresses stay ordered by last use
		frappe.db.set_value("Address", existing, "modified", frappe.utils.now())
		return frappe.get_doc("Address", existing)
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


def find_address(party: str, address: dict) -> str | None:
	links = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": party},
		pluck="parent",
	)
	if not links:
		return None
	return frappe.db.get_value(
		"Address",
		{
			"name": ["in", links],
			"address_line1": address.get("address_line1"),
			"city": address.get("city"),
			"pincode": address.get("pincode"),
		},
	)


def create_sales_order(
	cart,
	party: str,
	shipping_address,
	order_quote=None,
	terms_accepted: int = 0,
	business_buyer: int = 0,
	email: str | None = None,
	po_no: str | None = None,
	order_note: str | None = None,
):
	"""Place the order the shopper was quoted, for their customer."""
	if order_quote is None:
		order_quote = totals.compute(cart)
	sales_order = order_quote.order
	sales_order.customer = party
	sales_order.customer_group = frappe.get_cached_value("Customer", party, "customer_group")
	# a signed-in customer is billed to their own address when they have one; a guest to the
	# address they gave, never one already on the customer
	signed_in = bool(pricing.session_customer())
	sales_order.customer_address = (billing_address(party) if signed_in else None) or shipping_address.name
	sales_order.shipping_address_name = shipping_address.name
	if email:
		# the customer's own contact with that email
		sales_order.contact_person = frappe.db.get_value(
			"Dynamic Link",
			{
				"parenttype": "Contact",
				"link_doctype": "Customer",
				"link_name": party,
				"parent": [
					"in",
					frappe.get_all("Contact Email", {"email_id": email}, pluck="parent") or [""],
				],
			},
			"parent",
		)
		sales_order.contact_email = email
	# the buyer's own reference, which ERPNext carries onto the invoice, and what they asked of the order
	sales_order.po_no = frappe.utils.strip_html(po_no or "").strip()[:140] or None
	sales_order.shop_order_note = frappe.utils.strip_html(order_note or "").strip()[:1000] or None
	set_shop_details(sales_order, order_quote, terms_accepted, business_buyer)
	totals.keep_prices(sales_order)
	sales_order.flags.ignore_permissions = True
	sales_order.insert(ignore_permissions=True)
	check_total(sales_order, order_quote)
	check_credit_limit(sales_order)
	sales_order.submit()
	return sales_order


def billing_address(party: str) -> str | None:
	"""The customer's billing address: their primary Billing address, else their latest one."""
	linked = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": party},
		pluck="parent",
	)
	if not linked:
		return None
	return frappe.db.get_value(
		"Address",
		{"name": ["in", linked], "address_type": "Billing", "disabled": 0},
		"name",
		order_by="is_primary_address desc, modified desc",
	)


def check_credit_limit(sales_order) -> None:
	"""ERPNext's credit limit check for an order paid on account, with a message meant for the shopper.
	It is invoiced straight away, so the limit is checked as ERPNext checks it on the invoice."""
	from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding

	if sales_order.get("shop_payment_method") != totals.ACCOUNT:
		return
	customer, company = sales_order.customer, sales_order.company
	limit = flt(get_credit_limit(customer, company))
	if not limit:
		return
	# two orders at once can't both fit under the limit: the second waits for the first
	frappe.db.get_value("Customer", customer, "name", for_update=True)
	if flt(get_customer_outstanding(customer, company)) + flt(sales_order.base_grand_total) > limit:
		frappe.throw(_("This order is over your account's credit limit. Please contact us to place it."))


def set_shop_details(sales_order, order_quote, terms_accepted: int, business_buyer: int) -> None:
	settings = frappe.get_cached_doc("Shop Settings")
	if not frappe.get_meta("Sales Order").has_field("shop_payment_method"):
		return
	method = order_quote.payment_method
	if totals.is_gateway(method):
		gateway = totals.gateway_row(method)
		sales_order.shop_payment_gateway = gateway.payment_gateway if gateway else None
		method = totals.GATEWAY
	sales_order.shop_payment_method = method
	if settings.get("order_naming_series"):
		sales_order.naming_series = settings.order_naming_series
	days = {
		totals.BANK: frappe.utils.cint(settings.get("bank_transfer_days")),
		totals.SWIFT: frappe.utils.cint(settings.get("bank_transfer_days")),
		totals.GATEWAY: frappe.utils.cint(settings.get("online_payment_days")),
	}.get(method)
	if days:
		sales_order.shop_payment_due = add_days(nowdate(), days)
	if order_quote.shipping:
		sales_order.shop_shipping_option = shipping_choice_json(order_quote)
	from shop.storefront import terms

	# an order made from a quote keeps the quote's terms
	if not (sales_order.get("tc_name") or sales_order.get("terms")):
		terms.apply_to(sales_order)
	if terms_accepted:
		sales_order.shop_terms_version = terms.version()
		sales_order.shop_terms_accepted_on = frappe.utils.now_datetime()
	sales_order.shop_business_buyer = 1 if business_buyer else 0


SHIPPING_FIELDS = ("id", "label", "amount", "carrier", "service", "meta", "warehouse")


def shipping_choice_json(order_quote) -> str:
	"""What the customer chose to ship with: one service, or one per parcel (with its warehouse)."""
	chosen = order_quote.get("shippings") or [order_quote.shipping]
	rows = [{key: row.get(key) for key in SHIPPING_FIELDS} for row in chosen]
	return json.dumps(rows if len(rows) > 1 else rows[0], default=str)


def check_total(sales_order, order_quote) -> None:
	"""The order must cost what the shopper was shown."""
	if abs(totals.order_total(sales_order) - flt(order_quote.total)) > 0.009:
		frappe.log_error(
			title="Shop order total differs from checkout",
			message=f"{totals.order_total(sales_order)} vs {order_quote.total}",
		)
		frappe.throw(_("We couldn't work out your total. Please try again or contact us."))


def convert_cart(cart, sales_order):
	cart.status = "Converted"
	cart.sales_order = sales_order.name
	cart.save(ignore_permissions=True)


def create_payment_request(sales_order, customer: dict) -> str | None:
	from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

	gateway = sales_order.get("shop_payment_gateway") or totals.gateway_row(totals.GATEWAY).payment_gateway
	account = totals.gateway_account(gateway, sales_order.currency)
	if not account or account.currency != sales_order.currency:
		frappe.throw(_("This order can't be paid online in {0}.").format(sales_order.currency))
	payment_request = make_payment_request(
		dt="Sales Order",
		dn=sales_order.name,
		recipient_id=customer.get("email"),
		payment_gateway_account=account.name,
		submit_doc=1,
		mute_email=1,
		return_doc=1,
	)
	return payment_request.get_payment_url()
