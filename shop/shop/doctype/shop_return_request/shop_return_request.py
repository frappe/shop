import frappe
from frappe.model.document import Document


class ShopReturnRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		credit_note: DF.Link | None
		customer: DF.Link | None
		item_code: DF.Link
		item_name: DF.Data | None
		qty: DF.Float
		reason: DF.SmallText
		refund: DF.Link | None
		request_type: DF.Literal["Return", "Replacement"]
		resolution_note: DF.SmallText | None
		return_delivery_note: DF.Link | None
		sales_order: DF.Link
		status: DF.Literal["Requested", "Approved", "Rejected", "Completed"]
	# end: auto-generated types

	def validate(self):
		if not self.item_name:
			self.item_name = frappe.db.get_value("Item", self.item_code, "item_name")
		if not self.customer:
			self.customer = frappe.db.get_value("Sales Order", self.sales_order, "customer")
