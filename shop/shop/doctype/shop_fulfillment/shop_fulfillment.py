import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

STAMPS = {
	"Shipped": "shipped_on",
	"Delivered": "delivered_on",
	"Cancelled": "cancelled_on",
}


class ShopFulfillment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from shop.shop.doctype.shop_fulfillment_item.shop_fulfillment_item import ShopFulfillmentItem

		cancelled_on: DF.Datetime | None
		carrier: DF.Data | None
		delivered_on: DF.Datetime | None
		error: DF.SmallText | None
		external_id: DF.Data | None
		items: DF.Table[ShopFulfillmentItem]
		last_response: DF.Code | None
		provider: DF.Data
		requested_on: DF.Datetime | None
		sales_order: DF.Link
		ship_from_address: DF.Link | None
		shipped_on: DF.Datetime | None
		shipping_option: DF.Code | None
		status: DF.Literal["Pending", "Accepted", "Shipped", "Delivered", "Cancelled", "Failed"]
		tracking_number: DF.Data | None
		tracking_url: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		self.requested_on = now_datetime()

	def apply_status(self, status: str) -> None:
		"""Record a provider status and stamp the moment it first happened. A parcel that has shipped
		doesn't go back to being prepared when a late or repeated update arrives."""
		if status == self.status or self.status == "Cancelled":
			return
		if self.status in ("Shipped", "Delivered") and status in ("Pending", "Accepted"):
			return
		if self.status == "Delivered" and status == "Shipped":
			return
		self.status = status
		field = STAMPS.get(status)
		if field and not self.get(field):
			self.set(field, now_datetime())
