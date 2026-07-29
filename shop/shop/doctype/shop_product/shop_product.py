import frappe
from frappe import _
from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name


class ShopProduct(Document):
	def before_insert(self):
		if not self.product_name:
			self.product_name = frappe.db.get_value("Item", self.item, "item_name")
		if not self.slug:
			self.slug = cleanup_page_name(self.product_name)

	def validate(self):
		if frappe.db.get_value("Item", self.item, "variant_of"):
			frappe.throw(_("Publish the template item instead of an individual variant"))
