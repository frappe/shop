"""Rates staff set in the Shop admin: for every trade account, one customer or everyone, on an Item
Group or a product, as percent off or a price, with quantity breaks. The most specific applies."""

import frappe
from frappe.tests import IntegrationTestCase

from shop.api import pricing as pricing_api
from shop.storefront import pricing

HARDWARE, TOOLS = "_Test Rates Hardware", "_Test Rates Tools"
TOOL, BOLT = "_Test Rates Tool", "_Test Rates Bolt"
TRADE = "_Test Rates Trade"
MOVED = ("_Test Rates Fixings", "_Test Rates Fasteners")


def ensure(doctype, name, values):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
	return name


class TestRates(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_doc("Shop Settings")
		self.price_list = settings.price_list
		ensure(
			"Item Group",
			HARDWARE,
			{"item_group_name": HARDWARE, "parent_item_group": "All Item Groups", "is_group": 1},
		)
		ensure("Item Group", TOOLS, {"item_group_name": TOOLS, "parent_item_group": HARDWARE, "is_group": 1})
		for item, group in ((TOOL, TOOLS), (BOLT, HARDWARE)):
			ensure(
				"Item",
				item,
				{
					"item_code": item,
					"item_name": item,
					"item_group": group,
					"stock_uom": "Nos",
					"is_stock_item": 0,
				},
			)
			if not frappe.db.exists("Item Price", {"item_code": item, "price_list": self.price_list}):
				frappe.get_doc(
					{
						"doctype": "Item Price",
						"item_code": item,
						"price_list": self.price_list,
						"price_list_rate": 100,
					}
				).insert(ignore_permissions=True)
		ensure(
			"Customer Group",
			TRADE,
			{"customer_group_name": TRADE, "parent_customer_group": "All Customer Groups"},
		)
		retail = frappe.db.get_value("Customer Group", {"is_group": 0, "name": ["!=", TRADE]})
		self.alpha = ensure(
			"Customer", "_Test Rates Alpha", {"customer_name": "_Test Rates Alpha", "customer_group": TRADE}
		)
		self.beta = ensure(
			"Customer", "_Test Rates Beta", {"customer_name": "_Test Rates Beta", "customer_group": TRADE}
		)
		self.retail = ensure(
			"Customer",
			"_Test Rates Retail",
			{"customer_name": "_Test Rates Retail", "customer_group": retail},
		)
		previous = frappe.db.get_single_value("Shop Settings", "trade_customer_group")
		self.addCleanup(frappe.clear_cache, doctype="Shop Settings")
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "trade_customer_group", previous)
		frappe.db.set_single_value("Shop Settings", "trade_customer_group", TRADE)
		frappe.clear_cache(doctype="Shop Settings")
		self.clear_rules()
		self.addCleanup(self.clear_rules)

	def clear_rules(self):
		names = {
			row.parent
			for doctype, field, values in (
				("Pricing Rule Item Group", "item_group", [HARDWARE, TOOLS, *MOVED]),
				("Pricing Rule Item Code", "item_code", [TOOL, BOLT]),
			)
			for row in frappe.get_all(doctype, filters={field: ["in", values]}, fields=["parent"])
		}
		for name in names:
			frappe.delete_doc("Pricing Rule", name, force=True, ignore_permissions=True)

	def price(self, item, customer, qty=1):
		frappe.local.shop_customer_rates = {}
		return pricing.customer_rate(item, customer, self.price_list, qty)

	def save(self, scope, target_type, target, *tiers, customer=None):
		return pricing_api.save_rates(
			scope,
			target_type,
			target,
			[{"from_qty": start, "kind": kind, "value": value} for start, kind, value in tiers],
			customer=customer,
		)

	def test_the_trade_rate_is_for_every_trade_account_and_a_customers_own_replaces_it(self):
		self.save("trade", "Item Group", HARDWARE, (1, "discount", 15))
		self.assertEqual([self.price(BOLT, c) for c in (self.alpha, self.beta, self.retail)], [85, 85, 100])
		self.save("customer", "Item Group", HARDWARE, (1, "discount", 20), customer=self.alpha)
		self.assertEqual([self.price(BOLT, c) for c in (self.alpha, self.beta)], [80, 85])
		rates = pricing_api.get_rates("customer", self.alpha)
		self.assertEqual(rates["rates"][0]["tiers"][0]["label"], "20% off")

	def test_the_most_specific_rate_applies(self):
		self.save("trade", "Item Group", HARDWARE, (1, "discount", 15))
		self.save("trade", "Item Group", TOOLS, (1, "discount", 10))
		self.assertEqual((self.price(TOOL, self.beta), self.price(BOLT, self.beta)), (90, 85))
		self.save("trade", "Product", TOOL, (1, "price", 70))
		self.assertEqual(self.price(TOOL, self.beta), 70)
		# a customer's own rate on the outer Item Group still wins over the trade product price
		self.save("customer", "Item Group", HARDWARE, (1, "discount", 20), customer=self.alpha)
		self.assertEqual(self.price(TOOL, self.alpha), 80)

	def test_quantity_breaks(self):
		self.save("trade", "Product", TOOL, (1, "price", 70), (10, "price", 60), (50, "discount", 50))
		self.assertEqual(
			[self.price(TOOL, self.beta, qty) for qty in (1, 9, 10, 49, 50)], [70, 70, 60, 60, 50]
		)
		tiers = pricing_api.get_rates("trade")["rates"][0]["tiers"]
		self.assertEqual(
			[(t["from_qty"], t["kind"]) for t in tiers], [(0, "price"), (10, "price"), (50, "discount")]
		)
		# a break taken out leaves the others joined up
		self.save("trade", "Product", TOOL, (1, "price", 70), (50, "discount", 50))
		self.assertEqual([self.price(TOOL, self.beta, qty) for qty in (10, 50)], [70, 50])
		self.assertEqual(len(pricing_api.get_rates("trade")["rates"][0]["tiers"]), 2)

	def test_everyones_quantity_breaks_and_the_trade_rate(self):
		self.save("everyone", "Product", BOLT, (5, "discount", 5))
		self.assertEqual([self.price(BOLT, self.retail, qty) for qty in (4, 5)], [100, 95])
		self.save("trade", "Item Group", HARDWARE, (1, "discount", 15))
		self.assertEqual(self.price(BOLT, self.beta, 5), 85)
		self.assertEqual(len(pricing_api.get_rates("everyone", item=BOLT)["rates"]), 1)

	def test_removing_rates(self):
		self.save("trade", "Item Group", HARDWARE, (1, "discount", 15))
		self.assertEqual(pricing_api.remove_rates("trade", "Item Group", HARDWARE)["rates"], [])
		self.assertEqual(self.price(BOLT, self.beta), 100)

	def test_rates_are_checked(self):
		for tiers in (
			[],
			[(1, "discount", 120)],
			[(1, "discount", 0)],
			[(1, "price", 0)],
			[(1, "discount", 10), (1, "discount", 12)],
			[(1, "free", 10)],
		):
			with self.assertRaises(frappe.ValidationError, msg=tiers):
				self.save("trade", "Item Group", HARDWARE, *tiers)
		with self.assertRaises(frappe.ValidationError):
			self.save("trade", "Item Group", "_Test No Such Group", (1, "discount", 5))
		with self.assertRaises(frappe.ValidationError):
			self.save("customer", "Item Group", HARDWARE, (1, "discount", 5))

	def test_rules_set_up_otherwise_in_desk_are_left_alone(self):
		rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Rates two groups",
				"apply_on": "Item Group",
				"item_groups": [{"item_group": HARDWARE}, {"item_group": TOOLS}],
				"applicable_for": "Customer Group",
				"customer_group": TRADE,
				"selling": 1,
				"rate_or_discount": "Discount Percentage",
				"discount_percentage": 3,
				"company": frappe.get_cached_doc("Shop Settings").company,
			}
		).insert(ignore_permissions=True)
		self.save("trade", "Product", TOOL, (1, "price", 70))
		rates = pricing_api.get_rates("trade")
		self.assertEqual([entry["target"] for entry in rates["rates"]], [TOOL])
		self.assertGreaterEqual(rates["set_in_desk"], 1)
		self.assertFalse(frappe.db.get_value("Pricing Rule", rule.name, "has_priority"))

	def test_staff_keep_item_groups(self):
		from shop.api import products

		for name in MOVED:
			if frappe.db.exists("Item Group", name):
				frappe.delete_doc("Item Group", name, force=True, ignore_permissions=True)
		depth = {g["name"]: g["depth"] for g in products.save_item_group("_Test Rates Fixings", HARDWARE)}
		self.assertEqual(depth["_Test Rates Fixings"], depth[HARDWARE] + 1)
		self.save("trade", "Item Group", "_Test Rates Fixings", (1, "discount", 12))
		tree = products.save_item_group(
			"_Test Rates Fasteners", "All Item Groups", name="_Test Rates Fixings"
		)
		moved = next(g for g in tree if g["name"] == "_Test Rates Fasteners")
		self.assertEqual((moved["parent"], moved["depth"]), ("All Item Groups", 2))
		self.assertFalse(frappe.db.exists("Item Group", "_Test Rates Fixings"))
		# the rate follows the renamed Item Group
		self.assertIn("_Test Rates Fasteners", [r["target"] for r in pricing_api.get_rates("trade")["rates"]])
		for name in (HARDWARE, TOOLS):
			with self.assertRaises(frappe.ValidationError):
				products.delete_item_group(name)
		pricing_api.remove_rates("trade", "Item Group", "_Test Rates Fasteners")
		products.delete_item_group("_Test Rates Fasteners")
		self.assertFalse(frappe.db.exists("Item Group", "_Test Rates Fasteners"))

	def test_staff_see_and_move_the_products_in_an_item_group(self):
		from shop.api import products

		group = products.get_item_group(TOOLS)
		self.assertEqual([p["item_code"] for p in group["products"]], [TOOL])
		self.assertEqual(products.get_item_group(HARDWARE)["groups_inside"], [TOOLS])
		moved = products.move_products([TOOL], HARDWARE)
		self.assertIn(TOOL, [p["item_code"] for p in moved["products"]])
		self.assertEqual(products.get_item_group(TOOLS)["products"], [])
		products.move_products([TOOL], TOOLS)
		with self.assertRaises(frappe.ValidationError):
			products.move_products([TOOL], "_Test No Such Group")
