"""Customers made by store checkouts had no Customer Primary Contact, so ERPNext had no email for
them. Use their first linked contact that has an email."""

import frappe


def execute():
	customers = frappe.db.sql_list(
		"""select distinct so.customer from `tabSales Order` so
		join `tabShop Cart` cart on cart.sales_order = so.name
		join `tabCustomer` c on c.name = so.customer
		where ifnull(c.customer_primary_contact, '') = ''"""
	)
	for customer in customers:
		contact = frappe.db.sql(
			"""select c.name from `tabContact` c join `tabDynamic Link` l on l.parent = c.name
			where l.link_doctype = 'Customer' and l.link_name = %s and l.parenttype = 'Contact'
			and ifnull(c.email_id, '') != '' order by c.creation limit 1""",
			customer,
		)
		if contact:
			email, mobile = frappe.db.get_value("Contact", contact[0][0], ["email_id", "mobile_no"])
			frappe.db.set_value(
				"Customer",
				customer,
				{"customer_primary_contact": contact[0][0], "email_id": email, "mobile_no": mobile},
			)
