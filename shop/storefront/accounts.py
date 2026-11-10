"""Customer accounts: sign-up with the store's terms, trade account applications and approval,
and the account overview (orders, invoices, quotes)."""

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, cstr, flt, now_datetime, nowdate, validate_email_address

from shop.routes import signin_url, store_url
from shop.storefront import pricing

ACCOUNT_PATH = "account/orders"


def sync_customer_home_page() -> None:
	"""Frappe sends a signed-in customer to their role's home page: the store account while the
	store keeps customers in the store, else the site's own choice."""
	if not frappe.db.exists("Role", "Customer"):
		return
	current = cstr(frappe.db.get_value("Role", "Customer", "home_page"))
	store_home = store_url(ACCOUNT_PATH).lstrip("/")
	if frappe.db.get_single_value("Shop Settings", "customers_land_in_store"):
		wanted = store_home
	else:
		wanted = "" if current.endswith(ACCOUNT_PATH) else current
	if wanted != current:
		frappe.db.set_value("Role", "Customer", "home_page", wanted or None)
		frappe.cache.delete_key("home_page")


def account_page_redirect(context) -> None:
	"""Frappe's own account page (/me) sends a customer to their store account while the store keeps
	customers in the store; staff keep it."""
	if context.get("path") != "me" or frappe.session.user == "Guest":
		return
	if not frappe.db.get_single_value("Shop Settings", "customers_land_in_store"):
		return
	if frappe.get_cached_value("User", frappe.session.user, "user_type") != "Website User":
		return
	frappe.flags.redirect_location = store_url(ACCOUNT_PATH)
	raise frappe.Redirect(302)


def check_terms(accept_terms) -> None:
	from shop.storefront import terms

	if terms.required() and not cint(accept_terms):
		frappe.throw(_("Please accept the terms and conditions"))


# --- sign-up ---------------------------------------------------------------------


@frappe.whitelist(allow_guest=True)
def signup_url() -> str | None:
	"""The store's sign-up page, when it replaces the site's own sign-up."""
	if not frappe.db.get_single_value("Website Settings", "disable_signup"):
		return None
	return store_url("account/register")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 10)
def register(full_name: str, email: str, accept_terms: int = 0) -> dict:
	"""Create a store account. The customer accepts the terms here; a link to set the password
	is emailed."""
	check_terms(accept_terms)
	email = (email or "").strip().lower()
	full_name = frappe.utils.strip_html(full_name or "").strip()
	validate_email_address(email, throw=True)
	if not full_name:
		frappe.throw(_("Please enter your name"))
	if frappe.db.exists("User", email):
		frappe.throw(_("There's already an account for {0}. Sign in, or reset your password.").format(email))
	from shop.storefront.checkout import elevated

	with elevated():
		create_user(email, full_name)
		ensure_customer(email, full_name)
	return {"message": _("Check your email for a link to set your password.")}


def create_user(email: str, full_name: str, accepted: tuple | None = None, record_terms: bool = True) -> str:
	"""A Website User for a store customer; `accepted` is the (terms version, time) they accepted,
	now when not given. Staff adding a person record no acceptance for them (record_terms)."""
	from shop.storefront import terms

	first, _space, last = full_name.partition(" ")
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first,
			"last_name": last.strip() or None,
			"user_type": "Website User",
			"send_welcome_email": 1,
		}
	)
	if user.meta.has_field("shop_terms_version") and (accepted or (record_terms and terms.required())):
		user.shop_terms_version, user.shop_terms_accepted_on = accepted or (terms.version(), now_datetime())
	user.flags.ignore_permissions = True
	user.insert(ignore_permissions=True)
	if frappe.db.exists("Role", "Customer"):
		user.add_roles("Customer")
	return user.name


def ensure_customer(email: str, full_name: str) -> str:
	from shop.storefront.checkout import create_contact, find_customer_by_email

	existing = find_customer_by_email(email)
	if existing:
		return existing
	party = frappe.get_doc(
		{"doctype": "Customer", "customer_name": full_name, "customer_type": "Individual"}
	).insert(ignore_permissions=True)
	create_contact(party.name, {"full_name": full_name}, email)
	return party.name


# --- trade accounts ------------------------------------------------------------------

