import frappe
from frappe import _
from frappe.utils import cint

from shop.routes import store_url, token_matches
from shop.storefront import cart as cart_module
from shop.storefront import pricing

STATUS_LABELS = {
	"To Deliver and Bill": "Processing",
	"To Deliver": "Processing",
	"To Bill": "Shipped",
	"Completed": "Delivered",
	"On Hold": "On hold",
}


@frappe.whitelist()
def get_orders(start: int = 0, limit: int = 20) -> list[dict]:
	"""The orders of the customer the signed-in shopper buys for."""
	from shop.storefront.pricing import session_customer

	customer = session_customer()
	if not customer:
		return []
	customers = [customer]
	orders = frappe.get_all(
		"Sales Order",
		filters={"customer": ["in", customers], "docstatus": 1},
		fields=["name", "transaction_date", "status", "grand_total", "currency"],
		order_by="creation desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 50),
	)
	from shop.storefront import payment, totals

	for order in orders:
		doc = frappe.get_doc("Sales Order", order.name)
		# the total and status the order page shows: awaiting payment, preparing, shipped...
		order.formatted_total = frappe.utils.fmt_money(totals.order_total(doc), currency=order.currency)
		order.display_status = display_status(doc, payment.is_paid(doc))
		order.formatted_date = frappe.utils.formatdate(order.transaction_date, "d MMM yyyy")
		order.url = store_url(f"order-confirmation/{order.name}")
	return orders


@frappe.whitelist()
def get_order(name: str) -> dict:
	order = frappe.get_doc("Sales Order", name)
	if order.customer not in session_customers():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return order_summary(order)


@frappe.whitelist(allow_guest=True)
def get_order_summary(name: str, token: str | None = None) -> dict:
	if not can_view(name, token):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return order_summary(frappe.get_doc("Sales Order", name), token)


def valid_token(name: str, token: str | None) -> bool:
	"""The cart token of the checkout that placed the order, or the order's own access token
	(orders made from an accepted quote)."""
	if not token or not name:
		return False
	if frappe.db.exists("Shop Cart", {"token": token, "sales_order": name}):
		return True
	return bool(
		frappe.get_meta("Sales Order").has_field("shop_access_token")
		and token_matches(frappe.db.get_value("Sales Order", name, "shop_access_token"), token)
	)


def access_token(order_name: str) -> str | None:
	"""The secret that opens an order's page without signing in: the checkout's cart token, or the
	order's own token (orders made from an accepted quote)."""
	token = frappe.db.get_value("Shop Cart", {"sales_order": order_name}, "token")
	if not token and frappe.get_meta("Sales Order").has_field("shop_access_token"):
		token = frappe.db.get_value("Sales Order", order_name, "shop_access_token")
	return token


def order_url(order_name: str) -> str:
	"""The order's page, with its token when it has one."""
	token = access_token(order_name)
	return store_url(f"order-confirmation/{order_name}" + (f"?token={token}" if token else ""))


def can_view(name: str, token: str | None) -> bool:
	"""The cart token doubles as the guest secret; the signed-in owner needs no token."""
	if valid_token(name, token):
		return True
	customers = session_customers()
	return bool(customers) and frappe.db.get_value("Sales Order", name, "customer") in customers


