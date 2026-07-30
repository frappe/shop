import frappe


def only_managers():
	frappe.only_for(("Shop Manager", "System Manager"))
