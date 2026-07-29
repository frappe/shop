import frappe


@frappe.whitelist()
def check_app_permission() -> bool:
	if frappe.session.user == "Administrator":
		return True
	return "Shop Manager" in frappe.get_roles()
