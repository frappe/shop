import frappe
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import pricing, stock

LOW_STOCK_DEFAULT = 5


@frappe.whitelist()
def get_inventory(
	search: str | None = None,
	low_only: bool = False,
	start: int = 0,
	limit: int = 50,
	warehouse: str | None = None,
) -> dict:
	only_managers()
	settings = frappe.get_cached_doc("Shop Settings")
	warehouse = store_warehouse(warehouse)
	threshold = cint(settings.get("low_stock_threshold")) or LOW_STOCK_DEFAULT
	rows = tracked_items(search)
	relabel_variants(rows)
	quantities = stock_map([row["item_code"] for row in rows], warehouse)
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
		"warehouse": warehouse,
		"warehouses": [{"value": name, "label": warehouse_label(name)} for name in stock.warehouses()],
	}


def store_warehouse(warehouse: str | None) -> str | None:
	"""One of the store's warehouses: the one asked for, else its first."""
	if not warehouse:
		return stock.primary_warehouse()
	if warehouse not in stock.warehouses():
		frappe.throw(frappe._("{0} is not one of the store's warehouses").format(warehouse))
	return warehouse


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


def valuation_rate(item_code: str, warehouse: str) -> float:
	"""What ERPNext values the item at: its current valuation in the warehouse, else the Valuation
	Rate set on the Item."""
	current = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "valuation_rate")
	return flt(current) or flt(frappe.db.get_value("Item", item_code, "valuation_rate"))


@frappe.whitelist(methods=["POST"])
def set_stock(item_code: str, qty: float, warehouse: str | None = None) -> dict:
	"""Reconcile an item to an exact quantity in one of the store's warehouses."""
	only_managers()
	settings = frappe.get_cached_doc("Shop Settings")
	warehouse = store_warehouse(warehouse)
	if not warehouse:
		frappe.throw(frappe._("Add a warehouse under Fulfillment locations in Settings first"))
	row = {"item_code": item_code, "warehouse": warehouse, "qty": flt(qty)}
	# valued as ERPNext values it, never made up from the selling price
	rate = valuation_rate(item_code, warehouse)
	if rate:
		row["valuation_rate"] = rate
	else:
		# no cost known yet: ERPNext's zero valuation, until a Valuation Rate is set on the Item
		row["allow_zero_valuation_rate"] = 1
	reconciliation = frappe.get_doc(
		{
			"doctype": "Stock Reconciliation",
			"company": settings.company,
			"purpose": "Stock Reconciliation",
			"items": [row],
		}
	)
	reconciliation.flags.ignore_permissions = True
	from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
		EmptyStockReconciliationItemsError,
	)

	try:
		reconciliation.insert(ignore_permissions=True)
	except EmptyStockReconciliationItemsError:
		frappe.clear_messages()  # already at that quantity and value: nothing to change
		return {"item_code": item_code, "stock": flt(qty)}
	reconciliation.submit()
	return {"item_code": item_code, "stock": flt(qty)}
