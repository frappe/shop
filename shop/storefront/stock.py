import frappe


def get_stock(item_codes: list[str]) -> dict[str, float]:
	if not item_codes:
		return {}
	settings = frappe.get_cached_doc("Shop Settings")
	rows = frappe.get_all(
		"Bin",
		filters={"item_code": ["in", item_codes], "warehouse": settings.default_warehouse},
		fields=["item_code", "actual_qty"],
	)
	qty_map = dict.fromkeys(item_codes, 0.0)
	qty_map.update({row.item_code: row.actual_qty for row in rows})
	return qty_map


def is_in_stock(item_code: str) -> bool:
	settings = frappe.get_cached_doc("Shop Settings")
	if settings.allow_out_of_stock:
		return True
	if not frappe.get_cached_value("Item", item_code, "is_stock_item"):
		return True
	return get_stock([item_code]).get(item_code, 0) > 0
