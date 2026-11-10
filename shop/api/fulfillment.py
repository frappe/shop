from urllib.parse import urlencode

"""The Shop admin's fulfilment actions. Each checks the user is staff, then runs the provider
elevated: providers call ERPNext code (Delivery Notes, returns, Shipments) that needs permissions
the Shop Manager role doesn't have in Desk, as when an order is sent once it is paid."""

import frappe
from frappe import _
from frappe.utils import cint, fmt_money

from shop.api import only_managers
from shop.fulfillment import service
from shop.fulfillment.provider import available, get_provider
from shop.storefront.checkout import elevated


@frappe.whitelist()
def get_providers() -> list[dict]:
	only_managers()
	return available()


@frappe.whitelist()
def get_fulfillment(order: str) -> dict | None:
	only_managers()
	return service.for_order(order)


@frappe.whitelist()
def get_parcels(order: str) -> list[dict]:
	"""Each parcel of an order (one per warehouse it is sent from) and its fulfillment."""
	only_managers()
	return service.order_parcels(order)


@frappe.whitelist(methods=["POST"])
def send_order(order: str, provider: str | None = None, warehouse: str | None = None) -> dict:
	only_managers()
	with elevated():
		name = service.send(order, provider, warehouse or None)
	return service.summary(name)


@frappe.whitelist(methods=["POST"])
def sync_fulfillment(fulfillment: str) -> dict:
	only_managers()
	with elevated():
		return service.sync(fulfillment)


@frappe.whitelist(methods=["POST"])
def cancel_fulfillment(fulfillment: str) -> dict:
	only_managers()
	with elevated():
		return service.cancel(fulfillment)


def open_fulfillment(name: str):
	"""A fulfillment that can still move on: not cancelled or failed, on an order not cancelled."""
	doc = frappe.get_doc("Shop Fulfillment", name)
	if (
		doc.status not in service.OPEN_STATUSES
		or frappe.db.get_value("Sales Order", doc.sales_order, "docstatus") != 1
	):
		frappe.throw(_("This fulfillment is {0} and can't be updated").format(_(doc.status).lower()))
	return doc


@frappe.whitelist()
def get_carriers() -> list[str]:
	"""Carriers the store has shipped with, to pick from when recording a shipment."""
	only_managers()
	from shop.api.settings import delivery_names

	return delivery_names(("carrier",))


@frappe.whitelist(methods=["POST"])
def mark_shipped(fulfillment: str, carrier: str | None = None, tracking_number: str | None = None) -> dict:
	"""Record a shipment you packed yourself, with optional tracking."""
	only_managers()
	doc = open_fulfillment(fulfillment)
	provider = get_provider(doc.provider)
	if not hasattr(provider, "mark_shipped"):
		frappe.throw(_("{0} reports shipping automatically").format(provider.label))
	with elevated():
		service.apply_result(doc, provider.mark_shipped(doc, carrier, tracking_number))
	return service.summary(doc)


@frappe.whitelist(methods=["POST"])
def mark_delivered(fulfillment: str) -> dict:
	"""Record that a parcel you send yourself arrived, or that the customer collected it."""
	only_managers()
	doc = open_fulfillment(fulfillment)
	provider = get_provider(doc.provider)
	if not hasattr(provider, "mark_delivered"):
		frappe.throw(_("{0} reports delivery automatically").format(provider.label))
	with elevated():
		service.apply_result(doc, provider.mark_delivered(doc))
	return service.summary(doc)


def courier_provider(doc):
	"""The parcel's provider, when it books couriers."""
	provider = get_provider(doc.provider)
	if not (hasattr(provider, "courier") and provider.courier(doc)):
		frappe.throw(_("{0} doesn't book couriers from the store").format(provider.label))
	return provider


def lock(doc) -> None:
	"""Two clicks at once can't book or buy twice: the second waits for the first."""
	frappe.db.get_value("Shop Fulfillment", doc.name, "name", for_update=True)
	doc.reload()
	if doc.status not in service.OPEN_STATUSES:
		frappe.throw(_("This fulfillment is {0} and can't be updated").format(_(doc.status).lower()))


def keep(doc) -> None:
	"""What the courier was paid for is kept whatever happens next; the provider may have updated
	the fulfillment meanwhile."""
	frappe.db.commit()
	doc.reload()


@frappe.whitelist()
def get_courier_services(fulfillment: str) -> list[dict]:
	"""The courier services a parcel can be booked with, and their prices."""
	only_managers()
	doc = open_fulfillment(fulfillment)
	with elevated():
		services = courier_provider(doc).courier_services(doc)
	for row in services:
		row["formatted_amount"] = fmt_money(row.get("amount"), currency=row.get("currency"))
	return services


@frappe.whitelist(methods=["POST"])
def book_courier(fulfillment: str, service_id: str) -> dict:
	"""Book the parcel with a courier service, which the courier charges for."""
	only_managers()
	doc = open_fulfillment(fulfillment)
	lock(doc)
	with elevated():
		result = courier_provider(doc).book_courier(doc, service_id)
	keep(doc)
	service.apply_result(doc, result)
	return service.summary(doc)


@frappe.whitelist(methods=["POST"])
def print_label(fulfillment: str) -> dict:
	"""The parcel's label, bought from the courier the first time, and where to open it."""
	only_managers()
	doc = frappe.get_doc("Shop Fulfillment", fulfillment)
	if doc.status in ("Cancelled", "Failed"):
		frappe.throw(_("This fulfillment is {0} and has no label").format(_(doc.status).lower()))
	lock(doc)
	with elevated():
		result = courier_provider(doc).print_label(doc)
	keep(doc)
	files = result.pop("files", None) or []
	service.apply_result(doc, result)
	return {"fulfillment": service.summary(doc), "labels": label_urls(doc.name, len(files))}


def label_urls(fulfillment: str, count: int) -> list[str]:
	return [
		"/api/method/shop.api.fulfillment.label?" + urlencode({"fulfillment": fulfillment, "index": index})
		for index in range(count)
	]


@frappe.whitelist()
def label(fulfillment: str, index: int = 0) -> None:
	"""A label printed for the parcel, as a PDF to print from the browser."""
	only_managers()
	doc = frappe.get_doc("Shop Fulfillment", fulfillment)
	files = courier_provider(doc).labels(doc)
	if not 0 <= cint(index) < len(files):
		raise frappe.DoesNotExistError(_("This parcel has no such label"))
	name = frappe.get_all("File", filters={"file_url": files[cint(index)]}, pluck="name", limit=1)
	if not name:
		raise frappe.DoesNotExistError(_("This parcel has no such label"))
	file = frappe.get_doc("File", name[0])
	# the label's bytes as they are (no encodings: get_content decodes text it can)
	frappe.local.response.update(
		filename=file.file_name, filecontent=file.get_content(encodings=[]), type="pdf"
	)


@frappe.whitelist()
def list_fulfillments(status: str | None = None, start: int = 0, limit: int = 20) -> dict:
	only_managers()
	filters = {"status": status} if status else {}
	names = frappe.get_all(
		"Shop Fulfillment",
		filters=filters,
		pluck="name",
		order_by="creation desc",
		start=frappe.utils.cint(start),
		limit=min(frappe.utils.cint(limit) or 20, 100),
	)
	return {
		"fulfillments": [service.summary(name) for name in names],
		"total": frappe.db.count("Shop Fulfillment", filters=filters),
	}
