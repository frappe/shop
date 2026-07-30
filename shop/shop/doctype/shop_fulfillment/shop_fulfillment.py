import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

STAMPS = {
	"Shipped": "shipped_on",
	"Delivered": "delivered_on",
	"Cancelled": "cancelled_on",
}


class ShopFulfillment(Document):
	def before_insert(self):
		self.requested_on = now_datetime()

	def apply_status(self, status: str) -> None:
		"""Record a provider status and stamp the moment it first happened."""
		if status == self.status:
			return
		self.status = status
		field = STAMPS.get(status)
		if field and not self.get(field):
			self.set(field, now_datetime())
