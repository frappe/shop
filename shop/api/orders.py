import frappe
from frappe import _
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import payment, pricing
from shop.storefront.checkout import elevated

MAX_SCAN = 500

DISPLAY_STATUS = {
	"To Deliver and Bill": "Open",
	"To Deliver": "Open",
	"To Pay": "Open",
	"To Bill": "Fulfilled",
	"On Hold": "On hold",
}

STATUS_FILTERS = {
	"Open": ["To Deliver and Bill", "To Deliver", "To Pay"],
	"Fulfilled": ["To Bill"],
	"Completed": ["Completed"],
}

LIST_FIELDS = [
	"name",
	"customer",
	"customer_name",
	"transaction_date",
	"delivery_date",
	"status",
	"grand_total",
	"currency",
	"per_delivered",
	"docstatus",
	"contact_email",
]


@frappe.whitelist()
def get_orders(
	status: str | None = None,
	payment: str | None = None,
	search: str | None = None,
	start: int = 0,
	limit: int = 20,
) -> dict:
	only_managers()
	filters = {"docstatus": ["<", 2]} if status != "Cancelled" else {"docstatus": 2}
	if status in STATUS_FILTERS:
		filters["status"] = ["in", STATUS_FILTERS[status]]
	or_filters = None
	if search:
		term = f"%{search.strip()}%"
		or_filters = [
			["name", "like", term],
			["customer_name", "like", term],
			["contact_email", "like", term],
		]
	matched = frappe.get_all(
		"Sales Order",
		filters=filters,
		or_filters=or_filters,
		fields=LIST_FIELDS,
		order_by="creation desc",
		limit=MAX_SCAN,
	)
	if payment:
		matched = [order for order in matched if payment_status_of(order) == payment]
	start, limit = cint(start), min(cint(limit) or 20, 100)
	orders = matched[start : start + limit]
	decorate(orders)
	return {
		"orders": orders,
		"total": len(matched),
		"statuses": [*STATUS_FILTERS, "Cancelled"],
	}


def payment_status_of(order) -> str:
	if "payment_status" not in order:
		order["payment_status"] = payment.payment_status(frappe.get_doc("Sales Order", order.name))
	return order["payment_status"]


def decorate(orders: list) -> None:
	"""The list's columns for the orders shown."""
	from shop.storefront.orders import shipment_summary

	for order in orders:
		shipment = shipment_summary(order.name) if order.docstatus != 2 else None
		order["formatted_total"] = pricing.document_amount(order.grand_total, order.currency)
		order["display_status"] = display_status(order, shipment)
		payment_status_of(order)
		order["fulfillment_status"] = fulfillment_label(order, shipment)


FULFILLMENT_LABELS = {
	"Pending": "Preparing",
	"Accepted": "Preparing",
	"Shipped": "Shipped",
	"Delivered": "Fulfilled",
	"Failed": "Unfulfilled",
}


UNKNOWN = object()


def display_status(order, shipment=UNKNOWN) -> str:
	"""The order's status for staff. ERPNext calls a delivered order To Bill, but one handed to a
	carrier is still open until the parcel ships."""
	from shop.storefront.orders import is_cancelled

	if is_cancelled(order):
		return "Cancelled"
	if order.status == "To Bill" and fulfillment_label(order, shipment) == "Preparing":
		return "Open"
	return DISPLAY_STATUS.get(order.status, order.status)


def fulfillment_label(order, shipment=UNKNOWN) -> str:
	"""For an order sent through a fulfilment provider, where the parcel is; else what ERPNext has
	delivered."""
	from shop.storefront.orders import shipment_summary

	if order.docstatus == 2:
		return "Cancelled"
	if shipment is UNKNOWN:
		shipment = shipment_summary(order.name)
	if shipment and shipment.partly_shipped:
		return "Partly shipped"
	if shipment:
		return FULFILLMENT_LABELS.get(shipment.status, "Preparing")
	if flt(order.per_delivered) >= 100:
		return "Fulfilled"
	if flt(order.per_delivered) > 0:
		return "Partly fulfilled"
	return "Unfulfilled"


