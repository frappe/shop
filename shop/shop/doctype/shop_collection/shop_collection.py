from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name


class ShopCollection(Document):
	def before_insert(self):
		if not self.slug:
			self.slug = cleanup_page_name(self.title)
