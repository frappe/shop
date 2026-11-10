"""ERPNext functions whose module moved between versions.

Shop targets ERPNext develop, where some functions were moved into new modules.
These wrappers use the new location when it exists and fall back to the
version-16 location, so Shop also runs on ERPNext v16.
"""


def make_delivery_note(sales_order: str):
	"""Unsaved Delivery Note mapped from a submitted Sales Order."""
	try:
		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note as make
	except ImportError:  # ERPNext v16
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as make
	return make(sales_order)


def get_sales_taxes(template: str) -> list[dict]:
	"""Tax rows of a Sales Taxes and Charges Template, ready to append to a sales document."""
	try:
		from erpnext.accounts.services.taxes import get_taxes_and_charges
	except ImportError:  # ERPNext v16
		from erpnext.controllers.accounts_controller import get_taxes_and_charges
	return get_taxes_and_charges("Sales Taxes and Charges Template", template) or []