@frappe.whitelist()
def get_order(name: str) -> dict:
	only_managers()
	order = frappe.get_doc("Sales Order", name)
	return {
		"name": order.name,
		"customer": order.customer,
		"customer_name": order.customer_name,
		"contact_email": order.contact_email,
		"currency": order.currency,
		"transaction_date": str(order.transaction_date),
		"delivery_date": str(order.delivery_date) if order.delivery_date else None,
		"status": order.status,
		"display_status": display_status(order),
		"docstatus": order.docstatus,
		"payment_status": payment.payment_status(order),
		"amount_due": payment.amount_due(order),
		"formatted_amount_due": pricing.document_amount(payment.amount_due(order), order.currency),
		"bank_accounts": bank_accounts(order),
		"refunds_due": payment.refunds_due(order.name),
		"fulfillment_status": fulfillment_label(order),
		"address": address_display(order.shipping_address_name),
		"po_no": order.po_no,
		"order_note": order.get("shop_order_note"),
		"formatted_total": pricing.document_amount(order.total, order.currency),
		"formatted_discount": pricing.document_amount(order.discount_amount, order.currency)
		if order.discount_amount
		else None,
		"formatted_grand_total": pricing.document_amount(order.grand_total, order.currency),
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": row.qty,
				"formatted_rate": pricing.document_amount(row.rate, order.currency),
				"formatted_amount": pricing.document_amount(row.amount, order.currency),
			}
			for row in order.items
		],
		"timeline": timeline(order),
	}


def timeline(order) -> list[dict]:
	events = [{"label": "Order placed", "on": str(order.creation)[:16]}]
	# a payment made before invoicing is moved onto the invoice by ERPNext; refunds pay credit notes
	invoices = frappe.get_all(
		"Sales Invoice Item",
		filters={"sales_order": order.name, "docstatus": 1},
		pluck="parent",
		distinct=True,
	)
	credit_notes = (
		frappe.get_all(
			"Sales Invoice", filters={"return_against": ["in", invoices], "docstatus": 1}, pluck="name"
		)
		if invoices
		else []
	)
	entries = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_name": ["in", [order.name, *invoices, *credit_notes]], "docstatus": 1},
		pluck="parent",
		distinct=True,
	)
	paid_seen = False
	for entry in frappe.get_all(
		"Payment Entry",
		filters={"name": ["in", entries]},
		fields=["payment_type", "creation"],
		order_by="creation",
	):
		if entry.payment_type == "Pay":
			events.append({"label": _("Refund sent"), "on": str(entry.creation)[:16]})
		elif not paid_seen:
			paid_seen = True
			events.append({"label": "Payment recorded", "on": str(entry.creation)[:16]})
	fulfillments = frappe.get_all(
		"Shop Fulfillment",
		filters={"sales_order": order.name},
		fields=["provider", "requested_on", "shipped_on", "delivered_on", "cancelled_on"],
		order_by="creation",
	)
	if fulfillments:
		from shop.fulfillment.service import provider_label

		for row in fulfillments:
			for label, on in (
				(_("Sent to {0}").format(provider_label(row.provider)), row.requested_on),
				(_("Shipped"), row.shipped_on),
				(_("Delivered"), row.delivered_on),
				(_("Shipment cancelled"), row.cancelled_on),
			):
				if on:
					events.append({"label": label, "on": str(on)[:16]})
	for note in frappe.get_all(
		"Delivery Note",
		filters={"name": ["in", delivery_notes(order.name)], "docstatus": 1},
		fields=["is_return", "creation"],
		order_by="creation",
	):
		if note.is_return:
			events.append({"label": _("Returned"), "on": str(note.creation)[:16]})
		elif not fulfillments:
			events.append({"label": _("Fulfilled"), "on": str(note.creation)[:16]})
	if order.docstatus == 2:
		events.append({"label": "Order cancelled", "on": str(order.modified)[:16]})
	# what the store and the payment gateway noted on the order, such as a disputed payment
	for note in frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Sales Order", "reference_name": order.name, "comment_type": "Info"},
		fields=["content", "creation"],
		order_by="creation",
	):
		events.append({"label": frappe.utils.strip_html(note.content), "on": str(note.creation)[:16]})
	return sorted(events, key=lambda event: event["on"])


def delivery_notes(order_name: str) -> list[str]:
	return frappe.get_all(
		"Delivery Note Item", filters={"against_sales_order": order_name}, pluck="parent", distinct=True
	)


def address_display(name: str | None) -> str | None:
	if not name:
		return None
	return safe_address_display(name)


