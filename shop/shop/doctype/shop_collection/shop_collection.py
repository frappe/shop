import frappe
from frappe import _
from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name


class ShopCollection(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		image: DF.AttachImage | None
		parent_collection: DF.Link | None
		published: DF.Check
		ranking: DF.Int
		slug: DF.Data | None
		title: DF.Data
	# end: auto-generated types

	def before_insert(self):
		if not self.slug:
			self.slug = cleanup_page_name(self.title)

	def validate(self):
		self.validate_parent()

	def validate_parent(self):
		"""A collection can't end up inside itself."""
		parent, seen = self.parent_collection, {self.name}
		while parent:
			if parent in seen:
				frappe.throw(_("{0} can't be inside {1}").format(self.title, self.parent_collection))
			seen.add(parent)
			parent = frappe.db.get_value("Shop Collection", parent, "parent_collection")
