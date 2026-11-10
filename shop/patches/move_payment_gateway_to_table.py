import frappe

OLD_FIELDS = (
	"payment_gateway_account",
	"online_payment_label",
	"card_fee_percent",
	"card_fee_fixed",
	"card_fee_percent_international",
	"card_fee_fixed_international",
)


def execute():
	"""The store's one online payment gateway and its card fee become its first online gateway."""
	values = dict(
		frappe.db.sql(
			"select field, value from `tabSingles` where doctype='Shop Settings' and field in %s",
			[OLD_FIELDS],
		)
	)
	account = values.get("payment_gateway_account")
	gateway = account and frappe.db.get_value("Payment Gateway Account", account, "payment_gateway")
	settings = frappe.get_doc("Shop Settings")
	if gateway and not settings.payment_gateways:
		row = settings.append(
			"payment_gateways",
			{
				"payment_gateway": gateway,
				"label": values.get("online_payment_label") or "Pay Online",
				"fee_label": "Card fee",
				"fee_percent": values.get("card_fee_percent"),
				"fee_fixed": values.get("card_fee_fixed"),
				"fee_percent_international": values.get("card_fee_percent_international"),
				"fee_fixed_international": values.get("card_fee_fixed_international"),
			},
		)
		row.db_insert()
	frappe.db.delete("Singles", {"doctype": "Shop Settings", "field": ("in", OLD_FIELDS)})
	frappe.clear_document_cache("Shop Settings", "Shop Settings")
