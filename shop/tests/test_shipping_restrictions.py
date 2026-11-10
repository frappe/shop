"""Where products can be sent: a Shop Shipping Restriction on an Item Group or an Item, kept to at
checkout and said on product pages."""

import frappe
from frappe.tests import IntegrationTestCase

from shop.api import products as products_api
from shop.api import settings as settings_api
from shop.storefront import cart, checkout, shipping, stock, totals
from shop.tests.utils import fresh_request, sellable, use_locations

ITEM = "SHOP-DEMO-003"
BUYER = {"email": "restricted-buyer@example.com", "full_name": "Restricted Buyer"}
ONLY_HOME, NOT_HOME = "_Test Domestic only", "_Test International only"


class TestShippingRestrictions(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()
		company = frappe.get_cached_doc("Shop Settings").company
		self.home = frappe.get_cached_value("Company", company, "country")
		self.other = "United States" if self.home != "United States" else "Australia"
		self.group = frappe.get_cached_value("Item", ITEM, "item_group")
		for name, ships_to in (
			(ONLY_HOME, "Only to these countries"),
			(NOT_HOME, "Everywhere except these countries"),
		):
			if not frappe.db.exists("Shop Shipping Restriction", name):
				frappe.get_doc(
					{
						"doctype": "Shop Shipping Restriction",
						"restriction_name": name,
						"ships_to": ships_to,
						"countries": [{"country": self.home}],
					}
				).insert(ignore_permissions=True)
		self.addCleanup(self.restrict, None, None)
		use_locations(self, {"warehouse": stock.primary_warehouse(), "fulfillment_provider": "manual"})
		sellable(ITEM, 5)
		self.home_address = {
			"address_line1": "5 High Street",
			"city": "Town",
			"pincode": "9016",
			"country": self.home,
		}
		self.abroad = {
			"address_line1": "350 5th Ave",
			"city": "New York",
			"pincode": "10118",
			"country": self.other,
		}

	def restrict(self, item: str | None = None, group: str | None = None) -> None:
		frappe.db.set_value("Item", ITEM, "shop_shipping_restriction", item)
		frappe.db.set_value("Item Group", self.group, "shop_shipping_restriction", group)
		frappe.clear_document_cache("Item", ITEM)
		frappe.clear_document_cache("Item Group", self.group)

	def quote(self, address):
		cart.add_item(ITEM, qty=1)
		return totals.compute(cart.resolve_cart(), address, None, "bank")

	def test_a_domestic_only_product_is_not_sent_abroad(self):
		self.restrict(item=ONLY_HOME)
		home = self.quote(self.home_address)
		self.assertTrue(home.shipping)
		abroad = totals.compute(cart.resolve_cart(), self.abroad, None, "bank")
		self.assertIsNone(abroad.shipping)
		name = frappe.get_cached_value("Item", ITEM, "item_name")
		self.assertEqual(abroad.shipping_messages, [f"{name} can't be sent to {self.other}."])
		with self.assertRaisesRegex(frappe.ValidationError, "can't be sent to"):
			checkout.place_order(customer=BUYER, address=self.abroad, payment_method="bank")

	def test_an_item_group_restriction_covers_its_items(self):
		self.restrict(group=NOT_HOME)
		self.assertIsNone(self.quote(self.home_address).shipping)
		self.assertTrue(totals.compute(cart.resolve_cart(), self.abroad, None, "bank").shipping)

	def test_a_parent_groups_restriction_covers_the_groups_under_it(self):
		parent = frappe.get_cached_value("Item Group", self.group, "parent_item_group")
		if not parent:
			self.skipTest("the item's group has no parent")
		frappe.db.set_value("Item Group", parent, "shop_shipping_restriction", ONLY_HOME)
		frappe.clear_document_cache("Item Group", parent)
		self.addCleanup(frappe.clear_document_cache, "Item Group", parent)
		self.addCleanup(frappe.db.set_value, "Item Group", parent, "shop_shipping_restriction", None)
		self.assertFalse(shipping.can_send(ITEM, self.other))
		self.assertTrue(shipping.can_send(ITEM, self.home))

	def test_the_items_own_restriction_comes_before_its_groups(self):
		self.restrict(item=NOT_HOME, group=ONLY_HOME)
		self.assertTrue(shipping.can_send(ITEM, self.other))
		self.assertFalse(shipping.can_send(ITEM, self.home))

	def test_a_variant_follows_its_template(self):
		variant = frappe.db.get_value(
			"Item", {"variant_of": ["is", "set"], "disabled": 0}, ["name", "variant_of"], as_dict=True
		)
		if not variant:
			self.skipTest("no variant items")
		frappe.db.set_value("Item", variant.variant_of, "shop_shipping_restriction", ONLY_HOME)
		frappe.clear_document_cache("Item", variant.variant_of)
		self.addCleanup(frappe.clear_document_cache, "Item", variant.variant_of)
		self.addCleanup(frappe.db.set_value, "Item", variant.variant_of, "shop_shipping_restriction", None)
		self.assertFalse(shipping.can_send(variant.name, self.other))

	def test_a_restricted_product_can_still_be_collected(self):
		use_locations(
			self,
			{"warehouse": stock.primary_warehouse(), "fulfillment_provider": "manual", "allow_pickup": 1},
		)
		self.restrict(item=ONLY_HOME)
		quote = self.quote(self.abroad)
		self.assertTrue(shipping.is_pickup(quote.shipping))
		self.assertTrue(quote.shipping_messages)

	def test_product_pages_say_where_it_is_sent(self):
		self.assertNotIn("shipping_note", stock.availability(ITEM))
		self.restrict(item=ONLY_HOME)
		self.assertEqual(stock.availability(ITEM)["shipping_note"], f"Ships only to {self.home}")
		frappe.db.set_value(
			"Shop Shipping Restriction", ONLY_HOME, "customer_note", "Within <b>home</b> only"
		)
		frappe.clear_document_cache("Shop Shipping Restriction", ONLY_HOME)
		self.addCleanup(frappe.db.set_value, "Shop Shipping Restriction", ONLY_HOME, "customer_note", None)
		self.assertEqual(stock.availability(ITEM)["shipping_note"], "Within &lt;b&gt;home&lt;/b&gt; only")

	def test_staff_set_restrictions_and_item_groups_in_settings(self):
		saved = settings_api.save_shipping_restrictions(
			[
				{"name": ONLY_HOME, "ships_to": "Only to these countries", "countries": [self.home]},
				{"name": NOT_HOME, "ships_to": "Everywhere except these countries", "countries": [self.home]},
				{
					"name": "_Test Not there",
					"ships_to": "Everywhere except these countries",
					"countries": [self.other],
				},
			],
			[{"item_group": self.group, "restriction": "_Test Not there"}],
		)
		self.assertIn("_Test Not there", [row["name"] for row in saved["shipping_restrictions"]])
		self.assertIn(
			{"item_group": self.group, "restriction": "_Test Not there"}, saved["item_group_restrictions"]
		)
		self.assertFalse(shipping.can_send(ITEM, self.other))
		# taken off the list: the restriction goes, and the group with it
		saved = settings_api.save_shipping_restrictions(
			[
				{"name": ONLY_HOME, "ships_to": "Only to these countries", "countries": [self.home]},
				{"name": NOT_HOME, "ships_to": "Everywhere except these countries", "countries": [self.home]},
			],
			[],
		)
		self.assertFalse(frappe.db.exists("Shop Shipping Restriction", "_Test Not there"))
		self.assertEqual(saved["item_group_restrictions"], [])
		self.assertTrue(shipping.can_send(ITEM, self.other))

	def test_a_restriction_a_product_uses_is_not_removed(self):
		self.restrict(item=ONLY_HOME)
		with self.assertRaises(frappe.LinkExistsError):
			settings_api.save_shipping_restrictions(
				[
					{
						"name": NOT_HOME,
						"ships_to": "Everywhere except these countries",
						"countries": [self.home],
					}
				],
				[],
			)

	def test_the_product_editor_sets_the_items_restriction(self):
		product = frappe.db.get_value("Shop Product", {"item": ITEM})
		if not product:
			self.skipTest("no product for the item")
		products_api.save_product({"name": product, "shipping_restriction": ONLY_HOME})
		self.assertEqual(products_api.get_product(product)["shipping_restriction"], ONLY_HOME)
		products_api.save_product({"name": product, "shipping_restriction": ""})
		self.assertIsNone(frappe.db.get_value("Item", ITEM, "shop_shipping_restriction"))
