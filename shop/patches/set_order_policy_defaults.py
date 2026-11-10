import frappe

DEFAULTS = (
	("return_window_days", 14),
	("quote_valid_days", 30),
	("payment_reminder_hours", 1),
	("delivery_days", 3),
	("allow_trade_applications", 1),
	("customers_land_in_store", 1),
)


def execute():
	"""Stores made before these were settings keep what they did: a 14 day return window, quotes
	valid for 30 days, a payment reminder after an hour, delivery dates three days on and trade
	applications open. Customers land in the store after signing in. A value a store already saved
	is kept."""
	for field, value in DEFAULTS:
		saved = frappe.db.sql(
			"select 1 from `tabSingles` where doctype = 'Shop Settings' and field = %s", field
		)
		if not saved:
			frappe.db.set_single_value("Shop Settings", field, value)
