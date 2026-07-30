import frappe
from frappe import _
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import pricing

RULE_PREFIX = "Shop coupon"


@frappe.whitelist()
def get_coupons() -> list[dict]:
	only_managers()
	coupons = frappe.get_all(
		"Coupon Code",
		fields=["name", "coupon_name", "coupon_code", "pricing_rule", "used", "maximum_use", "valid_from", "valid_upto"],
		order_by="creation desc",
	)
	rules = rule_map([coupon.pricing_rule for coupon in coupons if coupon.pricing_rule])
	for coupon in coupons:
		rule = rules.get(coupon.pricing_rule, {})
		coupon["discount_type"] = (
			"Amount" if rule.get("rate_or_discount") == "Discount Amount" else "Percentage"
		)
		coupon["value"] = (
			rule.get("discount_amount")
			if coupon["discount_type"] == "Amount"
			else rule.get("discount_percentage")
		)
		coupon["discount_percentage"] = rule.get("discount_percentage")
		coupon["discount_amount"] = rule.get("discount_amount")
		coupon["min_amt"] = rule.get("min_amt")
		coupon["enabled"] = not rule.get("disable")
		coupon["value_label"] = value_label(rule)
	return coupons


def rule_map(names: list[str]) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(
		"Pricing Rule",
		filters={"name": ["in", names]},
		fields=["name", "rate_or_discount", "discount_percentage", "discount_amount", "min_amt", "disable"],
	)
	return {row.name: row for row in rows}


def value_label(rule: dict) -> str:
	if not rule:
		return ""
	if rule.get("rate_or_discount") == "Discount Percentage":
		return f"{flt(rule.get('discount_percentage'))}% off"
	return f"{pricing.format_amount(flt(rule.get('discount_amount')))} off"


@frappe.whitelist(methods=["POST"])
def save_coupon(payload: dict) -> None:
	only_managers()
	code = (payload.get("coupon_code") or "").strip().upper()
	if not code:
		frappe.throw(_("Coupon code is required"))
	existing = payload.get("name") or frappe.db.exists("Coupon Code", {"coupon_code": code})
	coupon = frappe.get_doc("Coupon Code", existing) if existing else frappe.new_doc("Coupon Code")
	rule = save_rule(payload, coupon.pricing_rule if existing else None, code)
	coupon.coupon_name = payload.get("coupon_name") or code
	coupon.coupon_type = "Promotional"
	coupon.coupon_code = code
	coupon.pricing_rule = rule
	coupon.valid_from = payload.get("valid_from") or None
	coupon.valid_upto = payload.get("valid_upto") or None
	coupon.maximum_use = cint(payload.get("maximum_use"))
	coupon.save(ignore_permissions=True) if existing else coupon.insert(ignore_permissions=True)


def save_rule(payload: dict, name: str | None, code: str) -> str:
	settings = frappe.get_cached_doc("Shop Settings")
	rule = frappe.get_doc("Pricing Rule", name) if name else frappe.new_doc("Pricing Rule")
	rule.title = f"{RULE_PREFIX} {code}"
	rule.apply_on = "Transaction"
	rule.price_or_product_discount = "Price"
	rule.selling = 1
	rule.coupon_code_based = 1
	rule.company = settings.company
	rule.apply_discount_on = "Grand Total"
	rule.disable = 0 if payload.get("enabled", True) else 1
	rule.min_amt = flt(payload.get("min_amt"))
	if payload.get("discount_type") == "Amount":
		rule.rate_or_discount = "Discount Amount"
		rule.discount_amount = flt(payload.get("value"))
		rule.discount_percentage = 0
	else:
		rule.rate_or_discount = "Discount Percentage"
		rule.discount_percentage = flt(payload.get("value"))
		rule.discount_amount = 0
	rule.save(ignore_permissions=True) if name else rule.insert(ignore_permissions=True)
	return rule.name


@frappe.whitelist(methods=["POST"])
def set_enabled(name: str, enabled: bool) -> None:
	only_managers()
	rule = frappe.db.get_value("Coupon Code", name, "pricing_rule")
	if rule:
		frappe.db.set_value("Pricing Rule", rule, "disable", 0 if enabled else 1)


@frappe.whitelist(methods=["POST"])
def delete_coupon(name: str) -> None:
	only_managers()
	rule = frappe.db.get_value("Coupon Code", name, "pricing_rule")
	title = frappe.db.get_value("Pricing Rule", rule, "title") if rule else None
	release_from_carts(name)
	frappe.delete_doc("Coupon Code", name, ignore_permissions=True)
	if title and title.startswith(RULE_PREFIX):
		frappe.delete_doc("Pricing Rule", rule, ignore_permissions=True, force=True)


def release_from_carts(coupon: str) -> None:
	"""A coupon sitting in someone's cart must not make itself undeletable."""
	for cart in frappe.get_all("Shop Cart", filters={"coupon_code": coupon}, pluck="name"):
		frappe.db.set_value("Shop Cart", cart, "coupon_code", None, update_modified=False)