def order_summary(order, token: str | None = None) -> dict:
	from shop.storefront import payment, returns, totals

	shipment = shipment_summary(order.name)

	def fmt(amount):
		return frappe.utils.fmt_money(amount, currency=order.currency)

	products = [row for row in order.items if not totals.is_charge_item(row.item_code)]
	charges = [row for row in order.items if totals.is_charge_item(row.item_code)]
	lines, notes, factor = totals.shown_lines(order)
	product_total = sum(frappe.utils.flt(row.amount) for row in products)
	paid = payment.is_paid(order)
	method = payment.method(order)
	cancelled = is_cancelled(order)
	# an order staff entered in Desk was never confirmed by the store's emails
	from_store = placed_in_store(order)
	return {
		"returns": returns.summary(order.name),
		"confirmed": None if cancelled else "true",
		"emailed": "true" if from_store and not cancelled else None,
		"heading": _("Your order has been cancelled")
		if cancelled
		else _("Thank you for your order!")
		if from_store
		else _("Your order"),
		"name": order.name,
		"status": order.status,
		"display_status": display_status(order, paid),
		# signed in, the account lists every order; a guest keeps this page's own link
		"track_url": store_url("account/orders") if session_customers() else order_url(order.name),
		# an order waiting on an online payment is emailed once it is paid
		"confirmation_note": _("We've emailed you the details.")
		if cancelled
		else _("Your order is waiting for payment.")
		if order.docstatus == 1 and not paid and method == totals.GATEWAY
		else _("We've emailed you a copy of this order.")
		if from_store
		else _("Here's your order and where it's up to."),
		"progress": order_progress(order, shipment),
		"shipment": shipment,
		# paid, or to be paid on account or on delivery, and not sent yet
		"awaiting_shipment": "true"
		if not shipment
		and not cancelled
		and order.docstatus == 1
		and (paid or method in (totals.ACCOUNT, totals.COD, None))
		else None,
		"transaction_date": str(order.transaction_date),
		"currency": order.currency,
		"total": product_total,
		"formatted_total": fmt(product_total),
		"formatted_shipping": shipping_label(order, charges),
		"discount_amount": order.discount_amount or None,
		"formatted_discount": fmt(order.discount_amount) if order.discount_amount else None,
		"grand_total": totals.order_total(order),
		"formatted_grand_total": fmt(totals.order_total(order)),
		"charges": [
			{"label": row.description or row.item_name, "formatted_amount": fmt(row.amount)}
			for row in charges
		],
		"taxes": [
			{
				"description": tax.description,
				"amount": tax.tax_amount,
				"formatted_amount": fmt(tax.tax_amount),
			}
			for tax in order.taxes
			if not tax.included_in_print_rate and tax.tax_amount
		],
		"tax_note": " ".join(notes) or None,
		"payment_method": method,
		"paid": "true" if paid else None,
		"unpaid": None if paid or order.docstatus == 2 else "true",
		"bank_transfer": None if paid or order.docstatus == 2 else payment.bank_instructions(order),
		"pay_url": pay_url(order) if not paid and method == totals.GATEWAY and order.docstatus == 1 else None,
		"totals_html": totals_html(order, lines, notes, charges),
		"payment_html": payment_html(order, paid, method, token),
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": cart_module.display_qty(row.qty),
				"rate": row.rate,
				"formatted_rate": fmt(row.rate),
				"amount": row.amount,
				"formatted_amount": fmt(frappe.utils.flt(row.amount) * factor(row)),
				"image": row.image,
			}
			for row in products
		],
	}


def placed_in_store(order) -> bool:
	"""Checked out in the store or accepted from a quote, rather than entered by staff in Desk."""
	return bool(
		order.get("shop_payment_method")
		or order.get("shop_access_token")
		or frappe.db.exists("Shop Cart", {"sales_order": order.name})
	)


def totals_html(order, lines: list[dict], notes: list[str], charges) -> str:
	"""The order's money lines as ready-made HTML, so every theme shows the same breakdown."""
	from shop.storefront import totals

	esc = frappe.utils.escape_html

	def fmt(amount):
		return frappe.utils.fmt_money(amount, currency=order.currency)

	def line(label, amount, kind=""):
		return f'<div class="order-line {kind}"><span>{esc(label)}</span><span>{esc(amount)}</span></div>'

	html = line(lines[0]["label"], fmt(lines[0]["amount"]))
	if not any(row["kind"] == "shipping" for row in lines):
		html += line(_("Shipping"), shipping_label(order, charges))
	for row in lines[1:]:
		html += line(row["label"], fmt(row["amount"]), row["kind"])
	html += line(_("Total"), f"{fmt(totals.order_total(order))} {order.currency}", "total")
	return html + "".join(f'<p class="order-note">{esc(note)}</p>' for note in notes)


