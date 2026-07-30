import json

import frappe
from frappe import _
from frappe.utils import flt

from shop.fulfillment.provider import get_provider

OPEN_STATUSES = ("Pending", "Accepted", "Shipped")


def send(order_name: str, provider_key: str | None = None) -> str:
	"""Hand an order to a fulfillment provider. Returns the fulfillment name."""
	order = frappe.get_doc("Sales Order", order_name)
	if order.docstatus != 1:
		frappe.throw(_("Only submitted orders can be sent for fulfillment"))
	existing = frappe.db.exists(
		"Shop Fulfillment", {"sales_order": order_name, "status": ["in", OPEN_STATUSES]}
	)
	if existing:
		frappe.throw(_("This order is already with a fulfillment provider"))
	key = provider_key or configured_provider()
	provider = get_provider(key)
	if not provider.is_configured():
		frappe.throw(_("{0} is not set up yet. {1}").format(provider.label, provider.setup_hint()))
	items = [{"item_code": row.item_code, "item_name": row.item_name, "qty": flt(row.qty)} for row in order.items]
	fulfillment = frappe.get_doc(
		{
			"doctype": "Shop Fulfillment",
			"sales_order": order_name,
			"provider": key,
			"status": "Pending",
			"items": items,
		}
	)
	fulfillment.insert(ignore_permissions=True)
	try:
		apply_result(fulfillment, provider.create_shipment(order, items))
	except Exception as error:
		fulfillment.status = "Failed"
		fulfillment.error = str(error)[:500]
		fulfillment.save(ignore_permissions=True)
		raise
	return fulfillment.name


def sync(fulfillment_name: str) -> dict:
	"""Ask the provider where the shipment is, and record any movement."""
	fulfillment = frappe.get_doc("Shop Fulfillment", fulfillment_name)
	provider = get_provider(fulfillment.provider)
	apply_result(fulfillment, provider.fetch_status(fulfillment))
	return summary(fulfillment)


def cancel(fulfillment_name: str) -> dict:
	fulfillment = frappe.get_doc("Shop Fulfillment", fulfillment_name)
	provider = get_provider(fulfillment.provider)
	apply_result(fulfillment, provider.cancel(fulfillment))
	return summary(fulfillment)


def apply_result(fulfillment, result: dict) -> None:
	"""Record a provider response, then mirror a shipment into ERPNext once."""
	for field in ("external_id", "carrier", "tracking_number", "tracking_url"):
		if result.get(field):
			fulfillment.set(field, result[field])
	if result.get("raw") is not None:
		fulfillment.last_response = json.dumps(result["raw"], indent=1, default=str)[:100000]
	status = result.get("status")
	became_shipped = status in ("Shipped", "Delivered") and fulfillment.status not in ("Shipped", "Delivered")
	if status:
		fulfillment.apply_status(status)
	fulfillment.save(ignore_permissions=True)
	if became_shipped:
		record_delivery(fulfillment)


def record_delivery(fulfillment) -> None:
	"""File the delivery in ERPNext so stock and the order status stay honest."""
	from shop.api.orders import fulfill

	order = frappe.db.get_value(
		"Sales Order", fulfillment.sales_order, ["docstatus", "per_delivered"], as_dict=True
	)
	if not order or order.docstatus != 1 or flt(order.per_delivered) >= 100:
		return
	try:
		fulfill(fulfillment.sales_order)
	except Exception:
		frappe.log_error(title="Fulfillment delivery note failed")


def auto_send(order_name: str) -> None:
	"""Hand a paid order over without waiting to be asked, when the store wants that."""
	settings = frappe.get_cached_doc("Shop Settings")
	if not settings.get("auto_send_to_fulfillment"):
		return
	if frappe.db.exists("Shop Fulfillment", {"sales_order": order_name, "status": ["in", OPEN_STATUSES]}):
		return
	try:
		send(order_name)
	except Exception:
		frappe.log_error(title="Automatic fulfillment failed")


def configured_provider() -> str:
	settings = frappe.get_cached_doc("Shop Settings")
	return settings.get("fulfillment_provider") or "manual"


def summary(fulfillment) -> dict:
	if isinstance(fulfillment, str):
		fulfillment = frappe.get_doc("Shop Fulfillment", fulfillment)
	return {
		"name": fulfillment.name,
		"sales_order": fulfillment.sales_order,
		"provider": fulfillment.provider,
		"provider_label": provider_label(fulfillment.provider),
		"status": fulfillment.status,
		"external_id": fulfillment.external_id,
		"carrier": fulfillment.carrier,
		"tracking_number": fulfillment.tracking_number,
		"tracking_url": fulfillment.tracking_url,
		"requested_on": str(fulfillment.requested_on)[:16] if fulfillment.requested_on else None,
		"shipped_on": str(fulfillment.shipped_on)[:16] if fulfillment.shipped_on else None,
		"delivered_on": str(fulfillment.delivered_on)[:16] if fulfillment.delivered_on else None,
		"error": fulfillment.error,
		"items": [{"item_code": row.item_code, "item_name": row.item_name, "qty": row.qty} for row in fulfillment.items],
	}


def provider_label(key: str) -> str:
	from shop.fulfillment.provider import registry

	if key not in registry():
		return key
	return get_provider(key).label or key


def for_order(order_name: str) -> dict | None:
	name = frappe.db.get_value(
		"Shop Fulfillment", {"sales_order": order_name}, "name", order_by="creation desc"
	)
	return summary(name) if name else None


def sync_open_shipments() -> None:
	"""Scheduled: keep in-flight shipments up to date with their provider."""
	for name in frappe.get_all(
		"Shop Fulfillment", filters={"status": ["in", ("Pending", "Accepted", "Shipped")]}, pluck="name"
	):
		try:
			sync(name)
		except Exception:
			frappe.log_error(title="Fulfillment sync failed")