def safe_address_display(name: str) -> str:
	"""ERPNext's address display, with what the customer typed escaped (Frappe doesn't clean
	values that read as JSON, and the template prints them as they are)."""
	from frappe.contacts.doctype.address.address import get_address_display

	address = frappe.get_doc("Address", name).as_dict()
	for field, value in address.items():
		if isinstance(value, str):
			address[field] = frappe.utils.escape_html(value)
	return get_address_display(address)


def bank_accounts(order) -> list[dict]:
	"""The company's Bank Accounts a payment for the order can be recorded into, the one the
	customer was told to pay into first."""
	from shop.storefront import totals

	told = totals.bank_account(order.currency, order.get("shop_payment_method"))
	rows = frappe.get_all(
		"Bank Account",
		filters={"company": order.company, "is_company_account": 1, "disabled": 0, "account": ["is", "set"]},
		fields=["name", "account"],
	)
	accounts = [
		{"name": row.name, "currency": frappe.get_cached_value("Account", row.account, "account_currency")}
		for row in rows
	]
	accounts.sort(
		key=lambda row: (row["name"] != (told and told.bank_account), row["currency"] != order.currency)
	)
	return accounts


@frappe.whitelist(methods=["POST"])
def refund(name: str, credit_note: str, method: str, bank_account: str | None = None) -> dict:
	"""Refund a credit note of the order, as staff approved it: to the card, or from a bank account."""
	only_managers()
	if method not in ("card", "bank"):
		frappe.throw(_("Choose how to refund: to the card or from a bank account"))
	if method == "bank" and not bank_account:
		frappe.throw(_("Choose the bank account the refund is paid from"))
	with elevated():
		payment.refund(name, credit_note, bank_account if method == "bank" else None)
	return get_order(name)


@frappe.whitelist(methods=["POST"])
def mark_paid(
	name: str,
	bank_account: str | None = None,
	amount: float | None = None,
	mode_of_payment: str | None = None,
) -> dict:
	"""Record a payment for the order with ERPNext's Payment Entry: what arrived, in the bank account
	it arrived in."""
	only_managers()
	with elevated():
		record_payment(name, bank_account, amount, mode_of_payment)
	return get_order(name)


def record_payment(name: str, bank_account: str | None, amount: float | None, mode_of_payment: str | None):
	# no amount is the whole amount due; an amount given has to be one
	if amount is not None and not flt(amount) > 0:
		frappe.throw(_("Enter the amount that arrived"))
	# a second request waits for the first, then sees the payment it recorded
	frappe.db.get_value("Sales Order", name, "name", for_update=True)
	order = frappe.get_doc("Sales Order", name)
	if payment.payment_status(order) == "Paid":
		frappe.throw(_("This order is already paid"))
	account = frappe.db.get_value("Bank Account", bank_account, "account") if bank_account else None
	same_currency = (
		not account or frappe.get_cached_value("Account", account, "account_currency") == order.currency
	)
	if amount and same_currency and flt(amount) > payment.amount_due(order) + 0.005:
		frappe.throw(_("That is more than the order still owes"))
	entry, _rate = payment.payment_entry_for(order, account, flt(amount) or None)
	if bank_account:
		entry.bank_account = bank_account
	if mode_of_payment:
		entry.mode_of_payment = mode_of_payment
	entry.reference_no = name
	entry.reference_date = frappe.utils.nowdate()
	entry.flags.ignore_permissions = True
	entry.insert(ignore_permissions=True)
	entry.submit()


@frappe.whitelist(methods=["POST"])
def fulfill(name: str) -> dict:
	only_managers()
	from shop.compat import make_delivery_note

	order = frappe.get_doc("Sales Order", name)
	if order.docstatus != 1:
		frappe.throw(_("Only submitted orders can be fulfilled"))
	if flt(order.per_delivered) >= 100:
		frappe.throw(_("This order is already fulfilled"))
	with elevated():
		note = make_delivery_note(name)
		note.flags.ignore_permissions = True
		note.insert(ignore_permissions=True)
		note.submit()
	return get_order(name)


@frappe.whitelist(methods=["POST"])
def cancel_order(name: str, note: str | None = None) -> dict:
	only_managers()
	with elevated():
		payment.cancel_by_store(name, note)
	return get_order(name)
