import frappe
from frappe import _
from frappe.utils import cint

from shop.storefront import cart as cart_module
from shop.storefront import pricing


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
	return orders


@frappe.whitelist()
def get_order(name: str) -> dict:
	order = frappe.get_doc("Sales Order", name)
	if order.customer not in session_customers():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return order_summary(order)


@frappe.whitelist(allow_guest=True)
def get_order_summary(name: str, token: str) -> dict:
	if not token or not frappe.db.exists("Shop Cart", {"token": token, "sales_order": name}):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return order_summary(frappe.get_doc("Sales Order", name))


def order_summary(order) -> dict:
	return {
		"name": order.name,
		"status": order.status,
		"transaction_date": str(order.transaction_date),
		"total": order.total,
		"formatted_total": pricing.format_amount(order.total),
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
