import frappe
from frappe.tests import IntegrationTestCase

from shop.themes import ensure_default_theme, reset_theme


class TestThemes(IntegrationTestCase):
	def tearDown(self):
		settings = frappe.get_cached_doc("Shop Settings")
		if settings.active_theme:
			reset_theme(settings.active_theme)

	def test_ensure_default_theme_publishes_lowest_order_theme(self):
		ensure_default_theme()
		settings = frappe.get_doc("Shop Settings")
		self.assertEqual(settings.active_theme, "frappe")
		live_pages = frappe.get_all("Builder Page", filters={"is_template": 0}, fields=["route", "published"])
		self.assertEqual(len(live_pages), 11)
		self.assertTrue(all(page.published for page in live_pages))

	def test_ensure_default_theme_is_a_noop_once_a_theme_is_active(self):
		ensure_default_theme()
		live_pages_before = frappe.get_all("Builder Page", filters={"is_template": 0}, pluck="name")

		ensure_default_theme()

		live_pages_after = frappe.get_all("Builder Page", filters={"is_template": 0}, pluck="name")
		self.assertEqual(sorted(live_pages_before), sorted(live_pages_after))
