import frappe
from frappe.tests import IntegrationTestCase

from shop.agent import setup as agent_setup
from shop.agent import tools


class TestAgentTools(IntegrationTestCase):
	def test_every_tool_is_registered_with_flow(self):
		if "flow" not in frappe.get_installed_apps():
			self.skipTest("flow is not installed")
		agent_setup.sync()
		from flow import Tool

		expected = {value.name for value in vars(tools).values() if isinstance(value, Tool)}
		self.assertGreaterEqual(len(expected), 20)
		for name in expected:
			self.assertTrue(frappe.db.exists("Flow Tool", name), f"{name} not registered")
			self.assertEqual(frappe.db.get_value("Flow Tool", name, "import_path"), f"shop.agent.tools.{name}")

	def test_write_tools_require_confirmation(self):
		from flow import Tool

		must_confirm = {
			"add_product",
			"update_product",
			"add_product_with_options",
			"update_variant",
			"set_stock",
			"mark_order_paid",
			"fulfill_order",
			"cancel_order",
			"delete_review",
			"create_discount",
			"set_discount_enabled",
			"update_store_settings",
			"load_sample_catalog",
		}
		for name in must_confirm:
			tool = getattr(tools, name)
			self.assertIsInstance(tool, Tool)
			self.assertTrue(tool.requires_confirmation, f"{name} should ask before running")

	def test_read_tools_return_live_data(self):
		overview = tools.store_overview()
		self.assertIn("performance", overview)
		self.assertIn("today", overview)
		listing = tools.list_products(search="mug")
		self.assertTrue(listing["products"])
		detail = tools.product_details(product=listing["products"][0]["name"])
		self.assertTrue(detail["product_name"])
		self.assertTrue(tools.stock_levels(low_only=True)["total"] >= 0)
		self.assertIsInstance(tools.list_discounts(), list)
		self.assertIn("enable_cod", tools.store_settings())
		self.assertTrue(tools.setup_progress())

	def test_tool_arguments_are_validated(self):
		with self.assertRaises(Exception):
			tools.set_stock(item_code="SHOP-DEMO-003", qty="not a number")

	def test_update_product_preserves_untouched_fields(self):
		before = tools.product_details(product="ceramic-mug")
		tools.update_product(product="ceramic-mug", short_description="Temporary copy for tests")
		after = tools.product_details(product="ceramic-mug")
		self.assertEqual(after["short_description"], "Temporary copy for tests")
		self.assertEqual(after["price"], before["price"])
		self.assertEqual(after["compare_at_price"], before["compare_at_price"])
		self.assertEqual(len(after["images"]), len(before["images"]))
		tools.update_product(product="ceramic-mug", short_description=before["short_description"])

	def test_agent_status_reports_readiness(self):
		if "flow" not in frappe.get_installed_apps():
			self.skipTest("flow is not installed")
		status = agent_setup.get_agent_status()
		self.assertIn("ready", status)
		if not status["ready"]:
			self.assertIn(status["reason"], ("no_model", "not_installed"))
