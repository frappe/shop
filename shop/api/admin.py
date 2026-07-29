import frappe
from frappe.utils import add_days, cint, nowdate

from shop.storefront import pricing


@frappe.whitelist()
def check_app_permission() -> bool:
	if frappe.session.user == "Administrator":
		return True
	return "Shop Manager" in frappe.get_roles()


@frappe.whitelist()
def get_dashboard() -> dict:
	only_managers()
	return {
		"orders_today": frappe.db.count(
			"Sales Order", {"docstatus": 1, "transaction_date": nowdate()}
		),
		"revenue_week": pricing.format_amount(week_revenue()),
		"active_carts": frappe.db.count("Shop Cart", {"status": "Active"}),
		"published_products": frappe.db.count("Shop Product", {"published": 1}),
	}


@frappe.whitelist()
def get_orders(status: str | None = None, start: int = 0, limit: int = 20) -> list[dict]:
	only_managers()
	filters = {"docstatus": ["<", 2]}
	if status:
		filters["status"] = status
	orders = frappe.get_all(
		"Sales Order",
		filters=filters,
		fields=["name", "customer_name", "transaction_date", "status", "grand_total", "docstatus"],
		order_by="creation desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 100),
	)
	for order in orders:
		order.formatted_total = pricing.format_amount(order.grand_total)
	return orders


@frappe.whitelist()
def get_order(name: str) -> dict:
	only_managers()
	order = frappe.get_doc("Sales Order", name)
	return {
		"name": order.name,
		"customer_name": order.customer_name,
		"status": order.status,
		"docstatus": order.docstatus,
		"transaction_date": str(order.transaction_date),
		"grand_total": order.grand_total,
		"formatted_grand_total": pricing.format_amount(order.grand_total),
		"contact_email": order.contact_email,
		"address": address_display(order.shipping_address_name),
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": row.qty,
				"rate": row.rate,
				"formatted_rate": pricing.format_amount(row.rate),
				"formatted_amount": pricing.format_amount(row.amount),
			}
			for row in order.items
		],
	}


@frappe.whitelist(methods=["POST"])
def cancel_order(name: str) -> None:
	only_managers()
	order = frappe.get_doc("Sales Order", name)
	order.flags.ignore_permissions = True
	order.cancel()


@frappe.whitelist()
def search_items(query: str = "") -> list[dict]:
	only_managers()
	filters = {"disabled": 0, "variant_of": ["is", "not set"]}
	or_filters = None
	if query:
		term = f"%{query}%"
		or_filters = [["item_code", "like", term], ["item_name", "like", term]]
	return frappe.get_all(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "item_name", "item_group", "has_variants"],
		limit=20,
	)


def address_display(name: str | None) -> str | None:
	if not name:
		return None
	from frappe.contacts.doctype.address.address import get_address_display

	return get_address_display(name)


def week_revenue() -> float:
	rows = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1, "transaction_date": [">=", add_days(nowdate(), -7)]},
		fields=["grand_total"],
	)
	return sum(row.grand_total for row in rows)


def only_managers():
	frappe.only_for(("Shop Manager", "System Manager"))
