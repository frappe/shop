import frappe
from frappe.tests import IntegrationTestCase

from shop.api import products, variants

OPTIONS = [
	{"attribute": "Size", "values": ["Small", "Medium"]},
	{"attribute": "Colour", "values": ["Black", "White"]},
]


class TestVariants(IntegrationTestCase):
	def create(self, name="Variant Test Tee", opening_stock=2):
		result = variants.create_variant_product(
			product_name=name, options=OPTIONS, price=700, opening_stock=opening_stock
		)
		self.addCleanup(self.cleanup, result["product"], name)
		return result

	def cleanup(self, product, name):
		if frappe.db.exists("Shop Product", product):
			products.delete_product(product)
		for code in frappe.get_all("Item", filters={"item_name": ["like", f"{name}%"]}, pluck="name"):
			frappe.delete_doc("Item", code, ignore_permissions=True, force=True)

	def test_creates_one_variant_per_combination(self):
		result = self.create()
		self.assertEqual(len(result["variants"]), 4)
		combos = {tuple(sorted(variant["attributes"].items())) for variant in result["variants"]}
		self.assertEqual(len(combos), 4)
		self.assertTrue(all(variant["stock"] == 2 for variant in result["variants"]))
		self.assertTrue(all(variant["price"] == 700 for variant in result["variants"]))

	def test_options_are_scoped_to_the_product(self):
		"""A product must not inherit every value of a shared attribute."""
		result = self.create(name="Scoped Tee")
		sizes = next(o["values"] for o in result["options"] if o["attribute"] == "Size")
		self.assertEqual(sizes, ["Small", "Medium"])
		self.assertGreater(
			len(frappe.get_all("Item Attribute Value", filters={"parent": "Size"})), len(sizes)
		)

	def test_adding_a_value_generates_only_new_combinations(self):
		result = self.create(name="Growing Tee")
		expanded = variants.set_options(
			result["product"],
			[
				{"attribute": "Size", "values": ["Small", "Medium", "Large"]},
				{"attribute": "Colour", "values": ["Black", "White"]},
			],
		)
		self.assertEqual(len(expanded["variants"]), 6)
		self.assertEqual(expanded["missing_combinations"], 0)

	def test_update_variant_price_and_availability(self):
		result = self.create(name="Editable Tee")
		code = result["variants"][0]["item_code"]
		updated = variants.update_variant(code, price=950, disabled=True)
		variant = next(v for v in updated["variants"] if v["item_code"] == code)
		self.assertEqual(variant["price"], 950)
		self.assertTrue(variant["disabled"])

	def test_demo_product_infers_its_own_option_values(self):
		payload = variants.get_variants("crew-neck-t-shirt")
		self.assertTrue(payload["has_variants"])
		self.assertEqual(len(payload["variants"]), 6)
		self.assertEqual(payload["missing_combinations"], 0)

	def test_options_blocked_once_stock_exists(self):
		simple = products.create_product(product_name="Simple Stocked", price=300, opening_stock=5)
		self.addCleanup(self.cleanup, simple["name"], "Simple Stocked")
		payload = variants.get_variants(simple["name"])
		self.assertFalse(payload["has_variants"])
		self.assertFalse(payload["can_add_options"])
		with self.assertRaises(frappe.ValidationError):
			variants.set_options(simple["name"], OPTIONS)
