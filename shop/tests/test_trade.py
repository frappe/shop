import frappe
from frappe.tests import IntegrationTestCase

from shop.api import admin, customers, trade


class TestTrade(IntegrationTestCase):
	def setUp(self):
		self.group = frappe.db.get_value("Customer Group", {"is_group": 0})
		previous = frappe.db.get_single_value("Shop Settings", "trade_customer_group")
		self.addCleanup(self.set_group, previous)
		self.set_group(self.group)
		self.customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "Trade Test Customer", "customer_group": self.group}
		).insert(ignore_permissions=True)

	def set_group(self, group):
		frappe.db.set_single_value("Shop Settings", "trade_customer_group", group)
		frappe.clear_cache(doctype="Shop Settings")

	def test_staff_make_and_end_a_trade_customer(self):
		terms = (
			frappe.db.get_value("Payment Terms Template", {})
			or frappe.get_doc(
				{
					"doctype": "Payment Terms Template",
					"template_name": "_Test Trade Net 20",
					"terms": [
						{
							"invoice_portion": 100,
							"credit_days_based_on": "Day(s) after invoice date",
							"credit_days": 20,
						}
					],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		other = frappe.db.get_value("Customer Group", {"is_group": 0, "name": ["!=", self.group]})
		self.customer.db_set("customer_group", other)
		with self.assertRaises(frappe.ValidationError):
			trade.make_trade_customer(self.customer.name, allow_on_account=1)
		status = trade.make_trade_customer(
			self.customer.name, payment_terms=terms, allow_on_account=1, credit_limit=500
		)
		self.assertTrue(status["is_trade"])
		self.assertEqual((status["payment_terms"], status["credit_limit"]), (terms, 500))
		self.assertEqual(customers.get_customer(self.customer.name)["trade"]["is_trade"], True)
		previous = frappe.db.get_single_value("Selling Settings", "customer_group")
		self.addCleanup(frappe.db.set_single_value, "Selling Settings", "customer_group", previous)
		frappe.db.set_single_value("Selling Settings", "customer_group", other)
		self.customer.db_set("default_price_list", frappe.db.get_value("Price List", {"selling": 1}))
		ended = trade.end_trade(self.customer.name)
		# none of what approval gave is left
		self.assertFalse(ended["allow_on_account"])
		self.assertFalse(ended["is_trade"])
		self.assertEqual((ended["payment_terms"], ended["credit_limit"]), (None, None))
		self.assertFalse(frappe.db.get_value("Customer", self.customer.name, "default_price_list"))

	def test_waiting_applications_only_with_trade_accounts(self):
		self.assertIsInstance(admin.get_dashboard()["trade_applications"], int)
		self.set_group(None)
		self.assertIsNone(admin.get_dashboard()["trade_applications"])
