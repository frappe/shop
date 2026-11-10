import json

import frappe
from frappe import _
from frappe.utils import flt, fmt_money

from shop.fulfillment.provider import get_provider

OPEN_STATUSES = ("Pending", "Accepted", "Shipped")


def parcels(order) -> dict[str | None, list[dict]]:
	"""The order's goods by the warehouse they are sent from: one parcel per warehouse."""
	from shop.storefront.totals import is_charge_item

	grouped: dict[str | None, list[dict]] = {}
	for row in order.items:
		if is_charge_item(row.item_code):
			continue
		grouped.setdefault(row.warehouse or None, []).append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": flt(row.qty),
				"warehouse": row.warehouse or None,
			}
		)
	return grouped


def parcel_provider(warehouse: str | None) -> str:
	"""Who sends from a warehouse: its location's provider. A warehouse that isn't one of the
	store's locations (an order made in Desk, a location since removed) is sent by hand."""
	from shop.storefront.stock import location, locations

	row = location(warehouse) if warehouse else next(iter(locations()), None)
	return row.provider if row else "manual"


def chosen_option(order, warehouse: str | None) -> dict | None:
	"""The shipping service the customer chose for the parcel from this warehouse."""
	raw = order.get("shop_shipping_option")
	if not raw:
		return None
	try:
		chosen = json.loads(raw)
	except ValueError:
		return None
	if isinstance(chosen, dict):
		# an order placed before parcels: one choice for everything
		return chosen
	return next((option for option in chosen if option.get("warehouse") == warehouse), None)


def send(order_name: str, provider_key: str | None = None, warehouse: str | None = None) -> str:
	"""Hand a parcel of an order to a fulfillment provider: the one from this warehouse, or the
	order's first parcel not sent yet. Returns the fulfillment name."""
	order = frappe.get_doc("Sales Order", order_name)
	if order.docstatus != 1:
		frappe.throw(_("Only submitted orders can be sent for fulfillment"))
	groups = parcels(order)
	if warehouse is None:
		waiting = [name for name in groups if not open_fulfillment(order_name, name)]
		if not waiting:
			frappe.throw(_("This order is already with a fulfillment provider"))
		warehouse = waiting[0]
	elif warehouse not in groups:
		frappe.throw(_("Nothing in this order is sent from {0}").format(warehouse))
	if open_fulfillment(order_name, warehouse):
		frappe.throw(_("This parcel is already with a fulfillment provider"))
	option = chosen_option(order, warehouse)
	# a parcel the customer collects goes to no carrier
	key = provider_key or ("pickup" if is_pickup(option) else parcel_provider(warehouse))
	provider = get_provider(key)
	if not provider.is_configured():
		frappe.throw(_("{0} is not set up yet. {1}").format(provider.label, provider.setup_hint()))
	from shop.storefront.stock import location, warehouse_address

	place = location(warehouse)
	items = groups[warehouse]
	record = {
		"doctype": "Shop Fulfillment",
		"sales_order": order_name,
		"provider": key,
		"warehouse": warehouse,
		"ship_from_address": (place.ship_from if place else None)
		or (warehouse_address(warehouse) if warehouse else None),
		"shipping_option": json.dumps(option, default=str) if option else None,
		"items": [{field: row[field] for field in ("item_code", "item_name", "qty")} for row in items],
	}
	frappe.db.savepoint("shop_send")
	fulfillment = frappe.get_doc({**record, "status": "Pending"}).insert(ignore_permissions=True)
	try:
		apply_result(fulfillment, create_shipment(provider, order, items, fulfillment))
	except Exception as error:
		# what the provider made before failing (a Delivery Note, say) is undone; the failure is kept,
		# also when the request that sent it is rolled back
		frappe.db.rollback(save_point="shop_send")
		failed = {**record, "status": "Failed", "error": str(error)[:500]}
		name = frappe.get_doc(failed).insert(ignore_permissions=True).name
		frappe.db.after_rollback.add(lambda: keep_failure(name, failed))
		raise
	return fulfillment.name


