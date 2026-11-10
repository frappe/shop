"""Shipping surcharges: amounts added to each parcel's delivery price when the parcel matches every
condition the surcharge sets."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from shop.api import settings as settings_api
from shop.shop.doctype.shop_shipping_surcharge.shop_shipping_surcharge import (
	address_pattern,
	postcode_matches,
)
from shop.storefront import cart, shipping, stock, totals
from shop.tests.utils import fresh_request, sellable, service, template, use_locations

ITEM = "SHOP-DEMO-003"
original_hooks = frappe.get_hooks


def carrier_rates(context):
	"""Two carriers: one whose prices include the store's tax, one whose don't."""
	return [
		{
			"id": "post:parcel",
			"label": "Post Parcel",
			"amount": 11.5,
			"tax_included": True,
			"carrier": "Post",
		},
		{
			"id": "other:parcel",
			"label": "Other Parcel",
			"amount": 10.0,
			"tax_included": False,
			"carrier": "Other Co",
		},
	]


def with_carriers(hook=None, *args, **kwargs):
	if hook == "shop_shipping_rate_providers":
		return ["shop.tests.test_shipping_surcharges.carrier_rates"]
	return original_hooks(hook, *args, **kwargs)


class TestShippingSurcharges(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		frappe.db.delete("Shop Shipping Surcharge")
		fresh_request()
		settings = frappe.get_doc("Shop Settings")
		fields = (
			"flat_shipping_rate",
			"free_shipping_above",
			"shipping_item",
			"prices_include_tax",
			"tax_template",
		)
		self.addCleanup(self.restore, {field: settings.get(field) for field in fields})
		company = settings.company
		self.home = frappe.get_cached_value("Company", company, "country")
		self.other = "United States" if self.home != "United States" else "Australia"
		settings.update(
			{
				"flat_shipping_rate": 10,
				"free_shipping_above": 0,
				"shipping_item": service("TEST-SHIPPING", company),
				"prices_include_tax": 1,
				"tax_template": template(company, "Test VAT 15 included", 15, 1),
			}
		)
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")
		use_locations(self, {"warehouse": stock.primary_warehouse(), "fulfillment_provider": "manual"})
		sellable(ITEM, 5)
		weight = frappe.db.get_value("Item", ITEM, "weight_per_unit")
		frappe.db.set_value("Item", ITEM, "weight_per_unit", 2)
		frappe.clear_document_cache("Item", ITEM)
		self.addCleanup(frappe.clear_document_cache, "Item", ITEM)
		self.addCleanup(frappe.db.set_value, "Item", ITEM, "weight_per_unit", weight)
		cart.add_item(ITEM, qty=1)
		self.cart = cart.resolve_cart()
		self.rural = {
			"address_line1": "1640 Coast Highway",
			"address_line2": "RD 4",
			"city": "Town",
			"pincode": "0984",
			"country": self.home,
		}
		self.town = {
			"address_line1": "8 High Street",
			"city": "City",
			"pincode": "9016",
			"country": self.home,
		}
		self.abroad = {
			"address_line1": "Route 4",
			"address_line2": "RD 7",
			"city": "Town",
			"pincode": "10118",
			"country": self.other,
		}

	def restore(self, values):
		frappe.db.delete("Shop Shipping Surcharge")
		settings = frappe.get_doc("Shop Settings")
		settings.update(values)
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")

	def surcharge(self, name="Rural delivery", **values):
		return frappe.get_doc(
			{
				"doctype": "Shop Shipping Surcharge",
				"surcharge_name": name,
				"label": name,
				"amount": 6.9,
				"amount_includes_tax": 1,
			}
			| values
		).insert(ignore_permissions=True)

	def options(self, address):
		with patch("frappe.get_hooks", side_effect=with_carriers):
			return shipping.get_options(self.cart, frappe._dict(address), 100, refresh=True)["options"]

	def price(self, address, option="flat"):
		return next(o for o in self.options(address) if o["id"] == option)["amount"]

	def test_address_words_with_a_number(self):
		pattern = address_pattern("RD #")
		for text in ("RD 4", "rd4", "R.D. 12", "1640 Coast Highway, RD 4, Town", "Rd 2 Town"):
			self.assertTrue(pattern.search(text), text)
		for text in ("3rd 4 Street", "Ford 4", "RD Street", "Third Road", "RDX 4"):
			self.assertFalse(pattern.search(text), text)

	def test_postcodes_exact_prefix_and_range(self):
		self.assertTrue(postcode_matches("", "1234"))
		self.assertTrue(postcode_matches("9016, 0984", "0984"))
		self.assertTrue(postcode_matches("IV*\nKW*", "iv2 3ab"))
		self.assertTrue(postcode_matches("7000...7999", "7420"))
		self.assertFalse(postcode_matches("7000...7999", "8001"))
		self.assertFalse(postcode_matches("9016", ""))

	def test_a_surcharge_with_no_conditions_is_on_every_delivery(self):
		self.surcharge("Handling", amount=2)
		self.assertAlmostEqual(self.price(self.town), 12)
		self.assertAlmostEqual(self.price(self.abroad), 12)
		self.assertIn("Standard shipping (incl. Handling)", [o["label"] for o in self.options(self.town)])

	def test_an_address_with_the_words_pays_it(self):
		self.surcharge(address_contains="RD #")
		self.assertAlmostEqual(self.price(self.rural), 16.9)
		self.assertEqual(self.price(self.town), 10)

	def test_postcodes(self):
		self.surcharge(postcodes="0900...0999\nIV*")
		self.assertAlmostEqual(self.price(self.rural), 16.9)
		self.assertEqual(self.price(self.town), 10)

	def test_destinations(self):
		rule = self.surcharge(address_contains="RD #", destination="Within the store's country")
		self.assertEqual(self.price(self.abroad), 10)
		for destination, rural, abroad in (
			("Abroad", 10, 16.9),
			("Everywhere", 16.9, 16.9),
			("Only these countries", 10, 16.9),
			("Everywhere except these countries", 16.9, 10),
		):
			rule.reload()
			rule.destination = destination
			rule.set("countries", [{"country": self.other}] if "countries" in destination else [])
			rule.save(ignore_permissions=True)
			self.assertAlmostEqual(self.price(self.rural), rural, msg=destination)
			self.assertAlmostEqual(self.price(self.abroad), abroad, msg=destination)

	def test_only_the_services_named(self):
		self.surcharge(services="post, express")
		self.assertAlmostEqual(self.price(self.town, "post:parcel"), 11.5 + 6.9)
		self.assertEqual(self.price(self.town, "other:parcel"), 10.0)
		self.assertEqual(self.price(self.town), 10)

	def test_parcel_weight_and_value(self):
		rule = self.surcharge("Heavy", weight_from=1.5)
		self.assertAlmostEqual(self.price(self.town), 16.9)
		rule.weight_from = 3
		rule.save(ignore_permissions=True)
		self.assertEqual(self.price(self.town), 10)
		rule.weight_from, rule.value_to = 0, 1
		rule.save(ignore_permissions=True)
		self.assertEqual(self.price(self.town), 10)

	def test_a_percent_of_the_delivery_price(self):
		self.surcharge("Fuel", charge_type="Percent of the delivery price", amount=10)
		self.assertAlmostEqual(self.price(self.town), 11)
		self.assertAlmostEqual(self.price(self.town, "post:parcel"), 12.65)

	def test_a_fixed_amount_on_the_footing_of_the_price(self):
		self.surcharge()
		# a price without tax gets the surcharge without tax
		self.assertAlmostEqual(self.price(self.town, "other:parcel"), 10.0 + 6.0)
		self.assertAlmostEqual(self.price(self.town, "post:parcel"), 11.5 + 6.9)

	def test_a_disabled_surcharge_is_not_added(self):
		self.surcharge(enabled=0)
		self.assertEqual(self.price(self.town), 10)

	def test_collection_is_not_charged(self):
		use_locations(
			self,
			{"warehouse": stock.primary_warehouse(), "fulfillment_provider": "manual", "allow_pickup": 1},
		)
		self.surcharge()
		parcel = shipping.parcels(totals.compute(self.cart, self.town, None, "bank").order)[0]
		found = shipping.get_options(self.cart, frappe._dict(self.rural), 100, True, parcel)["options"]
		pickup = next(option for option in found if shipping.is_pickup(option))
		self.assertEqual(pickup["amount"], 0)
		self.assertNotIn("surcharges", pickup)

	def test_checkout_charges_it_on_the_shipping_line(self):
		self.surcharge(address_contains="RD #")
		rural = totals.compute(self.cart, self.rural, None, "bank")
		town = totals.compute(cart.resolve_cart(), self.town, None, "bank")
		self.assertEqual(rural.shipping["label"], "Standard shipping (incl. Rural delivery)")
		self.assertAlmostEqual(rural.order.grand_total - town.order.grand_total, 6.9, delta=0.01)

	def test_conditions_are_checked(self):
		for values in (
			{"destination": "Only these countries"},
			{"weight_from": 5, "weight_to": 2},
			{"value_from": -1},
			{"amount": -1},
			{"address_contains": " , "},
			{"postcodes": "A...B"},
		):
			with self.assertRaises(frappe.ValidationError, msg=values):
				self.surcharge("Invalid", **values)

	def test_staff_keep_surcharges_in_settings(self):
		saved = settings_api.save_shipping_surcharges(
			[
				{
					"name": "Rural delivery",
					"label": "Rural delivery",
					"address_contains": "RD #",
					"amount": 6,
				},
				{
					"name": "Remote",
					"label": "Remote area",
					"destination": "Only these countries",
					"countries": [self.other],
					"amount": 9,
				},
			]
		)
		self.assertEqual([row["name"] for row in saved], ["Remote", "Rural delivery"])
		self.assertEqual(saved[0]["countries"], [self.other])
		saved = settings_api.save_shipping_surcharges([saved[0]])
		self.assertEqual([row["name"] for row in saved], ["Remote"])
		self.assertFalse(frappe.db.exists("Shop Shipping Surcharge", "Rural delivery"))