TRADE_FIELDS = (
	"company_name",
	"company_number",
	"tax_id",
	"industry",
	"website",
	"country",
	"message",
	"contact_name",
	"email",
	"phone",
	"address_line1",
	"address_line2",
	"city",
	"state",
	"pincode",
)


def trade_source() -> str:
	from shop.install import TRADE_SOURCE

	return TRADE_SOURCE


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 10)
def apply_trade(application: dict, accept_terms: int = 0) -> dict:
	"""A business applies for a trade account: an ERPNext Lead (UTM Source "Store Trade Application")
	with its contact, address and the terms they accepted. Staff approve it from the Lead."""
	if not frappe.get_cached_doc("Shop Settings").allow_trade_applications:
		frappe.throw(_("We aren't taking trade account applications."))
	check_terms(accept_terms)
	values = {field: frappe.utils.strip_html(cstr(application.get(field))).strip() for field in TRADE_FIELDS}
	values["email"] = values["email"].lower()
	validate_email_address(values["email"], throw=True)
	for field, label in (
		("company_name", _("business name")),
		("contact_name", _("your name")),
		("country", _("country")),
	):
		if not values[field]:
			frappe.throw(_("Please enter {0}").format(label))
	from shop.storefront.checkout import elevated
	from shop.storefront.shipping import valid_country

	values["country"] = valid_country(values["country"])
	if values["industry"] and not frappe.db.exists("Industry Type", values["industry"]):
		values["industry"] = ""
	with elevated():
		lead = application_lead(values["email"])
		if lead and lead.status == "Converted":
			# already approved: nothing to do, and the reply doesn't say whose account it is
			return {"message": _("Thanks. We'll review your application and email you.")}
		user = pricing.shopper()
		owner = user not in ("Guest", None) and user == values["email"]
		if lead and not (owner and lead.get("utm_source") == trade_source()):
			# anyone can type an email: an existing Lead is only noted, for staff to check, unless
			# its own signed-in customer is applying again to the store
			note_application(lead, values)
			return {"message": _("Thanks. We'll review your application and email you.")}
		lead = lead or frappe.new_doc("Lead")
		given = {
			"lead_name": values["contact_name"],
			"company_name": values["company_name"],
			"email_id": values["email"],
			"phone": values["phone"],
			"website": values["website"],
			"country": values["country"],
			"city": values["city"],
			"state": values["state"],
			"industry": values["industry"],
			"shop_tax_id": values["tax_id"],
			"shop_company_number": values["company_number"],
		}
		# applying again adds to the application; what was left blank keeps what was given before
		lead.update({field: value for field, value in given.items() if value})
		lead.update(
			{
				"company": frappe.get_cached_doc("Shop Settings").company,
				"utm_source": trade_source(),
				"status": "Open",
				"qualification_status": "In Process",
			}
		)
		note = values["message"] or (_("Applied again.") if not lead.is_new() else "")
		if note:
			lead.append("notes", {"note": frappe.utils.escape_html(note), "added_on": now_datetime()})
		from shop.storefront import terms

		if terms.required():
			lead.shop_terms_version = terms.version()
			lead.shop_terms_accepted_on = now_datetime()
		if owner:
			lead.shop_user = user
		lead.flags.ignore_permissions = True
		lead.save(ignore_permissions=True)
		if values["address_line1"] and values["city"]:
			add_address("Lead", lead.name, values)
		from shop.storefront import emails

		emails.send(
			"trade_application_staff",
			staff_emails(),
			lead,
			desk_url=frappe.utils.get_url(f"/desk/lead/{lead.name}"),
			review_url=review_url(lead.name),
		)
		emails.send("trade_application_received", values["email"], lead)
	return {"message": _("Thanks. We'll review your application and email you.")}


def note_application(lead, values: dict) -> None:
	"""Add an application for an existing Lead as a note, without changing the Lead, and tell staff."""
	from shop.storefront import emails

	details = ", ".join(
		f"{field}: {value}" for field, value in values.items() if value and field != "message"
	)
	note = _("Applied for a trade account again ({0}). Check these details before approving.").format(details)
	if values.get("message"):
		note += " " + values["message"]
	lead.append("notes", {"note": frappe.utils.escape_html(note), "added_on": now_datetime()})
	lead.flags.ignore_permissions = True
	lead.save(ignore_permissions=True)
	emails.send(
		"trade_application_staff",
		staff_emails(),
		lead,
		desk_url=frappe.utils.get_url(f"/desk/lead/{lead.name}"),
		review_url=review_url(lead.name),
	)


