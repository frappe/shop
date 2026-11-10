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
			try:
				frappe.delete_doc("Item", code, ignore_permissions=True, force=True)
			except frappe.LinkExistsError:
				# an item with stock can't be deleted
				frappe.db.set_value("Item", code, "disabled", 1)

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

	def test_a_product_with_stock_gets_options_and_keeps_its_item(self):
		name = f"Stocked {frappe.generate_hash(length=6)}"
		simple = products.create_product(product_name=name, price=300, opening_stock=5)
		self.addCleanup(self.cleanup, simple["name"], name)
		item = frappe.db.get_value("Shop Product", simple["name"], "item")
		self.assertTrue(variants.get_variants(simple["name"])["has_history"])
		# the version sold now has to be named
		with self.assertRaises(frappe.ValidationError):
			variants.set_options(simple["name"], OPTIONS)
		result = variants.set_options(simple["name"], OPTIONS, current={"Size": "Small", "Colour": "Black"})
		product = frappe.get_doc("Shop Product", simple["name"])
		self.assertEqual((product.item, product.default_variant), (f"{item}-V", item))
		self.assertEqual(frappe.db.get_value("Item", item, "variant_of"), product.item)
		self.assertEqual(len(result["variants"]), 4)
		kept = next(v for v in result["variants"] if v["item_code"] == item)
		self.assertEqual(
			(kept["attributes"], kept["stock"], kept["price"]), ({"Size": "Small", "Colour": "Black"}, 5, 300)
		)
		self.assertTrue(all(v["price"] == 300 for v in result["variants"]))

		# a new option gives the versions there are the value named for it
		coating = {"attribute": "Coating", "values": ["None", "Conformal"]}
		with self.assertRaises(frappe.ValidationError):
			variants.set_options(simple["name"], [*OPTIONS, coating])
		grown = variants.set_options(simple["name"], [*OPTIONS, coating], current={"Coating": "None"})
		self.assertEqual(len(grown["variants"]), 8)
		kept = next(v for v in grown["variants"] if v["item_code"] == item)
		self.assertEqual(kept["attributes"], {"Size": "Small", "Colour": "Black", "Coating": "None"})
		self.assertEqual(kept["stock"], 5)

	# --- what the product page shows ------------------------------------------

	def page(self, product):
		from shop.storefront.product import get_product

		frappe.clear_document_cache("Shop Product", product)
		return get_product(frappe.db.get_value("Shop Product", product, "slug"))

	def code(self, result, **attributes):
		return next(v["item_code"] for v in result["variants"] if v["attributes"] == attributes)

	def test_variants_follow_the_order_of_the_option_values(self):
		result = self.create(name="Ordered Tee")
		order = [v["attributes"] for v in result["variants"]]
		self.assertEqual(
			order,
			[
				{"Size": "Small", "Colour": "Black"},
				{"Size": "Small", "Colour": "White"},
				{"Size": "Medium", "Colour": "Black"},
				{"Size": "Medium", "Colour": "White"},
			],
		)
		page = self.page(result["product"])
		self.assertEqual([v["attributes"] for v in page["variants"]], order)
		self.assertEqual(page["attributes"], OPTIONS)
		# the page opens on the first that can be bought
		self.assertEqual(page["default_item_code"], self.code(result, Size="Small", Colour="Black"))

	def test_the_page_opens_on_the_default_variant_while_it_can_be_bought(self):
		result = self.create(name="Default Tee")
		medium_white = self.code(result, Size="Medium", Colour="White")
		saved = variants.set_default_variant(result["product"], medium_white)
		self.assertEqual(saved["default_variant"], medium_white)
		self.assertEqual(self.page(result["product"])["default_item_code"], medium_white)
		# sold out: the first one that can be bought instead
		variants.update_variant(medium_white, stock=0)
		self.assertEqual(
			self.page(result["product"])["default_item_code"], self.code(result, Size="Small", Colour="Black")
		)
		variants.set_default_variant(result["product"], None)
		self.assertIsNone(frappe.db.get_value("Shop Product", result["product"], "default_variant"))

	def test_a_switched_off_variant_is_not_on_the_page(self):
		result = self.create(name="Hidden Tee")
		small_black = self.code(result, Size="Small", Colour="Black")
		variants.update_variant(small_black, disabled=True)
		page = self.page(result["product"])
		self.assertNotIn(small_black, [v["item_code"] for v in page["variants"]])
		self.assertEqual(page["default_item_code"], self.code(result, Size="Small", Colour="White"))
		self.assertEqual(page["unavailable_label"], "Not available")

	def test_the_default_variant_must_be_the_products_own(self):
		result = self.create(name="Own Tee")
		other = self.create(name="Other Tee")
		with self.assertRaises(frappe.ValidationError):
			variants.set_default_variant(result["product"], other["variants"][0]["item_code"])
