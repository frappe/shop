"""Addresses suggested in the storefront's address forms. The lookup belongs to another app (ERPNext
Shipping), registered in the `shop_address_lookup` hook as a module with:

	suggestions(text, country, session) -> {"enabled", "suggestions": [{id, label, detail, address?}], "attribution"}
	details(id, session) -> {address_line1, address_line2, city, state, pincode, country}
	status() -> {"enabled", "service", "settings_url"}

These endpoints let shoppers who aren't signed in use it, limited per visitor."""

import frappe
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=90, seconds=60)
def suggest(text: str, country: str | None = None, session: str | None = None) -> dict:
	lookup = provider()
	if not lookup:
		return {"enabled": False, "suggestions": []}
	return lookup.suggestions(text, country, session)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=60)
def address(id: str, session: str | None = None) -> dict:
	lookup = provider()
	if not lookup:
		frappe.throw(frappe._("No address lookup is installed"))
	return lookup.details(id, session)


def status() -> dict:
	lookup = provider()
	return {"installed": bool(lookup), **(lookup.status() if lookup else {"enabled": False})}


def provider():
	modules = frappe.get_hooks("shop_address_lookup")
	return frappe.get_module(modules[-1]) if modules else None
