from frappe.model.document import Document


class ShopImportDuty(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		country: DF.Link
		duty_free_up_to: DF.Float
		duty_rate: DF.Percent
		fee_on_duty: DF.Percent
		fee_per_parcel: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
