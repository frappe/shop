"""The store's terms: the ERPNext Terms and Conditions record picked in Shop Settings. Orders and
quotations carry it (tc_name), and what a shopper accepted is recorded as its version and time."""

import frappe
from frappe.utils import format_datetime

from shop.routes import store_url


def settings():
	return frappe.get_cached_doc("Shop Settings")


def required() -> bool:
	return bool(settings().get("require_terms"))


def record() -> str | None:
	"""The Terms and Conditions record the store uses, if any (and not disabled)."""
	name = settings().get("terms_and_conditions")
	if name and not frappe.db.get_value("Terms and Conditions", name, "disabled"):
		return name
	return None


def version() -> str | None:
	name = record()
	if not name:
		return None
	modified = frappe.db.get_value("Terms and Conditions", name, "modified")
	return f"{name} ({format_datetime(modified, 'yyyy-MM-dd HH:mm')})"


def url() -> str:
	"""Where shoppers read the terms: the store's terms page, or an outside page if one is set."""
	return settings().get("terms_url") or (store_url("terms") if record() else "")


def details() -> dict | None:
	"""What the store's forms need to show the terms checkbox; None when terms aren't required."""
	if not required():
		return None
	return {
		"url": url(),
		"version": version() or "",
		"note": settings().get("terms_checkbox_note") or None,
		"business_label": settings().get("business_buyer_label") or None,
	}


def text(doc=None) -> str:
	"""The terms as HTML, rendered against a document as ERPNext does (its terms may use Jinja)."""
	name = record()
	if not name:
		return ""
	from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_and_conditions

	from shop.storefront.checkout import elevated

	with elevated():
		return get_terms_and_conditions(name, doc or {}) or ""


def apply_to(doc) -> None:
	"""Pick the store's terms on a quotation or order, as choosing them in the desk would.
	ERPNext fills in the text from the record when the document is saved."""
	name = record()
	if name and doc.meta.has_field("tc_name"):
		doc.tc_name = name
		doc.terms = None
