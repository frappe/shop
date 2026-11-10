import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from shop.storefront import pricing


def resolve(code: str) -> dict:
	"""Validate a coupon code and return its discount terms. Throws on any problem."""
	name = frappe.db.get_value("Coupon Code", {"coupon_code": code.strip()})
	if not name:
		frappe.throw(_("That coupon code is not valid"))
	coupon = frappe.db.get_value(
		"Coupon Code",
		name,
		["name", "coupon_code", "pricing_rule", "valid_from", "valid_upto", "maximum_use", "used"],
		as_dict=True,
	)
	today = getdate(nowdate())
	if coupon.valid_from and getdate(coupon.valid_from) > today:
		frappe.throw(_("That coupon is not active yet"))
	if coupon.valid_upto and getdate(coupon.valid_upto) < today:
		frappe.throw(_("That coupon has expired"))
	if coupon.maximum_use and coupon.used >= coupon.maximum_use:
		frappe.throw(_("That coupon has been fully redeemed"))
	rule = frappe.db.get_value(
		"Pricing Rule",
		coupon.pricing_rule,
		["disable", "min_amt"],
		as_dict=True,
	)
	if not rule or rule.disable:
		frappe.throw(_("That coupon code is not valid"))
	return frappe._dict(name=coupon.name, code=coupon.coupon_code, min_amt=flt(rule.min_amt))


def check_minimum(coupon: dict, subtotal: float) -> None:
	"""Say how much more to add when the coupon's Pricing Rule has a minimum amount."""
	if coupon.min_amt and subtotal < coupon.min_amt:
		frappe.throw(
			_("This coupon is for orders of {0} or more: add {1} more to use it").format(
				pricing.display_amount(coupon.min_amt), pricing.display_amount(coupon.min_amt - subtotal)
			)
		)
