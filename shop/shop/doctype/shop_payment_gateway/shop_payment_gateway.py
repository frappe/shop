from frappe.model.document import Document


class ShopPaymentGateway(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		fee_fixed: DF.Float
		fee_fixed_international: DF.Float
		fee_label: DF.Data | None
		fee_percent: DF.Percent
		fee_percent_international: DF.Percent
		label: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_gateway: DF.Link
	# end: auto-generated types

	pass