def review_url(lead: str) -> str:
	"""Where staff review an application in the Shop admin."""
	return frappe.utils.get_url(f"/shop/trade-accounts/applications/{lead}")


def application_lead(email: str):
	"""The Lead for this email, which a new application updates: ERPNext keeps one Lead per email."""
	name = frappe.db.get_value("Lead", {"email_id": email}, order_by="creation desc")
	return frappe.get_doc("Lead", name) if name else None


def staff_emails() -> list[str]:
	"""Who is told of trade applications, quote requests and returns: the store's staff
	notification emails, else every Shop Manager and Sales Manager."""
	listed = frappe.get_cached_doc("Shop Settings").get("staff_notification_emails")
	emails = [email.strip() for email in (listed or "").replace(",", "\n").splitlines() if email.strip()]
	if emails:
		return list(dict.fromkeys(emails))
	users = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["Shop Manager", "Sales Manager"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	return [
		u
		for u in frappe.get_all("User", filters={"name": ["in", users or [""]], "enabled": 1}, pluck="name")
		if u not in ("Administrator", "Guest")
	]


def trade_application(lead: str):
	doc = frappe.get_doc("Lead", lead)
	if doc.utm_source != trade_source():
		frappe.throw(_("This Lead is not a trade account application"))
	return doc


def trade_lead(lead: str):
	doc = trade_application(lead)
	doc.check_permission("write")
	return doc


def applicant_customer(lead) -> str | None:
	"""The customer an approval updates: the applicant's own, when they applied signed in to it.
	An email typed into the form alone isn't proof the applicant owns that account."""
	if not lead.get("shop_user"):
		return None
	from shop.storefront.orders import session_customers

	customers = session_customers(lead.shop_user)
	return customers[0] if customers else None


@frappe.whitelist()
def trade_defaults(lead: str) -> dict:
	"""What the approval dialog starts with: the store's trade Customer Group and its Payment
	Terms, and the customer the approval would update, if any."""
	doc = trade_lead(lead)
	group = frappe.get_cached_doc("Shop Settings").get("trade_customer_group")
	return {
		"customer_group": group,
		"payment_terms": frappe.db.get_value("Customer Group", group, "payment_terms") if group else None,
		"existing_customer": applicant_customer(doc),
	}


def set_trade_terms(
	customer,
	customer_group: str | None = None,
	payment_terms: str | None = None,
	credit_limit: float | None = None,
	allow_on_account: int = 0,
	price_list: str | None = None,
	exact: bool = False,
) -> None:
	"""A trade customer's terms on their Customer: the trade group and what staff set. Anything left
	unset keeps the customer's current value, unless exact: then the terms are what is given, so
	staff can also take them away (no payment terms, not on account, no credit limit)."""
	settings = frappe.get_cached_doc("Shop Settings")
	customer.customer_group = (
		customer_group or settings.get("trade_customer_group") or customer.customer_group
	)
	if price_list:
		customer.default_price_list = price_list
	if payment_terms or exact:
		customer.payment_terms = payment_terms or None
	if customer.meta.has_field("shop_allow_on_account"):
		customer.shop_allow_on_account = (
			1 if cint(allow_on_account) else (0 if exact else customer.get("shop_allow_on_account") or 0)
		)
	if flt(credit_limit) or (exact and credit_limit is not None):
		customer.credit_limits = [
			row for row in customer.get("credit_limits") or [] if row.company != settings.company
		]
	if flt(credit_limit):
		# the limit applies to what is invoiced on account; orders paid up front aren't held by it
		customer.append(
			"credit_limits",
			{"company": settings.company, "credit_limit": flt(credit_limit), "bypass_credit_limit_check": 1},
		)


@frappe.whitelist(methods=["POST"])
def approve_trade(
	lead: str,
	customer_group: str | None = None,
	payment_terms: str | None = None,
	credit_limit: float | None = None,
	allow_on_account: int = 0,
	price_list: str | None = None,
) -> dict:
	"""Approve a trade application from the Lead form, for a user who may change the Lead and the
	Customer it makes or updates."""
	doc = trade_lead(lead)
	existing = applicant_customer(doc)
	if existing:
		frappe.has_permission("Customer", "write", existing, throw=True)
	else:
		frappe.has_permission("Customer", "create", throw=True)
	return approve(doc, customer_group, payment_terms, credit_limit, allow_on_account, price_list)


def approve(
	doc,
	customer_group: str | None = None,
	payment_terms: str | None = None,
	credit_limit: float | None = None,
	allow_on_account: int = 0,
	price_list: str | None = None,
	approved_by: str | None = None,
) -> dict:
	"""Approve a trade application: ERPNext makes the Customer from the Lead (moving its contact and
	address over and marking it Converted), or the applicant's own customer is converted. The trade
	terms are set on the Customer and the applicant gets a store login."""
	if doc.status == "Converted":
		frappe.throw(_("This application has already been approved"))
	if cint(allow_on_account) and not payment_terms:
		frappe.throw(_("Set the Payment Terms to let them pay on account"))
	from erpnext.crm.doctype.lead.lead import _make_customer

	existing = applicant_customer(doc)
	if existing:
		customer = frappe.get_doc("Customer", existing)
		# the applicant's own account becomes the business they applied as
		customer.customer_name = doc.company_name or customer.customer_name
		customer.customer_type = "Company" if doc.company_name else customer.customer_type
		customer.lead_name = doc.name
		customer.tax_id = customer.tax_id or doc.shop_tax_id
	else:
		customer = _make_customer(doc.name, ignore_permissions=True)
		customer.tax_id = doc.shop_tax_id
	set_trade_terms(customer, customer_group, payment_terms, credit_limit, allow_on_account, price_list)
	user = (
		doc.shop_user
		or (doc.email_id if frappe.db.exists("User", doc.email_id) else None)
		or create_user(
			doc.email_id,
			doc.lead_name,
			accepted=(doc.shop_terms_version, doc.shop_terms_accepted_on)
			if doc.get("shop_terms_version")
			else None,
		)
	)
	if user not in [row.user for row in customer.get("portal_users") or []]:
		customer.append("portal_users", {"user": user})
	customer.flags.ignore_permissions = True
	customer.save(ignore_permissions=True) if existing else customer.insert(ignore_permissions=True)
	if existing:
		# the applicant's customer keeps its own contact; the Lead's address joins it
		for address in frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": "Address", "link_doctype": "Lead", "link_name": doc.name},
			pluck="parent",
		):
			address_doc = frappe.get_doc("Address", address)
			address_doc.append("links", {"link_doctype": "Customer", "link_name": customer.name})
			address_doc.save(ignore_permissions=True)
	doc.reload()
	doc.db_set(
		{
			"status": "Converted",
			"customer": customer.name,
			"qualification_status": "Qualified",
			"qualified_by": approved_by or frappe.session.user,
			"qualified_on": nowdate(),
		}
	)
	from shop.storefront import emails

	emails.send(
		"trade_account_approved",
		doc.email_id,
		doc,
		on_account=bool(cint(allow_on_account)),
		sign_in_url=frappe.utils.get_url(signin_url(store_url("account/orders"))),
	)
	return {"customer": customer.name, "user": user}


