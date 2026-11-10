from frappe.model.document import Document


class ShopStockAlert(Document):
	"""A shopper's ask to be emailed when an out-of-stock item can be bought again."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		email: DF.Data
		item_code: DF.Link
		product: DF.Link | None
		sent_on: DF.Datetime | None
	# end: auto-generated types

	pass
