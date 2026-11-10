import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ShopCart(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from shop.shop.doctype.shop_cart_item.shop_cart_item import ShopCartItem

		coupon_code: DF.Link | None
		items: DF.Table[ShopCartItem]
		email: DF.Data | None
		last_active: DF.Datetime | None
		reminded: DF.Check
		sales_order: DF.Link | None
		shipping_quotes: DF.Code | None
		shipping_rate: DF.Data | None
		status: DF.Literal["Active", "Converted", "Abandoned"]
		token: DF.Data | None
		user: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		if not self.token:
			self.token = frappe.generate_hash(length=32)

	def validate(self):
		self.last_active = now_datetime()
