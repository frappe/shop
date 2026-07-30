import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import cart, checkout, orders

BUYER = {"email": "jane@example.com", "full_name": "Jane Doe", "phone": "9999999999"}
ADDRESS = {
	"address_line1": "12 Lake View Road",
	"city": "Bengaluru",
	"state": "Karnataka",
	"country": "India",
	"pincode": "560001",
}


class TestCheckout(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		if hasattr(frappe.local, "request"):
			del frappe.local.request

	def test_place_order_cod(self):
		cart.add_item("SHOP-DEMO-003", qty=2)
		result = checkout.place_order(customer=BUYER, address=ADDRESS, payment_method="cod")
		sales_order = frappe.get_doc("Sales Order", result["sales_order"])
		self.assertEqual(sales_order.docstatus, 1)
		self.assertEqual(sales_order.items[0].item_code, "SHOP-DEMO-003")
		self.assertEqual(sales_order.items[0].qty, 2)
		converted = frappe.get_doc("Shop Cart", {"sales_order": sales_order.name})
		self.assertEqual(converted.status, "Converted")
		customer = frappe.db.get_value("Customer", sales_order.customer, "customer_name")
		self.assertEqual(customer, "Jane Doe")

	def test_customer_reused_on_second_order(self):
		cart.add_item("SHOP-DEMO-003")
		first = checkout.place_order(customer=BUYER, address=ADDRESS)
		cart.add_item("SHOP-DEMO-004")
		second = checkout.place_order(customer=BUYER, address=ADDRESS)
		customers = {
			frappe.db.get_value("Sales Order", order["sales_order"], "customer")
			for order in (first, second)
		}
		self.assertEqual(len(customers), 1)

	def test_empty_cart_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			checkout.place_order(customer=BUYER, address=ADDRESS)

	def test_guest_order_summary_via_token(self):
		cart.add_item("SHOP-DEMO-003")
		result = checkout.place_order(customer=BUYER, address=ADDRESS)
		token = frappe.db.get_value(
			"Shop Cart", {"sales_order": result["sales_order"]}, "token"
		)
		summary = orders.get_order_summary(result["sales_order"], token)
		self.assertEqual(summary["items"][0]["item_code"], "SHOP-DEMO-003")
		with self.assertRaises(frappe.PermissionError):
			orders.get_order_summary(result["sales_order"], "wrong-token")

	def test_confirmation_email_queued(self):
		if not (frappe.conf.mail_server or frappe.db.exists("Email Account", {"default_outgoing": 1})):
			self.skipTest("no outgoing email configured")
		cart.add_item("SHOP-DEMO-003")
		result = checkout.place_order(customer=BUYER, address=ADDRESS)
		self.assertTrue(
			frappe.db.exists(
				"Email Queue",
				{"reference_doctype": "Sales Order", "reference_name": result["sales_order"]},
			)
		)

	def test_out_of_stock_rejected(self):
		cart.add_item("SHOP-DEMO-003", qty=9999)
		with self.assertRaises(frappe.ValidationError):
			checkout.place_order(customer=BUYER, address=ADDRESS)
