import math

import frappe
from frappe import _
from frappe.utils import cint, flt


def locations() -> list[frappe._dict]:
	"""The store's fulfillment locations, first to last: a warehouse, who sends from it and from
	which address."""
	settings = frappe.get_cached_doc("Shop Settings")
	return [
		frappe._dict(
			warehouse=row.warehouse,
			label=row.get("display_name")
			or frappe.get_cached_value("Warehouse", row.warehouse, "warehouse_name")
			or row.warehouse,
			named=bool(row.get("display_name")),
			show_stock=cint(row.get("show_stock")),
			provider=row.fulfillment_provider or "manual",
			ship_from=row.ship_from_address or warehouse_address(row.warehouse),
			auto_send=cint(row.auto_send),
			allow_pickup=cint(row.get("allow_pickup")),
			pickup_instructions=row.get("pickup_instructions") or "",
		)
		for row in settings.get("fulfillment_locations") or []
		if row.warehouse
	]


def location(warehouse: str | None) -> frappe._dict | None:
	return next((row for row in locations() if row.warehouse == warehouse), None)


def warehouses() -> list[str]:
	return [row.warehouse for row in locations()]


def primary_warehouse() -> str | None:
	"""The store's first warehouse: where stock is received and services are booked."""
	names = warehouses()
	return names[0] if names else None


def warehouse_address(warehouse: str) -> str | None:
	"""The Address linked to a Warehouse in ERPNext, its preferred one first."""
	rows = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Warehouse", "link_name": warehouse, "parenttype": "Address"},
		pluck="parent",
	)
	if not rows:
		return None
	return frappe.db.get_value(
		"Address",
		{"name": ["in", rows], "disabled": 0},
		"name",
		order_by="is_shipping_address desc, is_primary_address desc",
	)


def warehouse_stock(item_codes: list[str], sellable: bool = False) -> dict[str, dict[str, float]]:
	"""Stock of each item (and each Product Bundle) in each of the store's warehouses; sellable
	leaves out what orders not yet delivered wait for. A bundle counts where all its stocked parts
	are."""
	names = warehouses()
	if not item_codes or not names:
		return {code: {} for code in item_codes}
	parts = bundles_parts(item_codes)
	codes = list(dict.fromkeys([*item_codes, *(part for rows in parts.values() for part, _qty in rows)]))
	bins = frappe.get_all(
		"Bin",
		filters={"item_code": ["in", codes], "warehouse": ["in", names]},
		fields=["item_code", "warehouse", "actual_qty", "reserved_qty"],
	)
	qty = {code: dict.fromkeys(names, 0.0) for code in codes}
	for row in bins:
		qty[row.item_code][row.warehouse] = flt(row.actual_qty) - (flt(row.reserved_qty) if sellable else 0)
	for code, bundle in parts.items():
		stocked = [(part, n) for part, n in bundle if frappe.get_cached_value("Item", part, "is_stock_item")]
		if stocked:
			qty[code] = {
				warehouse: min(math.floor(qty[part][warehouse] / n) for part, n in stocked)
				for warehouse in names
			}
	return {code: qty[code] for code in item_codes}


def get_stock(item_codes: list[str], sellable: bool = False) -> dict[str, float]:
	"""Stock across the store's warehouses; sellable leaves out what orders not yet delivered wait
	for. A Product Bundle has as many as its stocked parts make up in each warehouse."""
	by_warehouse = warehouse_stock(item_codes, sellable)
	return {code: sum(max(qty, 0) for qty in by_warehouse[code].values()) for code in item_codes}


def stocked_parts(item_code: str) -> list[tuple[str, float]]:
	"""The stock items a line of this item takes, and how many of each per unit: the item itself,
	or a Product Bundle's stocked parts."""
	parts = bundle_parts(item_code)
	if parts:
		return [(part, n) for part, n in parts if frappe.get_cached_value("Item", part, "is_stock_item")]
	return [(item_code, 1.0)] if frappe.get_cached_value("Item", item_code, "is_stock_item") else []


def demand(lines: list[tuple[str, float]]) -> dict[str, float]:
	"""How many of each stock item the lines take together, bundles counted by their parts."""
	need: dict[str, float] = {}
	for code, qty in lines:
		for part, n in stocked_parts(code):
			need[part] = need.get(part, 0) + n * flt(qty)
	return need


def allocate(lines: list[tuple[str, float]]) -> list[frappe._dict]:
	"""Which warehouse each line is sent from: the first, in the store's order, that has all of it;
	a line no single warehouse has is split across them. A Product Bundle is counted by its parts,
	so a bundle and its own part in one order draw on the same stock. What isn't stocked (a
	service), or isn't in stock where the store sells out-of-stock items, goes to the first
	warehouse."""
	first = primary_warehouse()
	needs = {code: stocked_parts(code) for code, _qty in lines}
	left = warehouse_stock(
		list(dict.fromkeys(part for need in needs.values() for part, _n in need)), sellable=True
	)

	def can_take(need, warehouse) -> float:
		return min(math.floor(round(left[part].get(warehouse, 0) / n, 9)) for part, n in need)

	def take(need, warehouse, qty) -> None:
		for part, n in need:
			left[part][warehouse] = left[part].get(warehouse, 0) - n * qty

	allocated = []
	for code, qty in lines:
		qty, need = flt(qty), needs[code]
		if not need:
			allocated.append(frappe._dict(item_code=code, qty=qty, warehouse=first))
			continue
		whole = next((warehouse for warehouse in warehouses() if can_take(need, warehouse) >= qty), None)
		if whole:
			take(need, whole, qty)
			allocated.append(frappe._dict(item_code=code, qty=qty, warehouse=whole))
			continue
		for warehouse in warehouses():
			part_qty = min(qty, max(can_take(need, warehouse), 0))
			if part_qty > 0:
				take(need, warehouse, part_qty)
				qty -= part_qty
				allocated.append(frappe._dict(item_code=code, qty=part_qty, warehouse=warehouse))
		if qty > 0:
			allocated.append(frappe._dict(item_code=code, qty=qty, warehouse=first))
	return allocated


