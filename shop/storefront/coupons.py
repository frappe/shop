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
		["disable", "rate_or_discount", "discount_percentage", "discount_amount", "min_amt"],
		as_dict=True,
	)
	if not rule or rule.disable:
		frappe.throw(_("That coupon code is not valid"))
	return frappe._dict(
		name=coupon.name,
		code=coupon.coupon_code,
		rate_or_discount=rule.rate_or_discount,
		discount_percentage=flt(rule.discount_percentage),
		discount_amount=flt(rule.discount_amount),
		min_amt=flt(rule.min_amt),
	)


def discount_for(coupon: dict, subtotal: float) -> float:
	if coupon.min_amt and subtotal < coupon.min_amt:
		frappe.throw(
			_("Add items worth {0} to use this coupon").format(pricing.format_amount(coupon.min_amt))
		)
	if coupon.rate_or_discount == "Discount Percentage":
		return flt(subtotal * coupon.discount_percentage / 100, 2)
	return min(flt(coupon.discount_amount), subtotal)


def redeem(name: str):
	frappe.db.set_value(
		"Coupon Code", name, "used", frappe.db.get_value("Coupon Code", name, "used") + 1
	)
