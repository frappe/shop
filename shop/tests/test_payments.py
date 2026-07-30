import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import cart, checkout

BUYER = {"email": "payer@example.com", "full_name": "Pay Er", "phone": "9999900000"}
ADDRESS = {"address_line1": "9 Gateway Rd", "city": "Bengaluru", "country": "India", "pincode": "560002"}


class TestPayments(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		if hasattr(frappe.local, "request"):
			del frappe.local.request
		self.settings = frappe.get_doc("Shop Settings")
		self.gateway_account = frappe.db.get_value("Payment Gateway Account", {}, "name")

	def test_gateway_order_creates_payment_request(self):
		if not self.gateway_account:
			self.skipTest("no payment gateway account configured")
		frappe.db.set_single_value("Shop Settings", "payment_gateway_account", self.gateway_account)
		frappe.get_cached_doc("Shop Settings")
		cart.add_item("SHOP-DEMO-003")
		result = checkout.place_order(customer=BUYER, address=ADDRESS, payment_method="gateway")
		self.assertTrue(result.get("payment_url"))
		payment_request = frappe.get_doc(
			"Payment Request", {"reference_name": result["sales_order"], "docstatus": 1}
		)
		self.assertEqual(payment_request.reference_doctype, "Sales Order")

	def test_on_payment_authorized_marks_paid_and_redirects(self):
		if not self.gateway_account:
			self.skipTest("no payment gateway account configured")
		frappe.db.set_single_value("Shop Settings", "payment_gateway_account", self.gateway_account)
		frappe.get_cached_doc("Shop Settings")
		cart.add_item("SHOP-DEMO-004")
		result = checkout.place_order(customer=BUYER, address=ADDRESS, payment_method="gateway")
		payment_request = frappe.get_doc(
			"Payment Request", {"reference_name": result["sales_order"], "docstatus": 1}
		)
		redirect = payment_request.run_method("on_payment_authorized", "Completed")
		self.assertIn(f"/order-confirmation/{result['sales_order']}", redirect)
		self.assertTrue(
			frappe.db.exists(
				"Payment Entry Reference",
				{"reference_name": result["sales_order"], "docstatus": 1},
			)
		)
