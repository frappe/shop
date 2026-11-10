import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

LISTED = ("Only these countries", "Everywhere except these countries")
PERCENT = "Percent of the delivery price"


class ShopShippingSurcharge(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from shop.shop.doctype.shop_country.shop_country import ShopCountry

		address_contains: DF.Data | None
		amount: DF.Float
		amount_includes_tax: DF.Check
		charge_type: DF.Literal["Fixed amount", "Percent of the delivery price"]
		countries: DF.TableMultiSelect[ShopCountry]
		destination: DF.Literal[
			"Everywhere",
			"Within the store's country",
			"Abroad",
			"Only these countries",
			"Everywhere except these countries",
		]
		enabled: DF.Check
		label: DF.Data
		postcodes: DF.SmallText | None
		services: DF.Data | None
		surcharge_name: DF.Data
		value_from: DF.Float
		value_to: DF.Float
		weight_from: DF.Float
		weight_to: DF.Float
	# end: auto-generated types

	def validate(self):
		if self.destination in LISTED and not self.countries:
			frappe.throw(_("Pick the countries the destination names"))
		if self.destination not in LISTED:
			self.countries = []
		for low, high, label in (
			(self.weight_from, self.weight_to, _("parcel weight")),
			(self.value_from, self.value_to, _("parcel value")),
		):
			if flt(low) < 0 or flt(high) < 0 or (flt(high) and flt(low) > flt(high)):
				frappe.throw(_("The {0} range is not valid").format(label))
		if flt(self.amount) < 0:
			frappe.throw(_("The amount can't be negative"))
		if self.address_contains and not any(c.isalnum() or c == "#" for c in self.address_contains):
			frappe.throw(_("Address Contains needs a word or # for a number"))
		for entry in postcode_entries(self.postcodes):
			if is_range(entry) and not all(part.isdigit() for part in range_parts(entry)):
				frappe.throw(_("Postcode range {0} must be two numbers").format(frappe.bold(entry)))

	def matches(self, address: dict, home_country: str | None, parcel: dict, option: dict) -> bool:
		"""Whether the surcharge applies to this delivery option for the parcel and address.

		parcel holds the goods' weight and value; option is a checkout delivery option."""
		return (
			self.matches_destination(address.get("country"), home_country)
			and postcode_matches(self.postcodes, address.get("pincode"))
			and (
				not self.address_contains
				or address_pattern(self.address_contains).search(address_text(address)) is not None
			)
			and self.matches_service(option)
			and within(parcel.get("weight"), self.weight_from, self.weight_to)
			and within(parcel.get("value"), self.value_from, self.value_to)
		)

	def matches_destination(self, country: str | None, home_country: str | None) -> bool:
		if self.destination == "Within the store's country":
			return country == home_country
		if self.destination == "Abroad":
			return country != home_country
		if self.destination in LISTED:
			listed = country in {row.country for row in self.countries}
			return listed if self.destination == "Only these countries" else not listed
		return True

	def matches_service(self, option: dict) -> bool:
		wanted = [word.strip().lower() for word in (self.services or "").split(",") if word.strip()]
		if not wanted:
			return True
		name = " ".join(str(option.get(key) or "") for key in ("label", "carrier", "service")).lower()
		return any(word in name for word in wanted)

	def charge(self, option: dict, tax_factor: float) -> float:
		"""The surcharge on the option's price, on the same footing: with tax or without, as the
		price is. tax_factor is 1 plus the store's tax rate."""
		if self.charge_type == PERCENT:
			return flt(option.get("amount")) * flt(self.amount) / 100
		amount = flt(self.amount)
		if bool(self.amount_includes_tax) == bool(option.get("tax_included")):
			return amount
		return amount / tax_factor if self.amount_includes_tax else amount * tax_factor


def within(value, low, high) -> bool:
	value = flt(value)
	return value >= flt(low) and (not flt(high) or value <= flt(high))


def address_text(address: dict) -> str:
	return " ".join(
		str(address.get(key) or "") for key in ("address_line1", "address_line2", "city", "state", "pincode")
	)


def address_pattern(text: str) -> re.Pattern:
	"""Words in any case, a letter optionally followed by a full stop, # for a number, with no letter
	or digit joined on at either end: "RD #" finds "RD 4", "rd4" and "R.D. 12", not "3rd 4"."""
	parts = []
	for char in (text or "").strip():
		if char == "#":
			parts.append(r"\s*\d+")
		elif char.isspace():
			parts.append(r"[\s,]*")
		elif char.isalpha():
			parts.append(re.escape(char) + r"\.?")
		else:
			parts.append(re.escape(char))
	return re.compile(r"(?<![^\W_])" + "".join(parts) + r"(?![^\W_])", re.IGNORECASE)


def postcode_entries(text: str | None) -> list[str]:
	return [re.sub(r"\s+", "", entry).upper() for entry in re.split(r"[,\n]+", text or "") if entry.strip()]


def is_range(entry: str) -> bool:
	return "..." in entry or ".." in entry


def range_parts(entry: str) -> list[str]:
	return re.split(r"\.{2,3}", entry, maxsplit=1)


def postcode_matches(text: str | None, postcode: str | None) -> bool:
	"""Whether the postcode is one listed: exactly, by a prefix ending in *, or in a range of numbers."""
	entries = postcode_entries(text)
	if not entries:
		return True
	code = re.sub(r"\s+", "", postcode or "").upper()
	if not code:
		return False
	for entry in entries:
		if entry.endswith("*"):
			if code.startswith(entry[:-1]):
				return True
		elif is_range(entry):
			low, high = range_parts(entry)
			if code.isdigit() and low.isdigit() and high.isdigit() and int(low) <= int(code) <= int(high):
				return True
		elif code == entry:
			return True
	return False