def invoice_url(invoice: str, order_name: str, token: str | None) -> str:
	"""The invoice PDF link; the order's private token lets guests open it without signing in."""
	from urllib.parse import urlencode

	params = {"name": invoice}
	if token:
		params.update(order=order_name, token=token)
	return "/api/method/shop.storefront.accounts.invoice_pdf?" + urlencode(params)


def payment_html(order, paid: bool, method: str | None, token: str | None) -> str:
	from shop.storefront import payment, totals

	esc = frappe.utils.escape_html
	if is_cancelled(order):
		return f'<div class="order-payment cancelled"><p>{esc(_("This order has been cancelled."))}</p></div>'
	if paid:
		invoice = payment.order_invoice(order.name)
		button = (
			f'<a class="order-pay-button" href="{esc(invoice_url(invoice, order.name, token))}">{esc(_("Download invoice"))}</a>'
			if invoice
			else ""
		)
		return (
			f'<div class="order-payment paid"><p>{esc(_("Payment received. Thank you."))}</p>{button}</div>'
		)
	if method == totals.ACCOUNT:
		invoice = payment.order_invoice(order.name)
		if not invoice:
			return ""
		due, owing = frappe.db.get_value("Sales Invoice", invoice, ["due_date", "outstanding_amount"])
		note = (
			_("On account: invoice {0}, due {1}.").format(invoice, frappe.utils.formatdate(due))
			if frappe.utils.flt(owing) > 0
			else _("Invoice {0} is paid. Thank you.").format(invoice)
		)
		link = payment.invoice_pay_url(invoice)
		pay = (
			f'<a class="order-pay-button" href="{esc(link)}">{esc(_("Pay invoice online"))}</a> '
			if link
			else ""
		)
		return (
			f'<div class="order-payment account"><p>{esc(note)}</p>{pay}'
			f'<a class="order-pay-button secondary" href="{esc(invoice_url(invoice, order.name, token))}">{esc(_("Download invoice"))}</a></div>'
		)
	if method in totals.BANK_METHODS:
		info = payment.bank_instructions(order)
		if not info:
			return ""
		details = "".join(f"<div>{esc(line)}</div>" for line in info["details"])
		due = f"<p>{esc(info['due_note'])}</p>" if info["due_note"] else ""
		return (
			f'<div class="order-payment bank"><h3>{esc(_("Pay by bank transfer"))}</h3>'
			f"<p>{esc(_('Amount'))}: <b>{esc(info['amount'])} {esc(info['currency'])}</b><br>"
			f"{esc(_('Reference'))}: <b>{esc(info['reference'])}</b></p>"
			f'<div class="bank-details">{details}</div>{due}'
			f"<p>{esc(_('We send your order as soon as the payment arrives.'))}</p></div>"
		)
	url = pay_url(order) if method == totals.GATEWAY else None
	if url:
		return (
			f'<div class="order-payment card"><p>{esc(_("This order is waiting for payment."))}</p>'
			f'<a class="order-pay-button" href="{esc(url)}">{esc(_("Pay now"))}</a></div>'
		)
	return ""


def display_status(order, paid: bool) -> str:
	from shop.storefront import totals

	if is_cancelled(order):
		return _("Cancelled")
	if not paid and order.get("shop_payment_method") in (*totals.BANK_METHODS, totals.GATEWAY):
		return _("Awaiting payment")
	shipment = shipment_summary(order.name)
	if shipment and shipment.collect and shipment.status == "Shipped":
		return _("Ready to collect")
	if shipment and shipment.collect and shipment.status == "Delivered":
		return _("Collected")
	if shipment and shipment.partly_shipped:
		return _("Partly shipped")
	if shipment and shipment.status in ("Pending", "Accepted"):
		return _("Preparing your order")
	if shipment and shipment.status == "Shipped":
		return _("Shipped")
	if shipment and shipment.status == "Delivered":
		return _("Delivered")
	return _(STATUS_LABELS.get(order.status, order.status))


