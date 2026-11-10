import json

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from shop.routes import (
	normalize_prefix,
	page_route,
	rewrite_blocks,
	rewrite_html,
	rewrite_url,
	signin_url,
	store_url,
	with_prefix_script,
)
from shop.themes import apply_route_prefix, ensure_default_theme, reset_theme


class TestRouteHelpers(UnitTestCase):
	def test_normalize_prefix(self):
		self.assertEqual(normalize_prefix(" /Store/ "), "store")
		self.assertEqual(normalize_prefix("shop//en"), "shop/en")
		self.assertEqual(normalize_prefix(None), "")

	def test_signin_comes_back_only_to_this_site(self):
		from shop.storefront.page_data import return_path

		self.assertEqual(signin_url("/store/cart"), store_url("account/signin") + "?redirect-to=/store/cart")
		self.assertEqual(return_path("/store/product/mug"), "/store/product/mug")
		for elsewhere in (
			"https://example.com",
			"//example.com",
			"/\\example.com",
			"/\t/example.com",
			"/\n/example.com",
			None,
		):
			self.assertEqual(return_path(elsewhere), store_url("account/orders"))

	def test_store_url(self):
		self.assertEqual(store_url("cart", prefix="store"), "/store/cart")
		self.assertEqual(store_url("", prefix="store"), "/store")
		self.assertEqual(store_url("home", prefix="store"), "/store")
		self.assertEqual(store_url("products?search=mug", prefix="store"), "/store/products?search=mug")
		self.assertEqual(store_url("cart", prefix=""), "/cart")
		self.assertEqual(store_url("", prefix=""), "/")

	def test_page_route(self):
		self.assertEqual(page_route("home", "store"), "store")
		self.assertEqual(page_route("product/:slug", "store"), "store/product/:slug")
		self.assertEqual(page_route("cart", ""), "cart")
		self.assertEqual(page_route("home", ""), "home")

	def test_rewrite_url_moves_storefront_links_only(self):
		self.assertEqual(rewrite_url("/cart", "store"), "/store/cart")
		self.assertEqual(rewrite_url("/", "store"), "/store")
		self.assertEqual(rewrite_url("/home", "store"), "/store")
		self.assertEqual(rewrite_url("/products?sort=new", "store"), "/store/products?sort=new")
		self.assertEqual(rewrite_url("/account/orders", "store"), "/store/account/orders")
		for untouched in (
			"/login",
			"/app/item",
			"/assets/shop/x.png",
			"https://example.com/cart",
			"//cdn/x",
			"#top",
		):
			self.assertEqual(rewrite_url(untouched, "store"), untouched)

	def test_rewrite_url_is_idempotent_and_moves_between_prefixes(self):
		self.assertEqual(rewrite_url("/store/cart", "store"), "/store/cart")
		self.assertEqual(rewrite_url("/store", "store"), "/store")
		self.assertEqual(rewrite_url("/store/cart", "shop", old_prefix="store"), "/shop/cart")
		self.assertEqual(rewrite_url("/store/cart", "", old_prefix="store"), "/cart")
		self.assertEqual(rewrite_url("/store", "", old_prefix="store"), "/")
		self.assertEqual(rewrite_url("/store/unrelated", "", old_prefix="store"), "/store/unrelated")

	def test_rewrite_html(self):
		html = '<a href="/cart">Cart</a> <a href="/login">Sign in</a> <form action=\'/products\'></form>'
		self.assertEqual(
			rewrite_html(html, "store"),
			'<a href="/store/cart">Cart</a> <a href="/login">Sign in</a> <form action=\'/store/products\'></form>',
		)

	def test_rewrite_blocks(self):
		blocks = [
			{
				"attributes": {"href": "/products"},
				"children": [
					{"attributes": {"href": "/cart"}},
					{"innerHTML": '<a href="/faq">FAQ</a>'},
					{"attributes": {"href": "/login"}},
				],
			}
		]
		as_json = json.dumps(blocks)
		result = json.loads(rewrite_blocks(as_json, "store"))
		self.assertEqual(result[0]["attributes"]["href"], "/store/products")
		self.assertEqual(result[0]["children"][0]["attributes"]["href"], "/store/cart")
		self.assertEqual(result[0]["children"][1]["innerHTML"], '<a href="/store/faq">FAQ</a>')
		self.assertEqual(result[0]["children"][2]["attributes"]["href"], "/login")

		unchanged = json.dumps([{"attributes": {"href": "/login"}}], indent=2)
		self.assertIs(rewrite_blocks(unchanged, "store"), unchanged)

	def test_prefix_script(self):
		body = '<script src="/assets/shop/js/storefront.js" defer></script>'
		with_script = with_prefix_script(body, "store")
		self.assertIn('window.shop_route_prefix = "/store"', with_script)
		self.assertEqual(with_prefix_script(with_script, "store"), with_script)
		self.assertEqual(with_prefix_script(with_script, ""), body)


class TestRoutePrefixThemes(IntegrationTestCase):
	def setUp(self):
		self.home_page = frappe.db.get_single_value("Builder Settings", "home_page")

	def tearDown(self):
		frappe.db.set_single_value("Shop Settings", "route_prefix", None)
		settings = frappe.get_cached_doc("Shop Settings")
		if settings.active_theme:
			reset_theme(settings.active_theme)
		frappe.db.set_single_value("Shop Settings", "applied_route_prefix", None)
		frappe.db.set_single_value("Builder Settings", "home_page", self.home_page)

	def live_routes(self):
		return set(frappe.get_all("Builder Page", filters={"is_template": 0}, pluck="route"))

	def test_theme_applied_under_prefix_keeps_site_home_page(self):
		frappe.db.set_single_value("Builder Settings", "home_page", "site-home")
		frappe.db.set_single_value("Shop Settings", "route_prefix", "store")

		ensure_default_theme()

		routes = self.live_routes()
		self.assertIn("store", routes)
		self.assertIn("store/cart", routes)
		self.assertIn("store/product/:slug", routes)
		self.assertFalse(routes & {"home", "cart", "about", "contact"})
		self.assertEqual(frappe.db.get_single_value("Builder Settings", "home_page"), "site-home")

	def test_changing_the_prefix_moves_live_pages(self):
		ensure_default_theme()
		self.assertIn("cart", self.live_routes())

		settings = frappe.get_doc("Shop Settings")
		settings.route_prefix = "store"
		settings.save()

		routes = self.live_routes()
		self.assertIn("store/cart", routes)
		self.assertNotIn("cart", routes)
		self.assertEqual(frappe.db.get_single_value("Shop Settings", "applied_route_prefix"), "store")

		apply_route_prefix()  # idempotent
		self.assertEqual(self.live_routes(), routes)

	def test_prefix_cannot_shadow_a_storefront_path(self):
		settings = frappe.get_doc("Shop Settings")
		settings.route_prefix = "products"
		self.assertRaises(frappe.ValidationError, settings.save)
