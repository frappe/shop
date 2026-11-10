"""Trade (B2B) accounts in the Shop admin, kept as ERPNext records: the store's trade Customer Group,
its customers and their terms, and the applications to join it. Their rates are in
shop.api.pricing."""

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money

from shop.api import only_managers
from shop.install import TRADE_SOURCE as APPLICATION_SOURCE


def trade_group() -> str | None:
	return frappe.get_cached_doc("Shop Settings").get("trade_customer_group")


@frappe.whitelist()
def get_trade() -> dict:
	only_managers()
	group = trade_group()
	return {
		"customer_group": group,
		"payment_terms": frappe.db.get_value("Customer Group", group, "payment_terms") if group else None,
		"payment_terms_templates": frappe.get_all("Payment Terms Template", pluck="name"),
	}


@frappe.whitelist()
def get_trade_accounts(search: str | None = None, start: int = 0, limit: int = 20) -> dict:
	"""The store's trade customers with their terms, what they owe and how many rates of their own
	they have."""
	from erpnext.selling.doctype.customer.customer import get_customer_outstanding

	only_managers()
	group = trade_group()
	if not group:
		return {"enabled": False, "accounts": [], "total": 0}
	filters = {"customer_group": group, "disabled": 0}
	or_filters = None
	if search:
		term = f"%{search.strip()}%"
		or_filters = [["customer_name", "like", term], ["name", "like", term]]
	on_account = frappe.get_meta("Customer").has_field("shop_allow_on_account")
	accounts = frappe.get_all(
		"Customer",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "customer_name", "payment_terms", *(["shop_allow_on_account"] if on_account else [])],
		order_by="customer_name",
		start=cint(start),
		page_length=min(cint(limit) or 20, 100),
	)
	company = frappe.get_cached_doc("Shop Settings").company
	currency = frappe.get_cached_value("Company", company, "default_currency")
	for account in accounts:
		limit_amount = frappe.db.get_value(
			"Customer Credit Limit", {"parent": account.name, "company": company}, "credit_limit"
		)
		owing = get_customer_outstanding(account.name, company)
		account.update(
			{
				"allow_on_account": account.pop("shop_allow_on_account", 0),
				"formatted_credit_limit": fmt_money(limit_amount, currency=currency)
				if limit_amount
				else None,
				"formatted_outstanding": fmt_money(owing, currency=currency),
				"own_rates": frappe.db.count(
					"Pricing Rule",
					{"applicable_for": "Customer", "customer": account.name, "selling": 1, "disable": 0},
				),
				"people": frappe.db.count("Portal User", {"parent": account.name, "parenttype": "Customer"}),
			}
		)
	total = (
		frappe.db.count("Customer", filters)
		if not search
		else len(frappe.get_all("Customer", filters=filters, or_filters=or_filters, pluck="name"))
	)
	return {"enabled": True, "customer_group": group, "accounts": accounts, "total": total}


@frappe.whitelist(methods=["POST"])
def make_trade_customer(
	customer: str,
	payment_terms: str | None = None,
	allow_on_account: int = 0,
	credit_limit: float | None = None,
) -> dict:
	"""Make a customer a trade customer, with the terms an approved application gets."""
	from shop.storefront.accounts import set_trade_terms

	only_managers()
	if not trade_group():
		frappe.throw(_("Choose the trade customer group in Settings first"))
	if int(allow_on_account or 0) and not payment_terms:
		frappe.throw(_("Set the Payment Terms to let them pay on account"))
	doc = frappe.get_doc("Customer", customer)
	set_trade_terms(doc, None, payment_terms, credit_limit, allow_on_account, exact=True)
	doc.save(ignore_permissions=True)
	return trade_status(customer)


@frappe.whitelist(methods=["POST"])
def end_trade(customer: str) -> dict:
	"""Back to the group new customers join, without the trade terms approval gave: paying on
	account, payment terms, price list and the store company's credit limit."""
	only_managers()
	group = frappe.db.get_single_value("Selling Settings", "customer_group")
	if not group:
		frappe.throw(
			_("Set the default Customer Group in Selling Settings first, for the customer to move to")
		)
	doc = frappe.get_doc("Customer", customer)
	doc.customer_group = group
	doc.payment_terms = None
	doc.default_price_list = None
	company = frappe.get_cached_doc("Shop Settings").company
	doc.set("credit_limits", [row for row in doc.get("credit_limits") or [] if row.company != company])
	if doc.meta.has_field("shop_allow_on_account"):
		doc.shop_allow_on_account = 0
	doc.save(ignore_permissions=True)
	return trade_status(customer)


