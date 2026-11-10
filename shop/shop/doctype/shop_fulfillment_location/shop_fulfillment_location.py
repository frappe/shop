from frappe.model.document import Document


class ShopFulfillmentLocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_pickup: DF.Check
		auto_send: DF.Check
		display_name: DF.Data | None
		fulfillment_provider: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pickup_instructions: DF.SmallText | None
		ship_from_address: DF.Link | None
		show_stock: DF.Check
		warehouse: DF.Link
	# end: auto-generated types

	pass
