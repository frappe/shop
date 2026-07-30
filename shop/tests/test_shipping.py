import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import cart, checkout, orders

BUYER = {"email": "shipping-buyer@example.com", "full_name": "Shipping Buyer"}
ADDRESS = {"address_line1": "8 Freight Road", "city": "Bengaluru", "country": "India"}


class TestShipping(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		if hasattr(frappe.local, "request"):
			del frappe.local.request
		self.settings = frappe.get_doc("Shop Settings")
		self.original = (
			self.settings.flat_shipping_rate,
			self.settings.free_shipping_above,
			self.settings.shipping_account,
		)
		self.account = frappe.db.get_value(
			"Account", {"company": self.settings.company, "is_group": 0, "root_type": "Income"}, "name"
		)

	def tearDown(self):
		rate, threshold, account = self.original
		frappe.db.set_single_value(
			"Shop Settings",
			{"flat_shipping_rate": rate, "free_shipping_above": threshold, "shipping_account": account},
		)
		frappe.clear_cache(doctype="Shop Settings")

	def configure(self, rate, threshold=0):
		frappe.db.set_single_value(
			"Shop Settings",
			{"flat_shipping_rate": rate, "free_shipping_above": threshold, "shipping_account": self.account},
		)
		frappe.clear_cache(doctype="Shop Settings")

	def test_no_charge_without_account(self):
		frappe.db.set_single_value("Shop Settings", {"flat_shipping_rate": 99, "shipping_account": None})
		frappe.clear_cache(doctype="Shop Settings")
		cart.add_item("SHOP-DEMO-003")
		payload = cart.get_cart()
		self.assertEqual(payload["shipping"], 0)
		self.assertEqual(payload["formatted_shipping"], "Free")

	def test_flat_rate_added_to_cart_and_order(self):
		self.configure(rate=49)
		cart.add_item("SHOP-DEMO-003")
		payload = cart.get_cart()
		self.assertEqual(payload["shipping"], 49)
		self.assertEqual(payload["total"], payload["subtotal"] + 49)
		result = checkout.place_order(customer=BUYER, address=ADDRESS)
		order = frappe.get_doc("Sales Order", result["sales_order"])
		self.assertEqual(order.grand_total, order.total + 49)
		summary = orders.get_order_summary(
			order.name, frappe.db.get_value("Shop Cart", {"sales_order": order.name}, "token")
		)
		self.assertNotEqual(summary["formatted_shipping"], "Free")

	def test_free_above_threshold(self):
		self.configure(rate=49, threshold=500)
		cart.add_item("SHOP-DEMO-003")
		payload = cart.get_cart()
		self.assertEqual(payload["shipping"], 0)
		self.assertEqual(payload["formatted_shipping"], "Free")