def trade_status(customer: str) -> dict:
	doc = frappe.get_doc("Customer", customer)
	company = frappe.get_cached_doc("Shop Settings").company
	limit = next((row.credit_limit for row in doc.get("credit_limits") or [] if row.company == company), None)
	group = trade_group()
	return {
		"enabled": bool(group),
		"is_trade": bool(group) and doc.customer_group == group,
		"customer_group": doc.customer_group,
		"payment_terms": doc.payment_terms,
		"allow_on_account": doc.get("shop_allow_on_account") or 0,
		"credit_limit": limit,
		"formatted_credit_limit": frappe.utils.fmt_money(
			limit, currency=frappe.get_cached_value("Company", company, "default_currency")
		)
		if limit
		else None,
	}


WAITING = {
	"utm_source": APPLICATION_SOURCE,
	"status": ["!=", "Converted"],
	"qualification_status": ["!=", "Unqualified"],
}
STATES = {
	"Waiting": WAITING,
	"Approved": {"utm_source": APPLICATION_SOURCE, "status": "Converted"},
	"Declined": {
		"utm_source": APPLICATION_SOURCE,
		"status": ["!=", "Converted"],
		"qualification_status": "Unqualified",
	},
}


def waiting_applications() -> int | None:
	"""Trade applications from the store not answered yet; None when the store has no trade accounts."""
	if not trade_group():
		return None
	return frappe.db.count("Lead", WAITING)


def application_state(lead) -> str:
	if lead.status == "Converted":
		return "Approved"
	if lead.qualification_status == "Unqualified":
		return "Declined"
	return "Waiting"


@frappe.whitelist()
def get_applications(state: str = "Waiting", start: int = 0, limit: int = 20) -> dict:
	"""Trade applications from the store that are waiting, approved or declined, newest first."""
	only_managers()
	if state not in STATES:
		frappe.throw(_("Unknown application state {0}").format(state))
	filters = STATES[state]
	return {
		"applications": frappe.get_all(
			"Lead",
			filters=filters,
			fields=["name", "company_name", "lead_name", "email_id", "country", "creation", "customer"],
			order_by="creation desc",
			start=cint(start),
			page_length=min(cint(limit) or 20, 100),
		),
		"total": frappe.db.count("Lead", filters),
		"enabled": bool(trade_group()),
	}


@frappe.whitelist()
def get_application(lead: str) -> dict:
	"""A trade application with what approving it starts from: the trade group's Payment Terms, and
	the applicant's own customer when approving updates it instead of making one."""
	from html import unescape

	from shop.api.orders import safe_address_display
	from shop.storefront.accounts import applicant_customer, trade_application

	only_managers()
	doc = trade_application(lead)
	group = trade_group()
	addresses = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Lead", "link_name": doc.name},
		pluck="parent",
	)
	return {
		"name": doc.name,
		"state": application_state(doc),
		"company_name": doc.company_name,
		"contact_name": doc.lead_name,
		"email": doc.email_id,
		"phone": doc.phone or doc.mobile_no,
		"website": doc.website,
		"industry": doc.industry,
		"country": doc.country,
		"tax_id": doc.get("shop_tax_id"),
		"company_number": doc.get("shop_company_number"),
		"applied_on": doc.creation,
		"signed_in_as": doc.get("shop_user"),
		"terms_accepted_on": doc.get("shop_terms_accepted_on"),
		"customer": doc.customer,
		"in_desk": frappe.has_permission("Lead", "read", doc),
		"existing_customer": None if doc.customer else applicant_customer(doc),
		"addresses": [{"name": name, "display": safe_address_display(name)} for name in addresses],
		"notes": [
			{
				"note": unescape(frappe.utils.strip_html(row.note or "")),
				"added_by": row.added_by,
				"added_on": row.added_on,
			}
			for row in doc.get("notes") or []
		],
		"trade_enabled": bool(group),
		"customer_group": group,
		"payment_terms": frappe.db.get_value("Customer Group", group, "payment_terms") if group else None,
		"payment_terms_templates": frappe.get_all("Payment Terms Template", pluck="name"),
	}


@frappe.whitelist(methods=["POST"])
def approve_application(
	lead: str,
	payment_terms: str | None = None,
	allow_on_account: int = 0,
	credit_limit: float | None = None,
) -> dict:
	"""Approve a trade application into the store's trade group, with these terms. ERPNext's
	Customer and Contact code needs permissions the Shop Manager role doesn't have in Desk."""
	from shop.storefront.accounts import approve, trade_application
	from shop.storefront.checkout import elevated

	only_managers()
	if not trade_group():
		frappe.throw(_("Choose the trade customer group in Settings first"))
	staff = frappe.session.user
	with elevated():
		return approve(
			trade_application(lead),
			payment_terms=payment_terms or None,
			credit_limit=credit_limit,
			allow_on_account=allow_on_account,
			approved_by=staff,
		)


@frappe.whitelist(methods=["POST"])
def decline_application(lead: str, reason: str | None = None) -> None:
	"""Turn down a trade application; the reason is emailed to the applicant."""
	from shop.storefront.accounts import decline, trade_application

	only_managers()
	decline(trade_application(lead), (reason or "").strip() or None)
