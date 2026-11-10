import frappe
from frappe import _
from frappe.utils import cint, flt, validate_email_address

from shop.api import only_managers
from shop.api.trade import trade_status
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
		fields=["customer", "base_grand_total", "transaction_date"],
		order_by="transaction_date desc",
	)
	summary = {}
	for row in rows:
		entry = summary.setdefault(row.customer, {"orders": 0, "spent": 0.0, "last": None})
		entry["orders"] += 1
		entry["spent"] += flt(row.base_grand_total)
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
		fields=["name", "transaction_date", "status", "grand_total", "currency", "base_grand_total"],
		order_by="creation desc",
	)
	for order in orders:
		order["formatted_total"] = pricing.document_amount(order.grand_total, order.currency)
	email = contact_emails([name]).get(name)
	return {
		"name": customer.name,
		"customer_name": customer.customer_name,
		"email": email,
		"joined": str(customer.creation)[:10],
		"orders": orders,
		"formatted_spent": pricing.format_amount(
			sum(flt(order.base_grand_total) for order in orders if order.status != "Cancelled")
		),
		"addresses": addresses(name),
		"reviews": reviews(email),
		"trade": trade_status(name),
		"people": people(name),
	}


def addresses(customer: str) -> list[dict]:
	names = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": customer},
		pluck="parent",
	)
	if not names:
		return []
	from shop.api.orders import safe_address_display

	return [{"name": name, "display": safe_address_display(name)} for name in names]


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


def people(customer: str) -> list[dict]:
	"""The customer's Portal Users: the people who sign in to the store and buy for it."""
	users = [row.user for row in frappe.get_doc("Customer", customer).get("portal_users") or []]
	if not users:
		return []
	found = {
		row.name: row
		for row in frappe.get_all(
			"User",
			filters={"name": ["in", users]},
			fields=["name", "full_name", "enabled", "user_type", "last_login"],
		)
	}
	return [
		{
			"user": user,
			"full_name": found[user].full_name or user,
			"can_sign_in": bool(found[user].enabled),
			"staff": found[user].user_type == "System User",
			"last_login": str(found[user].last_login) if found[user].last_login else None,
		}
		for user in users
		if user in found
	]


def person_of(customer: str, user: str) -> None:
	if user not in [row.user for row in frappe.get_doc("Customer", customer).get("portal_users") or []]:
		frappe.throw(_("{0} is not one of this customer's people").format(user))


@frappe.whitelist(methods=["POST"])
def add_person(customer: str, full_name: str, email: str) -> list[dict]:
	"""Let a person sign in to the store and buy for the customer: a Website User (emailed a link to
	set their password) on the customer's Portal Users, with a Contact linked to the customer."""
	only_managers()
	from shop.storefront.accounts import create_user
	from shop.storefront.checkout import create_contact

	email = (email or "").strip().lower()
	full_name = frappe.utils.strip_html(full_name or "").strip()
	validate_email_address(email, throw=True)
	if not full_name:
		frappe.throw(_("Enter the person's name"))
	doc = frappe.get_doc("Customer", customer)
	user_type = frappe.db.get_value("User", email, "user_type")
	if user_type == "System User":
		message = _("{0} is a staff login. Staff use Desk; add a separate email for buying in the store.")
		frappe.throw(message.format(email))
	if not user_type:
		create_user(email, full_name, record_terms=False)
	elif frappe.db.exists("Role", "Customer") and "Customer" not in frappe.get_roles(email):
		frappe.get_doc("User", email).add_roles("Customer")
	if email not in [row.user for row in doc.get("portal_users") or []]:
		doc.append("portal_users", {"user": email})
		doc.save(ignore_permissions=True)
	contact = frappe.db.get_value("Contact Email", {"email_id": email}, "parent")
	if not contact:
		create_contact(customer, {"full_name": full_name}, email)
	elif not frappe.db.exists(
		"Dynamic Link",
		{"parenttype": "Contact", "parent": contact, "link_doctype": "Customer", "link_name": customer},
	):
		contact_doc = frappe.get_doc("Contact", contact)
		contact_doc.append("links", {"link_doctype": "Customer", "link_name": customer})
		contact_doc.save(ignore_permissions=True)
	return people(customer)


@frappe.whitelist(methods=["POST"])
def remove_person(customer: str, user: str) -> list[dict]:
	"""Stop a person buying for the customer. Their login stays, with any other accounts it has."""
	only_managers()
	person_of(customer, user)
	doc = frappe.get_doc("Customer", customer)
	doc.set("portal_users", [row for row in doc.portal_users if row.user != user])
	doc.save(ignore_permissions=True)
	for contact in frappe.get_all("Contact Email", filters={"email_id": user}, pluck="parent"):
		contact_doc = frappe.get_doc("Contact", contact)
		links = [
			link
			for link in contact_doc.links
			if not (link.link_doctype == "Customer" and link.link_name == customer)
		]
		if len(links) != len(contact_doc.links):
			contact_doc.set("links", links)
			contact_doc.save(ignore_permissions=True)
	return people(customer)


@frappe.whitelist(methods=["POST"])
def send_password_reset(customer: str, user: str) -> dict:
	"""Email the person a link to set a new password."""
	only_managers()
	person_of(customer, user)
	doc = frappe.get_doc("User", user)
	if doc.user_type != "Website User":
		frappe.throw(_("{0} is a staff login; manage it in Desk").format(user))
	if not doc.enabled:
		frappe.throw(_("Turn {0}'s sign-in on first").format(user))
	doc._reset_password(send_email=True)
	return {"message": _("Password reset link sent to {0}").format(user)}


@frappe.whitelist(methods=["POST"])
def set_sign_in(customer: str, user: str, enabled: int) -> list[dict]:
	"""Turn a person's store sign-in on or off. Staff logins are managed in Desk."""
	only_managers()
	person_of(customer, user)
	doc = frappe.get_doc("User", user)
	if doc.user_type != "Website User":
		frappe.throw(_("{0} is a staff login; manage it in Desk").format(user))
	doc.enabled = 1 if cint(enabled) else 0
	doc.save(ignore_permissions=True)
	return people(customer)
