import frappe
from frappe.tests import IntegrationTestCase

from shop import demo


class TestDemo(IntegrationTestCase):
	def test_setup_is_idempotent(self):
		demo.setup()
		demo.setup()
		self.assertEqual(frappe.db.count("Shop Product"), len(demo.PRODUCTS))
		self.assertEqual(frappe.db.count("Shop Collection"), len(demo.COLLECTIONS))

	def test_variant_templates(self):
		for template in ("SHOP-DEMO-001", "SHOP-DEMO-002"):
			variants = frappe.get_all("Item", filters={"variant_of": template})
			self.assertEqual(len(variants), 6)

	def test_published_products_have_price_and_stock(self):
		settings = frappe.get_cached_doc("Shop Settings")
		for product in frappe.get_all("Shop Product", filters={"published": 1}, fields=["item", "has_variants"]):
			items = (
				frappe.get_all("Item", filters={"variant_of": product.item}, pluck="name")
				if product.has_variants
				else [product.item]
			)
			for item_code in items:
				self.assertTrue(
					frappe.db.exists("Item Price", {"item_code": item_code, "price_list": settings.price_list}),
					f"no price for {item_code}",
				)