def pay_url(order) -> str | None:
	"""Where to pay an order still owed online: its Payment Request's gateway page. Only shown to
	whoever may see the order."""
	return frappe.db.get_value(
		"Payment Request",
		{
			"reference_doctype": "Sales Order",
			"reference_name": order.name,
			"docstatus": 1,
			"status": ["!=", "Paid"],
		},
		"payment_url",
		order_by="creation desc",
	)


def is_cancelled(order) -> bool:
	"""Cancelled, or closed by the store when it cancelled an order already paid or invoiced."""
	from shop.storefront.payment import CANCELLED_BY_STORE

	return order.docstatus == 2 or (
		order.status == "Closed"
		and bool(
			frappe.db.exists(
				"Comment",
				{
					"reference_doctype": "Sales Order",
					"reference_name": order.name,
					"content": ["like", f"{CANCELLED_BY_STORE}%"],
				},
			)
		)
	)


def order_progress(order, shipment: dict | None) -> list[dict]:
	if is_cancelled(order):
		return [{"label": _("Cancelled"), "done": "true"}]
	from shop.storefront import payment, totals

	paid = bool(order.advance_paid) or has_payment(order.name) or payment.is_paid(order)
	# with a fulfilment, "shipped" means the courier has it, not that the stock was delivered
	if shipment:
		shipped = bool(shipment.get("shipped_on")) or shipment.get("status") in ("Shipped", "Delivered")
	else:
		shipped = (order.per_delivered or 0) >= 100
	delivered = bool(shipment and shipment.get("status") == "Delivered")
	method = order.get("shop_payment_method")
	if method == totals.ACCOUNT and not paid:
		payment_label, paid = _("Invoiced"), True
	elif paid:
		payment_label = _("Paid")
	elif method in (*totals.BANK_METHODS, totals.GATEWAY) or expects_online_payment(order.name):
		payment_label = _("Awaiting payment")
	else:
		payment_label = _("Payment on delivery")
	stages = [
		(_("Order placed"), True),
		(payment_label, paid),
		(_("Shipped"), shipped),
		(_("Delivered"), delivered),
	]
	return [{"label": label, "done": "true" if done else "false"} for label, done in stages]


def expects_online_payment(order_name: str) -> bool:
	return bool(
		frappe.db.exists(
			"Payment Request",
			{"reference_doctype": "Sales Order", "reference_name": order_name, "docstatus": 1},
		)
	)


def has_payment(order_name: str) -> bool:
	return bool(
		frappe.db.exists(
			"Payment Entry Reference",
			{"reference_doctype": "Sales Order", "reference_name": order_name, "docstatus": 1},
		)
	)


STAGES = {"Failed": 0, "Pending": 0, "Accepted": 1, "Shipped": 2, "Delivered": 3}


def collected_from(order, warehouse: str | None):
	"""The location the customer collects the parcel from this warehouse at, if they chose to."""
	from shop.fulfillment.service import chosen_option, is_pickup
	from shop.storefront.stock import location

	if not is_pickup(chosen_option(order, warehouse)):
		return None
	return location(warehouse) or frappe._dict(label=_("the store"), pickup_instructions="")


def collect_line(parcel) -> str:
	place = parcel.collect
	stage = STAGES.get(parcel.status, 0)
	if stage >= 3:
		return _("Collected from {0}.").format(place.label)
	if stage == 2:
		ready = _("Ready to collect from {0}.").format(place.label)
		return f"{ready} {place.pickup_instructions}".strip()
	return _("We're getting your order ready to collect from {0}.").format(place.label)


