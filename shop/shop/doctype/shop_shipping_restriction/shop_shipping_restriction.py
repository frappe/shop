import frappe
from frappe import _
from frappe.model.document import Document


class ShopShippingRestriction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from shop.shop.doctype.shop_country.shop_country import ShopCountry

		countries: DF.TableMultiSelect[ShopCountry]
		customer_note: DF.Data | None
		restriction_name: DF.Data
		ships_to: DF.Literal["Only to these countries", "Everywhere except these countries"]
	# end: auto-generated types

	def validate(self):
		seen = set()
		for row in self.countries:
			if row.country in seen:
				frappe.throw(_("{0} is listed twice").format(frappe.bold(row.country)))
			seen.add(row.country)

	def allows(self, country: str | None) -> bool:
		listed = country in {row.country for row in self.countries}
		return listed if self.ships_to == "Only to these countries" else not listed

	def note(self) -> str:
		"""What a product page says about where the product is sent."""
		if self.customer_note:
			return self.customer_note
		countries = ", ".join(_(row.country) for row in self.countries)
		if self.ships_to == "Only to these countries":
			return _("Ships only to {0}").format(countries)
		return _("Doesn't ship to {0}").format(countries)