def bundles_parts(item_codes: list[str]) -> dict[str, list[tuple[str, float]]]:
	"""bundle_parts for many items, in two queries."""
	bundles = dict(
		frappe.get_all(
			"Product Bundle",
			filters={"new_item_code": ["in", item_codes], "disabled": 0},
			fields=["name", "new_item_code"],
			as_list=True,
		)
	)
	parts = {code: [] for code in item_codes}
	for row in frappe.get_all(
		"Product Bundle Item",
		filters={"parent": ["in", list(bundles) or [""]]},
		fields=["parent", "item_code", "qty"],
		order_by="idx",
	):
		parts[bundles[row.parent]].append((row.item_code, flt(row.qty) or 1))
	return parts


def bundle_parts(item_code: str) -> list[tuple[str, float]]:
	"""The items of the item's Product Bundle and how many of each, or none."""
	bundle = frappe.db.get_value("Product Bundle", {"new_item_code": item_code, "disabled": 0})
	if not bundle:
		return []
	return [
		(row.item_code, flt(row.qty) or 1)
		for row in frappe.get_all(
			"Product Bundle Item", filters={"parent": bundle}, fields=["item_code", "qty"]
		)
	]


def is_stock_item(item_code: str) -> bool:
	"""Kept in stock: the item, or for a Product Bundle any of its parts."""
	if frappe.get_cached_value("Item", item_code, "is_stock_item"):
		return True
	return any(frappe.get_cached_value("Item", part, "is_stock_item") for part, _qty in bundle_parts(item_code))


def available_qty(item_code: str) -> float | None:
	"""How many the store can sell: None when it isn't limited (a service, or the store sells
	out-of-stock items)."""
	if frappe.get_cached_doc("Shop Settings").allow_out_of_stock or not is_stock_item(item_code):
		return None
	return get_stock([item_code], sellable=True).get(item_code, 0)


def availability(item_code: str, priced: bool = True) -> dict:
	"""Whether the item can be bought online, and what the product page says about it (with its
	stock at each location the store shows, and where it can be sent)."""
	from shop.storefront.shipping import shipping_restriction

	if not priced:
		return state(False, "unavailable", _("Not available online"))
	result = qty_state(available_qty(item_code), item_code)
	restriction = shipping_restriction(item_code)
	if restriction:
		result["shipping_note"] = frappe.utils.escape_html(restriction.note())
	shown = location_stock(item_code)
	if shown:
		result["stock_locations"] = shown
		items = "".join(
			f'<li data-stock-state="{row["stock_state"]}"><span>{frappe.utils.escape_html(row["label"])}</span>'
			f' <span>{frappe.utils.escape_html(row["stock_status"])}</span></li>'
			for row in shown
		)
		result["stock_locations_html"] = f'<ul class="stock-locations">{items}</ul>'
	return result


def qty_state(qty: float | None, item_code: str) -> dict:
	"""What a quantity on hand says: in stock, only a few left, or out of stock."""
	if qty is None:
		return state(True, "in", _("In stock") if is_stock_item(item_code) else _("Available"))
	if qty <= 0:
		return state(False, "out", _("Out of stock"))
	threshold = cint(frappe.get_cached_doc("Shop Settings").get("low_stock_threshold"))
	if threshold and qty <= threshold:
		return state(True, "low", _("Only {0} left").format(cint(qty)))
	return state(True, "in", _("In stock"))


def location_stock(item_code: str) -> list[dict]:
	"""The item's stock at each location the store shows customers, as ERPNext has it in each
	warehouse."""
	shown = [row for row in locations() if row.show_stock]
	if not shown or not is_stock_item(item_code):
		return []
	by_warehouse = warehouse_stock([item_code], sellable=True)[item_code]
	rows = []
	for row in shown:
		qty_said = qty_state(max(by_warehouse.get(row.warehouse, 0), 0), item_code)
		rows.append(
			{"label": row.label, "stock_state": qty_said["stock_state"], "stock_status": qty_said["stock_status"]}
		)
	return rows


def state(purchasable: bool, stock_state: str, stock_status: str) -> dict:
	return {"purchasable": purchasable, "stock_state": stock_state, "stock_status": stock_status}


def is_in_stock(item_code: str) -> bool:
	settings = frappe.get_cached_doc("Shop Settings")
	if settings.allow_out_of_stock:
		return True
	if not is_stock_item(item_code):
		return True
	return get_stock([item_code], sellable=True).get(item_code, 0) > 0