def unsent_warehouses(order_name: str, sent) -> list[str]:
	"""Warehouses the order's goods are sent from that have no fulfillment yet."""
	from shop.storefront.totals import is_charge_item

	rows = frappe.get_all(
		"Sales Order Item", filters={"parent": order_name}, fields=["item_code", "warehouse"], order_by="idx"
	)
	return list(
		dict.fromkeys(
			row.warehouse for row in rows if not is_charge_item(row.item_code) and row.warehouse not in sent
		)
	)


def shipment_summary(order_name: str) -> dict | None:
	"""Where the order's parcels are: one per warehouse it is sent from. The order is only as far
	along as its least advanced parcel, and is partly shipped while some are on their way."""
	rows = frappe.get_all(
		"Shop Fulfillment",
		filters={"sales_order": order_name, "status": ["!=", "Cancelled"]},
		fields=["status", "carrier", "tracking_number", "tracking_url", "shipped_on", "warehouse"],
		order_by="creation asc",
	)
	if not rows:
		return None
	latest = {}
	for row in rows:
		latest[row.warehouse] = row  # the latest fulfillment of each parcel
	if None not in latest:
		# a parcel not sent yet is still being prepared
		for warehouse in unsent_warehouses(order_name, latest):
			latest[warehouse] = frappe._dict(status="Pending", warehouse=warehouse)
	parcels = list(latest.values())
	order = frappe.get_doc("Sales Order", order_name)
	for parcel in parcels:
		parcel.shipped_on = str(parcel.shipped_on) if parcel.shipped_on else None
		parcel.collect = collected_from(order, parcel.warehouse)
		if parcel.collect:
			parcel.line = collect_line(parcel)
			continue
		parcel.line = " · ".join(part for part in (parcel.carrier, parcel.tracking_number) if part) or (
			_("We're getting your parcel ready to send.") if STAGES.get(parcel.status, 0) < 2 else None
		)
	least = min(parcels, key=lambda parcel: STAGES.get(parcel.status, 0))
	shipped = sorted(parcel.shipped_on for parcel in parcels if parcel.shipped_on)
	partly = len(parcels) > 1 and STAGES.get(least.status, 0) < 2 and bool(shipped)
	lines = [parcel.line for parcel in parcels if parcel.line]
	return frappe._dict(
		status=least.status,
		collect=all(parcel.collect for parcel in parcels),
		partly_shipped=partly,
		carrier=least.carrier,
		tracking_number=least.tracking_number,
		tracking_url=next((parcel.tracking_url for parcel in parcels if parcel.tracking_url), None),
		shipped_on=shipped[0] if shipped else None,
		last_shipped_on=shipped[-1] if shipped else None,
		line=" / ".join(dict.fromkeys(lines)) or None,
		parcels=parcels if len(parcels) > 1 else [],
	)


def shipping_label(order, charges=None) -> str:
	from shop.storefront import totals

	shipping_item = frappe.get_cached_doc("Shop Settings").get("shipping_item")
	charge = sum(row.amount for row in (charges or []) if shipping_item and row.item_code == shipping_item)
	shipping_account = frappe.get_cached_doc("Shop Settings").get("shipping_account")
	charge += sum(
		tax.tax_amount
		for tax in order.taxes
		if shipping_account and tax.account_head == shipping_account and tax.charge_type == "Actual"
	)
	return frappe.utils.fmt_money(charge, currency=order.currency) if charge else _("Free")


def session_customers(user: str | None = None) -> list[str]:
	user = user or getattr(frappe.local, "shop_shopper", None) or frappe.session.user
	if user in ("Guest", None):
		return []
	# customers the user is a Portal User of come first: they were given the account explicitly
	customers = frappe.get_all(
		"Portal User", filters={"parenttype": "Customer", "user": user}, pluck="parent"
	)
	contacts = frappe.get_all("Contact Email", filters={"email_id": user}, pluck="parent")
	if contacts:
		customers += frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": "Contact", "parent": ["in", contacts], "link_doctype": "Customer"},
			pluck="link_name",
		)
	return list(dict.fromkeys(customers))
