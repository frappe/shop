import json

import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import page_data
from shop.tests.utils import fresh_request


class TestSearchEngines(IntegrationTestCase):
	def setUp(self):
		fresh_request()
		self.slug = frappe.db.get_value("Shop Product", {"item": "SHOP-DEMO-003", "published": 1}, "slug")
		if not self.slug:
			self.skipTest("no published demo product")

	def test_a_product_page_says_what_it_sells(self):
		frappe.form_dict.slug = self.slug
		data = page_data.product_page()
		name = data["product"]["product_name"]
		self.assertEqual(data["title"], frappe.utils.escape_html(name))
		self.assertTrue(data["metatags"]["title"].startswith(name))
		self.assertEqual(data["metatags"]["og:type"], "product")
		self.assertLessEqual(len(data["metatags"]["description"]), 160)

		product = json.loads(data["product"]["structured_data"])
		self.assertEqual((product["@type"], product["name"]), ("Product", name))
		self.assertEqual(
			product["offers"]["priceCurrency"], frappe.db.get_single_value("Shop Settings", "currency")
		)
		self.assertIn(
			product["offers"]["availability"], ("https://schema.org/InStock", "https://schema.org/OutOfStock")
		)
		self.assertTrue(product["offers"]["url"].endswith(f"product/{self.slug}"))

	def test_structured_data_cant_end_its_script(self):
		data = page_data.structured_data(
			{
				"product_name": "Mug </script><script>alert(1)</script>",
				"item": "SHOP-DEMO-003",
				"slug": self.slug,
				"description_text": "",
				"price": 10,
			}
		)
		self.assertNotIn("</script>", data)
		self.assertEqual(json.loads(data)["name"], "Mug </script><script>alert(1)</script>")

	def test_the_store_sitemap_lists_products_and_shoppers_pages_are_left_out(self):
		from shop.theme_generators.blocks import private_route
		from shop.www import store_sitemap

		links = [link["loc"] for link in store_sitemap.get_context(frappe._dict())["links"]]
		self.assertTrue(any(link.endswith(f"product/{self.slug}") for link in links))
		for route in (
			"cart",
			"checkout",
			"account/orders",
			"order-confirmation/:order_id",
			"quote/:quote_id",
		):
			self.assertTrue(private_route(route), route)
		for route in ("home", "products", "product/:slug", "collection/:slug", "terms"):
			self.assertFalse(private_route(route), route)
