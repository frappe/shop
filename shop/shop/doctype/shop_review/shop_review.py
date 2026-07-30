import frappe
from frappe import _
from frappe.model.document import Document


class ShopReview(Document):
	def validate(self):
		if not 1 <= self.rating <= 5:
			frappe.throw(_("Rating must be between 1 and 5"))
