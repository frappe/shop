import frappe

OLD_FIELDS = ("default_warehouse", "fulfillment_provider", "auto_send_to_fulfillment")


def execute():
	"""The store's one warehouse, fulfillment provider and automatic sending become its first
	fulfillment location."""
	values = dict(
		frappe.db.sql(
			"select field, value from `tabSingles` where doctype='Shop Settings' and field in %s",
			[OLD_FIELDS],
		)
	)
	settings = frappe.get_doc("Shop Settings")
	warehouse = values.get("default_warehouse")
	if warehouse and not settings.fulfillment_locations and frappe.db.exists("Warehouse", warehouse):
		row = settings.append(
			"fulfillment_locations",
			{
				"warehouse": warehouse,
				"fulfillment_provider": values.get("fulfillment_provider") or "manual",
				"auto_send": frappe.utils.cint(values.get("auto_send_to_fulfillment")),
			},
		)
		row.db_insert()
	frappe.db.delete("Singles", {"doctype": "Shop Settings", "field": ("in", OLD_FIELDS)})
	frappe.clear_document_cache("Shop Settings", "Shop Settings")
