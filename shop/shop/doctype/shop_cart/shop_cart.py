import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ShopCart(Document):
	def before_insert(self):
		if not self.token:
			self.token = frappe.generate_hash(length=32)

	def validate(self):
		self.last_active = now_datetime()