def add_address(link_doctype: str, link_name: str, values: dict) -> None:
	"""The applicant's address, unless it is on the application already."""
	known = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": link_doctype, "link_name": link_name},
		pluck="parent",
	)
	if known and frappe.db.exists(
		"Address",
		{"name": ["in", known], "address_line1": values.get("address_line1"), "city": values.get("city")},
	):
		return
	frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": values.get("company_name") or values.get("contact_name"),
			"address_type": "Billing",
			"address_line1": values.get("address_line1"),
			"address_line2": values.get("address_line2"),
			"city": values.get("city"),
			"state": values.get("state"),
			"pincode": values.get("pincode"),
			"country": values.get("country"),
			"phone": values.get("phone"),
			"email_id": values.get("email"),
			"links": [{"link_doctype": link_doctype, "link_name": link_name}],
		}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def decline_trade(lead: str, reason: str | None = None) -> None:
	"""Turn down a trade application from the Lead form."""
	decline(trade_lead(lead), reason)


def decline(doc, reason: str | None = None) -> None:
	"""Turn down a trade application: the Lead is marked Unqualified, with the reason as a note."""
	if doc.status == "Converted" or doc.qualification_status == "Unqualified":
		frappe.throw(_("This application has already been dealt with"))
	if reason:
		doc.append(
			"notes",
			{
				"note": frappe.utils.escape_html(reason),
				"added_by": frappe.session.user,
				"added_on": now_datetime(),
			},
		)
	doc.qualification_status = "Unqualified"
	doc.save(ignore_permissions=True)
	from shop.storefront import emails

	emails.send("trade_application_declined", doc.email_id, doc, reason=reason or "")


