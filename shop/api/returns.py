import frappe
from frappe import _
from frappe.utils import cint

from shop.api import only_managers

STATUSES = ("Requested", "Approved", "Rejected", "Completed")


@frappe.whitelist()
def get_requests(status: str | None = None, start: int = 0, limit: int = 20) -> dict:
	only_managers()
	filters = {"status": status} if status in STATUSES else {}
	start, limit = cint(start), min(cint(limit) or 20, 100)
	requests = frappe.get_all(
		"Shop Return Request",
		filters=filters,
		fields=[
			"name",
			"sales_order",
			"customer",
			"item_code",
			"item_name",
			"qty",
			"request_type",
			"status",
			"reason",
			"resolution_note",
			"creation",
		],
		order_by="creation desc",
		start=start,
		limit=limit,
	)
	return {
		"requests": requests,
		"total": frappe.db.count("Shop Return Request", filters),
		"open_count": frappe.db.count("Shop Return Request", {"status": "Requested"}),
		"statuses": list(STATUSES),
	}


@frappe.whitelist()
def for_order(order: str) -> list[dict]:
	only_managers()
	return frappe.get_all(
		"Shop Return Request",
		filters={"sales_order": order},
		fields=["name", "item_name", "qty", "request_type", "status", "reason", "resolution_note", "creation"],
		order_by="creation desc",
	)


@frappe.whitelist(methods=["POST"])
def set_status(name: str, status: str, note: str | None = None) -> dict:
	only_managers()
	if status not in STATUSES:
		frappe.throw(_("Unknown status: {0}").format(status))
	request = frappe.get_doc("Shop Return Request", name)
	request.status = status
	if note is not None:
		request.resolution_note = note
	request.save(ignore_permissions=True)
	return {"name": request.name, "status": request.status, "resolution_note": request.resolution_note}
