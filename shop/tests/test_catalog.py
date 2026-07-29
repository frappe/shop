import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import catalog, product


class TestCatalog(IntegrationTestCase):
	def test_listing_returns_published_products(self):
		result = catalog.get_products()
		self.assertEqual(result["total"], frappe.db.count("Shop Product", {"published": 1}))
		self.assertTrue(result["products"])
		first = result["products"][0]
		self.assertIn("slug", first)
		self.assertIsNotNone(first.formatted_price)
		self.assertTrue(first.in_stock)

	def test_collection_filter(self):
		result = catalog.get_products(collection="apparel")
		slugs = {p.slug for p in result["products"]}
		self.assertIn("crew-neck-t-shirt", slugs)
		self.assertNotIn("ceramic-mug", slugs)

	def test_search(self):
		result = catalog.get_products(search="mug")
		self.assertEqual(result["total"], 1)
		self.assertEqual(result["products"][0].slug, "ceramic-mug")

	def test_collections_have_counts(self):
		collections = catalog.get_collections()
		self.assertEqual(len(collections), 4)
		self.assertTrue(all(c.product_count > 0 for c in collections))

	def test_product_detail_simple(self):
		detail = product.get_product("ceramic-mug")
		self.assertEqual(detail["item"], "SHOP-DEMO-003")
		self.assertTrue(detail["in_stock"])
		self.assertTrue(detail["images"])
		self.assertFalse(detail["has_variants"])

	def test_product_detail_variants(self):
		detail = product.get_product("crew-neck-t-shirt")
		self.assertTrue(detail["has_variants"])
		self.assertEqual(len(detail["variants"]), 6)
		attributes = {a["attribute"]: a["values"] for a in detail["attributes"]}
		self.assertEqual(attributes["Size"], ["Small", "Medium", "Large"])
		self.assertIn(detail["default_item_code"], [v["item_code"] for v in detail["variants"]])

	def test_unpublished_product_hidden(self):
		with self.assertRaises(frappe.DoesNotExistError):
			product.get_product("does-not-exist")
