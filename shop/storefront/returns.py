import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime, now_datetime

from shop.storefront import orders as orders_module

RETURN_WINDOW_DAYS = 14
OPEN_STATUSES = ("Requested", "Approved")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_request(
	order: str,
	item_code: str,
	request_type: str,
	reason: str,
	qty: float = 1,
	token: str | None = None,
) -> dict:
	if not orders_module.can_view(order, token):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if request_type not in ("Return", "Replacement"):
		frappe.throw(_("Choose return or replacement"))
	if not (reason or "").strip():
		frappe.throw(_("Please tell us what went wrong"))
	doc = frappe.get_doc("Sales Order", order)
	validate_item(doc, item_code, qty)
	validate_window(doc)
	if frappe.db.exists(
		"Shop Return Request",
		{"sales_order": order, "item_code": item_code, "status": ["in", OPEN_STATUSES]},
	):
		frappe.throw(_("There is already an open request for this item"))
	request = frappe.get_doc(
		{
			"doctype": "Shop Return Request",
			"sales_order": order,
			"item_code": item_code,
			"request_type": request_type,
			"qty": flt(qty) or 1,
			"reason": reason.strip(),
		}
	).insert(ignore_permissions=True)
	return {"name": request.name, "status": request.status}


def validate_item(order, item_code: str, qty: float):
	row = next((item for item in order.items if item.item_code == item_code), None)
	if not row:
		frappe.throw(_("That item is not part of this order"))
	if flt(qty) > flt(row.qty):
		frappe.throw(_("You ordered only {0} of this item").format(int(row.qty)))


def validate_window(order):
	shipped_on = shipped_date(order.name)
	if not shipped_on:
		frappe.throw(_("Returns open once the order has shipped"))
	if now_datetime() > get_datetime(add_days(shipped_on, RETURN_WINDOW_DAYS)):
		frappe.throw(_("The {0}-day return window for this order has closed").format(RETURN_WINDOW_DAYS))


def shipped_date(order_name: str):
	shipment = orders_module.shipment_summary(order_name)
	if shipment and shipment.get("shipped_on"):
		return get_datetime(shipment["shipped_on"])
	delivered = frappe.db.get_value(
		"Delivery Note Item",
		{"against_sales_order": order_name, "docstatus": 1},
		"creation",
		order_by="creation asc",
	)
	return get_datetime(delivered) if delivered else None


def summary(order_name: str) -> dict:
	"""What the confirmation page needs: open/closed requests and whether new ones are allowed."""
	requests = frappe.get_all(
		"Shop Return Request",
		filters={"sales_order": order_name},
		fields=["name", "item_name", "request_type", "status", "resolution_note"],
		order_by="creation desc",
	)
	for request in requests:
		request.line = f"{request.request_type} · {request.item_name}"
	shipped_on = shipped_date(order_name)
	eligible = bool(
		shipped_on and now_datetime() <= get_datetime(add_days(shipped_on, RETURN_WINDOW_DAYS))
	)
	return {
		"requests": requests,
		"eligible": "true" if eligible else None,
		"has_requests": "true" if requests else None,
		"show": "true" if requests or eligible else None,
		"window_days": RETURN_WINDOW_DAYS,
	}
