import frappe
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import pricing

LOW_STOCK_DEFAULT = 5


@frappe.whitelist()
def get_inventory(search: str | None = None, low_only: bool = False, start: int = 0, limit: int = 50) -> dict:
	only_managers()
	settings = frappe.get_cached_doc("Shop Settings")
	threshold = cint(settings.get("low_stock_threshold")) or LOW_STOCK_DEFAULT
	rows = tracked_items(search)
	relabel_variants(rows)
	quantities = stock_map([row["item_code"] for row in rows], settings.default_warehouse)
	for row in rows:
		row["stock"] = quantities.get(row["item_code"], 0)
		row["low"] = row["stock"] <= threshold
	if low_only:
		rows = [row for row in rows if row["low"]]
	start, limit = cint(start), min(cint(limit) or 50, 200)
	return {
		"items": rows[start : start + limit],
		"total": len(rows),
		"low_count": len([row for row in rows if row["low"]]),
		"threshold": threshold,
		"warehouse": warehouse_label(settings.default_warehouse),
	}


def relabel_variants(rows: list[dict]) -> None:
	from shop.api.products import display_names

	names = display_names([row["item_code"] for row in rows])
	for row in rows:
		row["label"] = names.get(row["item_code"], row["label"])


def warehouse_label(warehouse: str | None) -> str | None:
	if not warehouse:
		return warehouse
	return frappe.db.get_value("Warehouse", warehouse, "warehouse_name") or warehouse


def tracked_items(search: str | None) -> list[dict]:
	products = frappe.get_all(
		"Shop Product", fields=["name", "product_name", "item", "has_variants"], order_by="product_name"
	)
	rows = []
	for product in products:
		if product.has_variants:
			for variant in frappe.get_all(
				"Item", filters={"variant_of": product.item}, fields=["name", "item_name"]
			):
				rows.append(
					{
						"item_code": variant.name,
						"label": variant.item_name,
						"product": product.name,
						"product_name": product.product_name,
					}
				)
		else:
			rows.append(
				{
					"item_code": product.item,
					"label": product.product_name,
					"product": product.name,
					"product_name": product.product_name,
				}
			)
	if search:
		term = search.strip().lower()
		rows = [row for row in rows if term in row["label"].lower() or term in row["item_code"].lower()]
	return rows


def stock_map(item_codes: list[str], warehouse: str) -> dict:
	if not item_codes:
		return {}
	rows = frappe.get_all(
		"Bin",
		filters={"item_code": ["in", item_codes], "warehouse": warehouse},
		fields=["item_code", "actual_qty"],
	)
	return {row.item_code: row.actual_qty for row in rows}


@frappe.whitelist(methods=["POST"])
def set_stock(item_code: str, qty: float) -> dict:
	"""Reconcile an item to an exact quantity."""
	only_managers()
	settings = frappe.get_cached_doc("Shop Settings")
	rate = (pricing.get_price(item_code) or {}).get("rate") or 1
	reconciliation = frappe.get_doc(
		{
			"doctype": "Stock Reconciliation",
			"company": settings.company,
			"purpose": "Stock Reconciliation",
			"items": [
				{
					"item_code": item_code,
					"warehouse": settings.default_warehouse,
					"qty": flt(qty),
					"valuation_rate": flt(rate) * 0.6,
				}
			],
		}
	)
	reconciliation.flags.ignore_permissions = True
	reconciliation.insert(ignore_permissions=True)
	reconciliation.submit()
	return {"item_code": item_code, "stock": flt(qty)}
