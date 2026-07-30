import frappe
from frappe import _

from shop.api import only_managers
from shop.fulfillment import service
from shop.fulfillment.provider import available, get_provider


@frappe.whitelist()
def get_providers() -> list[dict]:
	only_managers()
	return available()


@frappe.whitelist()
def get_fulfillment(order: str) -> dict | None:
	only_managers()
	return service.for_order(order)


@frappe.whitelist(methods=["POST"])
def send_order(order: str, provider: str | None = None) -> dict:
	only_managers()
	return service.summary(service.send(order, provider))


@frappe.whitelist(methods=["POST"])
def sync_fulfillment(fulfillment: str) -> dict:
	only_managers()
	return service.sync(fulfillment)


@frappe.whitelist(methods=["POST"])
def cancel_fulfillment(fulfillment: str) -> dict:
	only_managers()
	return service.cancel(fulfillment)


@frappe.whitelist(methods=["POST"])
def mark_shipped(fulfillment: str, carrier: str | None = None, tracking_number: str | None = None) -> dict:
	"""Record a shipment you packed yourself, with optional tracking."""
	only_managers()
	doc = frappe.get_doc("Shop Fulfillment", fulfillment)
	provider = get_provider(doc.provider)
	if not hasattr(provider, "mark_shipped"):
		frappe.throw(_("{0} reports shipping automatically").format(provider.label))
	service.apply_result(doc, provider.mark_shipped(doc, carrier, tracking_number))
	return service.summary(doc)


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
