import frappe
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import pricing


@frappe.whitelist()
def get_carts(status: str = "Active", start: int = 0, limit: int = 20) -> dict:
	only_managers()
	filters = {"status": status} if status else {}
	carts = frappe.get_all(
		"Shop Cart",
		filters=filters,
		fields=["name", "user", "status", "last_active", "coupon_code", "sales_order"],
		order_by="last_active desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 100),
	)
	for cart in carts:
		cart.update(cart_contents(cart.name))
		cart["shopper"] = cart.user or "Guest"
		cart["last_active"] = str(cart.last_active)[:16] if cart.last_active else None
	return {
		"carts": carts,
		"total": frappe.db.count("Shop Cart", filters=filters),
		"open_value": open_value(),
	}


def cart_contents(name: str) -> dict:
	rows = frappe.get_all(
		"Shop Cart Item", filters={"parent": name}, fields=["item_code", "qty", "rate"]
	)
	value = sum(flt(row.qty) * flt(row.rate) for row in rows)
	return {
		"item_count": sum(flt(row.qty) for row in rows),
		"value": value,
		"formatted_value": pricing.format_amount(value),
		"items": [
			{"item_code": row.item_code, "qty": row.qty, "formatted_rate": pricing.format_amount(row.rate)}
			for row in rows
		],
	}


def open_value() -> str:
	names = frappe.get_all("Shop Cart", filters={"status": "Active"}, pluck="name")
	if not names:
		return pricing.format_amount(0)
	rows = frappe.get_all(
		"Shop Cart Item", filters={"parent": ["in", names]}, fields=["qty", "rate"]
	)
	return pricing.format_amount(sum(flt(row.qty) * flt(row.rate) for row in rows))
