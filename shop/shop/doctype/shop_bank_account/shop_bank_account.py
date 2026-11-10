from frappe.model.document import Document


class ShopBankAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bank_account: DF.Link
		branch_code_label: DF.Data | None
		conversion_fee_percent: DF.Percent
		instructions: DF.SmallText | None
		label: DF.Data | None
		local_transfer_fee: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		swift_transfer_fee: DF.Float
	# end: auto-generated types

	pass
