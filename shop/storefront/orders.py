import frappe
from frappe import _
from frappe.utils import cint

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
	customers = session_customers()
	if not customers:
		return []
	orders = frappe.get_all(
		"Sales Order",
		filters={"customer": ["in", customers], "docstatus": 1},
		fields=["name", "transaction_date", "status", "grand_total", "currency"],
		order_by="creation desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 50),
	)
	for order in orders:
		order.formatted_total = pricing.format_amount(order.grand_total)
		order.display_status = STATUS_LABELS.get(order.status, order.status)
		order.formatted_date = frappe.utils.formatdate(order.transaction_date, "d MMM yyyy")
		order.url = f"/order-confirmation/{order.name}"
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
	return order_summary(frappe.get_doc("Sales Order", name))


def can_view(name: str, token: str | None) -> bool:
	"""The cart token doubles as the guest secret; the signed-in owner needs no token."""
	if token and frappe.db.exists("Shop Cart", {"token": token, "sales_order": name}):
		return True
	customers = session_customers()
	return bool(customers) and frappe.db.get_value("Sales Order", name, "customer") in customers


def order_summary(order) -> dict:
	shipment = shipment_summary(order.name)
	return {
		"name": order.name,
		"status": order.status,
		"display_status": STATUS_LABELS.get(order.status, order.status),
		"progress": order_progress(order, shipment),
		"shipment": shipment,
		"awaiting_shipment": None if shipment else "true",
		"transaction_date": str(order.transaction_date),
		"total": order.total,
		"formatted_total": pricing.format_amount(order.total),
		"formatted_shipping": shipping_label(order),
		"discount_amount": order.discount_amount or None,
		"formatted_discount": pricing.format_amount(order.discount_amount)
		if order.discount_amount
		else None,
		"grand_total": order.grand_total,
		"formatted_grand_total": pricing.format_amount(order.grand_total),
		"taxes": [
			{"description": tax.description, "amount": tax.tax_amount, "formatted_amount": pricing.format_amount(tax.tax_amount)}
			for tax in order.taxes
		],
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": cart_module.display_qty(row.qty),
				"rate": row.rate,
				"formatted_rate": pricing.format_amount(row.rate),
				"amount": row.amount,
				"formatted_amount": pricing.format_amount(row.amount),
				"image": row.image,
			}
			for row in order.items
		],
	}


def order_progress(order, shipment: dict | None) -> list[dict]:
	if order.docstatus == 2:
		return [{"label": _("Cancelled"), "done": "true"}]
	paid = bool(order.advance_paid) or has_payment(order.name)
	shipped = bool(shipment and shipment.get("shipped_on")) or (order.per_delivered or 0) >= 100
	delivered = bool(shipment and shipment.get("status") == "Delivered")
	payment_label = _("Paid") if paid or expects_online_payment(order.name) else _("Payment on delivery")
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


def shipment_summary(order_name: str) -> dict | None:
	rows = frappe.get_all(
		"Shop Fulfillment",
		filters={"sales_order": order_name, "status": ["!=", "Cancelled"]},
		fields=["status", "carrier", "tracking_number", "tracking_url", "shipped_on"],
		order_by="creation desc",
		limit=1,
	)
	if not rows:
		return None
	shipment = rows[0]
	shipment.shipped_on = str(shipment.shipped_on) if shipment.shipped_on else None
	shipment.line = " · ".join(part for part in (shipment.carrier, shipment.tracking_number) if part)
	return shipment


def shipping_label(order) -> str:
	charge = sum(
		tax.tax_amount for tax in order.taxes if (tax.description or "").strip().lower() == "shipping"
	)
	return pricing.format_amount(charge) if charge else "Free"


def session_customers() -> list[str]:
	if frappe.session.user in ("Guest", None):
		return []
	contacts = frappe.get_all(
		"Contact Email", filters={"email_id": frappe.session.user}, pluck="parent"
	)
	if not contacts:
		return []
	return frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "parent": ["in", contacts], "link_doctype": "Customer"},
		pluck="link_name",
	)