# --- account overview --------------------------------------------------------------


def trade_status() -> dict | None:
	"""The signed-in shopper's trade account: approved terms, or where their application stands."""
	customer = pricing.session_customer()
	user = pricing.shopper()
	if user in ("Guest", None):
		return None
	application = frappe.db.get_value(
		"Lead",
		{"email_id": user, "utm_source": trade_source()},
		["name", "status", "qualification_status"],
		as_dict=True,
		order_by="creation desc",
	)
	state = None
	if application:
		state = (
			"Approved"
			if application.status == "Converted"
			else ("Declined" if application.qualification_status == "Unqualified" else "Pending")
		)
	if not customer:
		return {"status": state} if state else None
	fields = ["customer_group", "payment_terms", "lead_name"] + (
		["shop_allow_on_account"] if frappe.get_meta("Customer").has_field("shop_allow_on_account") else []
	)
	values = frappe.db.get_value("Customer", customer, fields, as_dict=True)
	settings = frappe.get_cached_doc("Shop Settings")
	trade = (
		pricing.customer_price_list(customer) != settings.price_list
		or (settings.get("trade_customer_group") and values.customer_group == settings.trade_customer_group)
		or state == "Approved"
	)
	return {
		"trade": bool(trade),
		"status": state,
		"on_account": bool(values.get("shop_allow_on_account") and values.payment_terms),
		"payment_terms": values.payment_terms,
	}


def invoices(customers: list[str]) -> list[dict]:
	from shop.storefront import payment

	if not customers:
		return []
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"customer": ["in", customers], "docstatus": 1},
		fields=[
			"name",
			"posting_date",
			"due_date",
			"grand_total",
			"outstanding_amount",
			"currency",
			"status",
		],
		order_by="posting_date desc",
		limit=50,
	)
	for row in rows:
		row.formatted_total = frappe.utils.fmt_money(row.grand_total, currency=row.currency)
		row.formatted_outstanding = frappe.utils.fmt_money(row.outstanding_amount, currency=row.currency)
		row.pdf_url = "/api/method/shop.storefront.accounts.invoice_pdf?" + urlencode({"name": row.name})
		# the payment link an app gives unpaid invoices (the payments app's invoice links)
		row.pay_url = (
			payment.invoice_pay_url(row.name) if frappe.utils.flt(row.outstanding_amount) > 0 else None
		)
		row.overdue = (
			frappe.utils.flt(row.outstanding_amount) > 0
			and row.due_date
			and row.due_date < frappe.utils.getdate()
		)
	return rows


@frappe.whitelist(allow_guest=True)
def invoice_pdf(name: str, order: str | None = None, token: str | None = None):
	"""A customer's invoice as a PDF: their own when signed in, or with the order's private link."""
	from shop.storefront.orders import session_customers, valid_token

	customer = frappe.db.get_value("Sales Invoice", {"name": name, "docstatus": 1}, "customer")
	if not customer:
		raise frappe.PermissionError
	from_order = bool(
		order
		and token
		and valid_token(order, token)
		and frappe.db.exists("Sales Invoice Item", {"parent": name, "sales_order": order})
	)
	if not from_order and customer not in session_customers():
		raise frappe.PermissionError
	from shop.storefront.checkout import elevated

	with elevated():
		# name the print format, as the desk does: without it Frappe renders the default format
		# with the site's PDF generator instead of the one the format is built for
		print_format = frappe.get_meta("Sales Invoice").default_print_format or None
		pdf = frappe.get_print("Sales Invoice", name, print_format=print_format, as_pdf=True)
	frappe.local.response.filename = f"{name}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"
