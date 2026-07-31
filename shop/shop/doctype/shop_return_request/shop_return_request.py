import frappe
from frappe.model.document import Document


class ShopReturnRequest(Document):
	def validate(self):
		if not self.item_name:
			self.item_name = frappe.db.get_value("Item", self.item_code, "item_name")
		if not self.customer:
			self.customer = frappe.db.get_value("Sales Order", self.sales_order, "customer")
