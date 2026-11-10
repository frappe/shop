"""Customer statements from ERPNext's General Ledger: the account page download, and the store's
monthly Process Statement Of Accounts run for its trade Customer Group."""

import frappe
from frappe import _
from frappe.utils import add_months, getdate, nowdate

STATEMENT_MONTHS = 12
ROW_DOCTYPE = "Process Statement Of Accounts Customer"


def statement_doc(customers: list[str], company: str, from_date, to_date):
	"""An unsaved Process Statement Of Accounts for these customers, as ERPNext would run it."""
	doc = frappe.new_doc("Process Statement Of Accounts")
	doc.update(
		{
			"company": company,
			"report": "General Ledger",
			"from_date": from_date,
			"to_date": to_date,
			"orientation": "Portrait",
			"include_ageing": 1,
			"ageing_based_on": "Due Date",
			"include_break": 1,
			"categorize_by": "Categorize by Voucher (Consolidated)",
			"letter_head": letter_head_for(customers),
		}
	)
	for customer in customers:
		doc.append(
			"customers",
			{
				"customer": customer,
				"customer_name": frappe.db.get_value("Customer", customer, "customer_name"),
			},
		)
	return doc


def letter_head_for(customers: list[str]) -> str | None:
	"""The letterhead of the statement run the customer is in, so the download matches the
	statements they are emailed; otherwise the default letterhead."""
	run = frappe.db.get_value(
		ROW_DOCTYPE,
		{"customer": ["in", customers or [""]], "parenttype": "Process Statement Of Accounts"},
		"parent",
	)
	letter_head = run and frappe.db.get_value("Process Statement Of Accounts", run, "letter_head")
	return letter_head or frappe.db.get_value("Letter Head", {"is_default": 1, "disabled": 0})


@frappe.whitelist(methods=["GET"])
def statement_pdf():
	"""The signed-in customer's statement for the last 12 months, with ageing."""
	from erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts import (
		get_report_pdf,
	)

	from shop.storefront.checkout import elevated
	from shop.storefront.pricing import session_customer

	customer = session_customer()
	if not customer:
		raise frappe.PermissionError
	customers = [customer]
	company = frappe.get_cached_doc("Shop Settings").company
	to_date = getdate(nowdate())
	with elevated():
		pdf = get_report_pdf(
			statement_doc(customers, company, add_months(to_date, -STATEMENT_MONTHS), to_date)
		)
	if not pdf:
		frappe.throw(_("There is nothing on your account yet."), title=_("No statement"))
	frappe.local.response.filename = f"Statement {to_date}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


def sync_customer(doc, method=None) -> None:
	"""Customer on_update: when the store emails monthly statements, keep the customer list of its
	statement run (ERPNext's Process Statement Of Accounts for the trade Customer Group) as
	ERPNext's Fetch Customers fills it, making the run once the group has a customer."""
	settings = frappe.get_cached_doc("Shop Settings")
	group = settings.get("trade_customer_group")
	if not (group and settings.get("email_statements")):
		return
	before = doc.get_doc_before_save()
	if before and all(
		before.get(field) == doc.get(field) for field in ("customer_group", "email_id", "disabled")
	):
		return
	trade_groups = {group, *frappe.db.get_descendants("Customer Group", group)}
	if not {doc.customer_group, before.customer_group if before else None} & trade_groups:
		return
	from shop.setup_store import statement_pay_link, statement_run

	statement_run(
		settings.company,
		group,
		settings.store_name or frappe.get_cached_value("Company", settings.company, "company_name"),
	)
	for name in frappe.get_all(
		"Process Statement Of Accounts",
		filters={"customer_collection": "Customer Group", "collection_name": group},
		pluck="name",
	):
		run = frappe.get_doc("Process Statement Of Accounts", name)
		if "payment_link" not in (run.body or ""):
			# runs made before statements linked to payment
			run.body = (run.body or "") + statement_pay_link()
		customers = run_customers(group, run.primary_mandatory)
		if customers:
			run.set("customers", customers)
			run.enable_auto_email = 1
		else:
			# the group's last customer left: no one is sent statements
			run.enable_auto_email = 0
		run.flags.ignore_permissions = True
		run.save()


def run_customers(group: str, primary_mandatory: int) -> list[dict]:
	"""A statement run's customer rows for a Customer Group, as ERPNext's Fetch Customers makes them."""
	from erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts import (
		fetch_customers,
	)

	try:
		customers = fetch_customers("Customer Group", group, primary_mandatory)
	except frappe.ValidationError:
		frappe.clear_messages()
		return []
	return [
		{
			"customer": row["name"],
			"customer_name": row["customer_name"],
			"primary_email": row["primary_email"],
			"billing_email": row["billing_email"],
		}
		for row in customers
	]
