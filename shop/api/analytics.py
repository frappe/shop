import frappe
from frappe.utils import add_days, cint, flt, getdate, nowdate

from shop.api import only_managers
from shop.storefront import pricing


@frappe.whitelist()
def get_overview(days: int = 30) -> dict:
	only_managers()
	days = min(max(cint(days) or 30, 1), 365)
	start = add_days(nowdate(), -days + 1)
	orders = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1, "transaction_date": [">=", start]},
		fields=["name", "transaction_date", "grand_total", "status", "customer"],
	)
	revenue = sum(flt(order.grand_total) for order in orders)
	return {
		"days": days,
		"revenue": revenue,
		"formatted_revenue": pricing.format_amount(revenue),
		"orders": len(orders),
		"average_order_value": pricing.format_amount(revenue / len(orders)) if orders else pricing.format_amount(0),
		"units": units_sold(start),
		"customers": len({order.customer for order in orders}),
		"conversion": conversion_rate(start, len(orders)),
		"series": daily_series(orders, days),
		"top_products": top_products(start),
		"status_breakdown": status_breakdown(orders),
	}


def units_sold(start: str) -> float:
	rows = frappe.get_all(
		"Sales Order Item",
		filters={"docstatus": 1, "creation": [">=", start]},
		fields=["qty"],
	)
	return sum(flt(row.qty) for row in rows)


def conversion_rate(start: str, orders: int) -> float:
	"""Share of carts started in the window that became orders."""
	carts = frappe.db.count("Shop Cart", {"creation": [">=", start]})
	if not carts:
		return 0.0
	converted = frappe.db.count("Shop Cart", {"creation": [">=", start], "status": "Converted"})
	return round(min(converted * 100 / carts, 100), 1)


def daily_series(orders: list, days: int) -> list[dict]:
	buckets = {}
	for offset in range(days):
		day = add_days(nowdate(), -offset)
		buckets[str(getdate(day))] = {"date": str(getdate(day)), "revenue": 0.0, "orders": 0}
	for order in orders:
		bucket = buckets.get(str(getdate(order.transaction_date)))
		if bucket:
			bucket["revenue"] += flt(order.grand_total)
			bucket["orders"] += 1
	series = sorted(buckets.values(), key=lambda row: row["date"])
	for row in series:
		row["formatted_revenue"] = pricing.format_amount(row["revenue"])
	return series


def top_products(start: str, limit: int = 5) -> list[dict]:
	rows = frappe.get_all(
		"Sales Order Item",
		filters={"docstatus": 1, "creation": [">=", start]},
		fields=["item_code", "item_name", "qty", "amount"],
	)
	grouped = {}
	for row in rows:
		entry = grouped.setdefault(
			row.item_code, {"item_code": row.item_code, "item_name": row.item_name, "qty": 0.0, "revenue": 0.0}
		)
		entry["qty"] += flt(row.qty)
		entry["revenue"] += flt(row.amount)
	ranked = sorted(grouped.values(), key=lambda entry: entry["revenue"], reverse=True)[:limit]
	from shop.api.products import display_names

	names = display_names([entry["item_code"] for entry in ranked])
	for entry in ranked:
		entry["item_name"] = names.get(entry["item_code"], entry["item_name"])
		entry["formatted_revenue"] = pricing.format_amount(entry["revenue"])
	return ranked


def status_breakdown(orders: list) -> list[dict]:
	from shop.api.orders import DISPLAY_STATUS

	counts = {}
	for order in orders:
		label = DISPLAY_STATUS.get(order.status, order.status)
		counts[label] = counts.get(label, 0) + 1
	return [{"status": status, "count": count} for status, count in sorted(counts.items())]
