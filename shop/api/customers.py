import frappe
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import pricing


@frappe.whitelist()
def get_customers(search: str | None = None, start: int = 0, limit: int = 20) -> dict:
	only_managers()
	filters = {"disabled": 0}
	or_filters = None
	if search:
		term = f"%{search.strip()}%"
		or_filters = [["customer_name", "like", term], ["name", "like", term]]
	customers = frappe.get_all(
		"Customer",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "customer_name", "creation"],
		order_by="creation desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 100),
	)
	totals = order_totals([customer.name for customer in customers])
	emails = contact_emails([customer.name for customer in customers])
	for customer in customers:
		summary = totals.get(customer.name, {"orders": 0, "spent": 0.0, "last": None})
		customer["orders"] = summary["orders"]
		customer["formatted_spent"] = pricing.format_amount(summary["spent"])
		customer["last_order"] = summary["last"]
		customer["email"] = emails.get(customer.name)
		customer["joined"] = str(customer.creation)[:10]
		del customer["creation"]
	return {"customers": customers, "total": frappe.db.count("Customer", filters=filters)}


def order_totals(names: list[str]) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(
		"Sales Order",
		filters={"customer": ["in", names], "docstatus": 1},
		fields=["customer", "grand_total", "transaction_date"],
		order_by="transaction_date desc",
	)
	summary = {}
	for row in rows:
		entry = summary.setdefault(row.customer, {"orders": 0, "spent": 0.0, "last": None})
		entry["orders"] += 1
		entry["spent"] += flt(row.grand_total)
		entry["last"] = entry["last"] or str(row.transaction_date)
	return summary


def contact_emails(names: list[str]) -> dict:
	if not names:
		return {}
	links = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "link_doctype": "Customer", "link_name": ["in", names]},
		fields=["parent", "link_name"],
	)
	if not links:
		return {}
	emails = frappe.get_all(
		"Contact Email",
		filters={"parent": ["in", [link.parent for link in links]]},
		fields=["parent", "email_id"],
	)
	by_contact = {row.parent: row.email_id for row in emails}
	return {link.link_name: by_contact.get(link.parent) for link in links if by_contact.get(link.parent)}


@frappe.whitelist()
def get_customer(name: str) -> dict:
	only_managers()
	customer = frappe.get_doc("Customer", name)
	orders = frappe.get_all(
		"Sales Order",
		filters={"customer": name, "docstatus": ["<", 2]},
		fields=["name", "transaction_date", "status", "grand_total"],
		order_by="creation desc",
	)
	for order in orders:
		order["formatted_total"] = pricing.format_amount(order.grand_total)
	email = contact_emails([name]).get(name)
	return {
		"name": customer.name,
		"customer_name": customer.customer_name,
		"email": email,
		"joined": str(customer.creation)[:10],
		"orders": orders,
		"formatted_spent": pricing.format_amount(
			sum(flt(order.grand_total) for order in orders if order.status != "Cancelled")
		),
		"addresses": addresses(name),
		"reviews": reviews(email),
	}


def addresses(customer: str) -> list[dict]:
	names = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": customer},
		pluck="parent",
	)
	if not names:
		return []
	from frappe.contacts.doctype.address.address import get_address_display

	return [{"name": name, "display": get_address_display(name)} for name in names]


def reviews(email: str | None) -> list[dict]:
	if not email:
		return []
	return frappe.get_all(
		"Shop Review",
		filters={"user": email},
		fields=["product", "rating", "title", "creation"],
		order_by="creation desc",
		limit=10,
	)