def keep_failure(name: str, record: dict) -> None:
	"""The failed hand-over again after its request was rolled back, while the order is there."""
	if frappe.db.exists("Shop Fulfillment", name) or not frappe.db.exists(
		"Sales Order", record.get("sales_order")
	):
		return
	frappe.get_doc(record).insert(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: the failed request's own transaction was rolled back


def is_pickup(option: dict | None) -> bool:
	return bool(option) and str(option.get("id") or "").startswith("pickup:")


def create_shipment(provider, order, items: list[dict], fulfillment) -> dict:
	"""A provider that takes the fulfillment gets it (its warehouse, address and the customer's
	choice); an older one gets the order and items only."""
	import inspect

	if "fulfillment" in inspect.signature(provider.create_shipment).parameters:
		return provider.create_shipment(order, items, fulfillment=fulfillment)
	return provider.create_shipment(order, items)


def open_fulfillment(order_name: str, warehouse: str | None) -> str | None:
	"""The parcel's fulfillment still in hand, if any. One recorded without a warehouse (before
	parcels) stands for the whole order."""
	filters = {"sales_order": order_name, "status": ["in", OPEN_STATUSES]}
	whole = frappe.db.get_value("Shop Fulfillment", {**filters, "warehouse": ["is", "not set"]})
	return whole or frappe.db.get_value("Shop Fulfillment", {**filters, "warehouse": warehouse})


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
	before = fulfillment.status
	if result.get("status"):
		fulfillment.apply_status(result["status"])
	fulfillment.save(ignore_permissions=True)
	sent = ("Shipped", "Delivered")
	became_shipped = fulfillment.status in sent and before not in sent
	became_delivered = fulfillment.status == "Delivered" and before != "Delivered"
	# a collected parcel leaves the store when the customer takes it, not when it is made ready
	if became_delivered if fulfillment.provider == "pickup" else became_shipped:
		record_delivery(fulfillment)
	if became_delivered:
		notify_customer(fulfillment, "Delivered")
	elif became_shipped:
		notify_customer(fulfillment, "Shipped")


def notify_customer(fulfillment, status: str) -> None:
	"""Tell the customer their order has shipped (with tracking) or been delivered."""
	if not frappe.get_cached_doc("Shop Settings").get("send_shipping_emails"):
		return
	email, docstatus = frappe.db.get_value(
		"Sales Order", fulfillment.sales_order, ["contact_email", "docstatus"]
	) or (None, None)
	if not email or docstatus != 1:
		return
	from shop.routes import store_url
	from shop.storefront import emails
	from shop.storefront.orders import access_token, order_url

	order = frappe.get_doc("Sales Order", fulfillment.sales_order)
	# an order entered in Desk has no link a guest can open: the email links to their account
	link = frappe.utils.get_url(
		order_url(order.name) if access_token(order.name) else store_url("account/orders")
	)
	if fulfillment.provider == "pickup":
		if status == "Shipped":
			from shop.storefront.stock import location

			place = location(fulfillment.get("warehouse"))
			emails.send(
				"ready_for_pickup", order.contact_email, order, order_url=link,
				location=place.label if place else "", instructions=place.pickup_instructions if place else "",
			)
		return
	if status == "Shipped":
		from shop.storefront.orders import shipment_summary

		shipment = shipment_summary(order.name)
		emails.send(
			"order_shipped", order.contact_email, order, order_url=link, tracking_url=fulfillment.tracking_url,
			carrier_line=" · ".join(filter(None, [fulfillment.carrier, fulfillment.tracking_number])),
			partly=bool(shipment and shipment.partly_shipped),
		)
	else:
		emails.send("order_delivered", order.contact_email, order, order_url=link)


def record_delivery(fulfillment) -> None:
	"""File the parcel's delivery in ERPNext so stock and the order status stay honest."""
	order = frappe.db.get_value(
		"Sales Order", fulfillment.sales_order, ["docstatus", "per_delivered"], as_dict=True
	)
	if not order or order.docstatus != 1 or flt(order.per_delivered) >= 100:
		return
	# a Delivery Note that fails half way isn't left behind as a draft
	frappe.db.savepoint("shop_record_delivery")
	try:
		deliver_parcel(fulfillment)
	except Exception:
		frappe.db.rollback(save_point="shop_record_delivery")
		frappe.log_error(
			title="Fulfillment delivery note failed",
			reference_doctype="Sales Order",
			reference_name=fulfillment.sales_order,
		)


def deliver_parcel(fulfillment) -> str | None:
	"""A Delivery Note for what the order still has to deliver from the parcel's warehouse (all of
	it, for a fulfillment recorded before parcels)."""
	from shop.compat import make_delivery_note

	note = make_delivery_note(fulfillment.sales_order)
	if fulfillment.get("warehouse"):
		note.items = [row for row in note.items if row.warehouse == fulfillment.warehouse]
	if not note.items:
		return None
	note.flags.ignore_permissions = True
	note.insert(ignore_permissions=True)
	note.submit()
	return note.name


def auto_send(order_name: str) -> None:
	"""Hand a paid order over without waiting to be asked, from the locations that want that: once
	the payment is saved, so a provider never gets an order whose payment was rolled back."""
	from shop.storefront.stock import locations

	if not any(row.auto_send for row in locations()):
		return
	frappe.enqueue(
		"shop.fulfillment.service.send_paid_order",
		order_name=order_name,
		job_id=f"shop-send-{order_name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def send_paid_order(order_name: str) -> None:
	from shop.storefront.stock import location, locations

	order = frappe.db.get_value("Sales Order", order_name, ["docstatus", "status", "per_delivered"], as_dict=True)
	if not order or order.docstatus != 1 or order.status in ("Closed", "Completed") or flt(order.per_delivered):
		return
	first = next(iter(locations()), None)
	for warehouse in parcels(frappe.get_doc("Sales Order", order_name)):
		# only a store location sends automatically; an order without warehouses is the first's
		place = location(warehouse) if warehouse else first
		if not place or not place.auto_send:
			continue
		# only the first hand-over of a parcel is automatic: one sent before (even if that was
		# cancelled) is left to staff
		if frappe.db.exists(
			"Shop Fulfillment", {"sales_order": order_name, "status": ["!=", "Failed"], "warehouse": warehouse}
		) or frappe.db.exists(
			"Shop Fulfillment",
			{"sales_order": order_name, "status": ["!=", "Failed"], "warehouse": ["is", "not set"]},
		):
			continue
		try:
			send(order_name, warehouse=warehouse)
		except Exception:
			frappe.log_error(
				title="Automatic fulfillment failed", reference_doctype="Sales Order", reference_name=order_name
			)


def summary(fulfillment) -> dict:
	if isinstance(fulfillment, str):
		fulfillment = frappe.get_doc("Shop Fulfillment", fulfillment)
	return {
		"name": fulfillment.name,
		"sales_order": fulfillment.sales_order,
		"provider": fulfillment.provider,
		"provider_label": provider_label(fulfillment.provider),
		"warehouse": fulfillment.get("warehouse"),
		"shipping_option": json.loads(fulfillment.shipping_option) if fulfillment.get("shipping_option") else None,
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
		"courier": courier(fulfillment),
	}


def courier(fulfillment) -> dict | None:
	"""Where the parcel's courier booking and label stand, when its provider books couriers."""
	from shop.fulfillment.provider import registry

	if fulfillment.provider not in registry() or fulfillment.status in ("Cancelled", "Failed"):
		return None
	provider = get_provider(fulfillment.provider)
	state = provider.courier(fulfillment) if hasattr(provider, "courier") else None
	if state and state.get("amount") is not None:
		state["formatted_amount"] = fmt_money(state["amount"], currency=state.get("currency"))
	return state


def provider_label(key: str) -> str:
	from shop.fulfillment.provider import registry

	if key not in registry():
		return key
	return get_provider(key).label or key


def for_order(order_name: str) -> dict | None:
	"""The order's latest fulfillment."""
	name = frappe.db.get_value(
		"Shop Fulfillment", {"sales_order": order_name}, "name", order_by="creation desc"
	)
	return summary(name) if name else None


def order_parcels(order_name: str) -> list[dict]:
	"""Each parcel of the order: its warehouse, who sends it, its goods and its latest fulfillment."""
	from shop.storefront.stock import location

	order = frappe.get_doc("Sales Order", order_name)
	result = []
	for warehouse, items in parcels(order).items():
		names = frappe.get_all(
			"Shop Fulfillment",
			filters={"sales_order": order_name, "warehouse": warehouse or ["is", "not set"]},
			pluck="name",
			order_by="creation desc",
		)
		if not names and len(parcels(order)) == 1:
			# recorded before parcels, without a warehouse
			names = frappe.get_all(
				"Shop Fulfillment", filters={"sales_order": order_name}, pluck="name", order_by="creation desc"
			)
		result.append(
			{
				"warehouse": warehouse,
				"warehouse_label": frappe.db.get_value("Warehouse", warehouse, "warehouse_name") if warehouse else None,
				"provider": parcel_provider(warehouse),
				"provider_label": provider_label(parcel_provider(warehouse)),
				"located": bool(location(warehouse)),
				"items": items,
				"fulfillment": summary(names[0]) if names else None,
				"history": [summary(name) for name in names[1:]],
			}
		)
	return result


def sync_open_shipments() -> None:
	"""Scheduled: keep in-flight shipments up to date with their provider."""
	for name in frappe.get_all(
		"Shop Fulfillment", filters={"status": ["in", ("Pending", "Accepted", "Shipped")]}, pluck="name"
	):
		try:
			sync(name)
		except Exception:
			frappe.log_error(title="Fulfillment sync failed")
