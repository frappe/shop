import frappe
from frappe import _
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import pricing

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
		or_filters = [["name", "like", term], ["customer_name", "like", term], ["contact_email", "like", term]]
	matched = frappe.get_all(
		"Sales Order",
		filters=filters,
		or_filters=or_filters,
		fields=LIST_FIELDS,
		order_by="creation desc",
		limit=MAX_SCAN,
	)
	decorate(matched)
	if payment:
		matched = [order for order in matched if order["payment_status"] == payment]
	start, limit = cint(start), min(cint(limit) or 20, 100)
	return {
		"orders": matched[start : start + limit],
		"total": len(matched),
		"statuses": [*STATUS_FILTERS, "Cancelled"],
	}


def decorate(orders: list) -> None:
	paid = paid_orders([order.name for order in orders])
	for order in orders:
		order["formatted_total"] = pricing.format_amount(order.grand_total)
		order["display_status"] = DISPLAY_STATUS.get(order.status, order.status)
		order["payment_status"] = "Paid" if order.name in paid else "Unpaid"
		order["fulfillment_status"] = fulfillment_label(order)


def fulfillment_label(order) -> str:
	if order.docstatus == 2:
		return "Cancelled"
	if flt(order.per_delivered) >= 100:
		return "Fulfilled"
	if flt(order.per_delivered) > 0:
		return "Partly fulfilled"
	return "Unfulfilled"


def paid_orders(names: list[str]) -> set:
	if not names:
		return set()
	rows = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Order", "reference_name": ["in", names], "docstatus": 1},
		pluck="reference_name",
	)
	return set(rows)


@frappe.whitelist()
def get_order(name: str) -> dict:
	only_managers()
	order = frappe.get_doc("Sales Order", name)
	return {
		"name": order.name,
		"customer": order.customer,
		"customer_name": order.customer_name,
		"contact_email": order.contact_email,
		"transaction_date": str(order.transaction_date),
		"delivery_date": str(order.delivery_date) if order.delivery_date else None,
		"status": order.status,
		"display_status": "Cancelled" if order.docstatus == 2 else DISPLAY_STATUS.get(order.status, order.status),
		"docstatus": order.docstatus,
		"payment_status": "Paid" if paid_orders([order.name]) else "Unpaid",
		"fulfillment_status": fulfillment_label(order),
		"address": address_display(order.shipping_address_name),
		"formatted_total": pricing.format_amount(order.total),
		"formatted_discount": pricing.format_amount(order.discount_amount) if order.discount_amount else None,
		"formatted_grand_total": pricing.format_amount(order.grand_total),
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": row.qty,
				"formatted_rate": pricing.format_amount(row.rate),
				"formatted_amount": pricing.format_amount(row.amount),
			}
			for row in order.items
		],
		"timeline": timeline(order),
	}


def timeline(order) -> list[dict]:
	events = [{"label": "Order placed", "on": str(order.creation)[:16]}]
	payment = frappe.db.get_value(
		"Payment Entry Reference",
		{"reference_doctype": "Sales Order", "reference_name": order.name, "docstatus": 1},
		"parent",
	)
	if payment:
		events.append(
			{"label": "Payment recorded", "on": str(frappe.db.get_value("Payment Entry", payment, "creation"))[:16]}
		)
	for note in frappe.get_all(
		"Delivery Note Item",
		filters={"against_sales_order": order.name, "docstatus": 1},
		fields=["parent", "creation"],
		group_by="parent",
	):
		events.append({"label": "Fulfilled", "on": str(note.creation)[:16]})
	if order.docstatus == 2:
		events.append({"label": "Order cancelled", "on": str(order.modified)[:16]})
	return events


def address_display(name: str | None) -> str | None:
	if not name:
		return None
	from frappe.contacts.doctype.address.address import get_address_display

	return get_address_display(name)


@frappe.whitelist(methods=["POST"])
def mark_paid(name: str, mode_of_payment: str | None = None) -> dict:
	only_managers()
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if paid_orders([name]):
		frappe.throw(_("This order is already marked paid"))
	entry = get_payment_entry("Sales Order", name)
	if mode_of_payment:
		entry.mode_of_payment = mode_of_payment
	entry.reference_no = name
	entry.reference_date = frappe.utils.nowdate()
	entry.flags.ignore_permissions = True
	entry.insert(ignore_permissions=True)
	entry.submit()
	from shop.fulfillment.service import auto_send

	auto_send(name)
	return get_order(name)


@frappe.whitelist(methods=["POST"])
def fulfill(name: str) -> dict:
	only_managers()
	from erpnext.selling.doctype.sales_order.mapper import make_delivery_note

	order = frappe.get_doc("Sales Order", name)
	if order.docstatus != 1:
		frappe.throw(_("Only submitted orders can be fulfilled"))
	if flt(order.per_delivered) >= 100:
		frappe.throw(_("This order is already fulfilled"))
	note = make_delivery_note(name)
	note.flags.ignore_permissions = True
	note.insert(ignore_permissions=True)
	note.submit()
	return get_order(name)


@frappe.whitelist(methods=["POST"])
def cancel_order(name: str) -> dict:
	only_managers()
	order = frappe.get_doc("Sales Order", name)
	order.flags.ignore_permissions = True
	order.cancel()
	return get_order(name)
