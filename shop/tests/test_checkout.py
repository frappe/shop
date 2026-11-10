from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import cart, checkout, orders
from shop.tests.utils import fresh_request

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
		fresh_request()

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

	def test_the_buyers_po_number_and_note_go_on_the_order(self):
		cart.add_item("SHOP-DEMO-003")
		result = checkout.place_order(
			customer=BUYER,
			address=ADDRESS,
			payment_method="cod",
			po_no=" PO-7781 ",
			order_note="Leave at the <b>back</b> door",
		)
		order = frappe.get_doc("Sales Order", result["sales_order"])
		self.assertEqual(order.po_no, "PO-7781")
		self.assertEqual(order.shop_order_note, "Leave at the back door")

	def test_tax_template_is_applied_to_the_order(self):
		settings = frappe.get_doc("Shop Settings")
		template = frappe.db.get_value("Sales Taxes and Charges Template", {"company": settings.company})
		if not template:
			self.skipTest("no sales tax template for the shop company")
		frappe.db.set_single_value("Shop Settings", "tax_template", template)
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "tax_template", settings.tax_template)

		cart.add_item("SHOP-DEMO-003")
		result = checkout.place_order(customer=BUYER, address=ADDRESS)

		sales_order = frappe.get_doc("Sales Order", result["sales_order"])
		self.assertEqual(sales_order.taxes_and_charges, template)
		self.assertTrue(sales_order.taxes)
		self.assertGreater(sales_order.total_taxes_and_charges, 0)

	def test_customer_reused_on_second_order(self):
		cart.add_item("SHOP-DEMO-003")
		first = checkout.place_order(customer=BUYER, address=ADDRESS)
		cart.add_item("SHOP-DEMO-004")
		second = checkout.place_order(customer=BUYER, address=ADDRESS)
		customers = {
			frappe.db.get_value("Sales Order", order["sales_order"], "customer") for order in (first, second)
		}
		self.assertEqual(len(customers), 1)

	def test_empty_cart_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			checkout.place_order(customer=BUYER, address=ADDRESS)

	def test_guest_order_summary_via_token(self):
		cart.add_item("SHOP-DEMO-003")
		result = checkout.place_order(customer=BUYER, address=ADDRESS)
		token = frappe.db.get_value("Shop Cart", {"sales_order": result["sales_order"]}, "token")
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
		with self.assertRaisesRegex(frappe.ValidationError, "left in stock"):
			cart.add_item("SHOP-DEMO-003", qty=9999)
		# stock sold in the meantime
		cart.add_item("SHOP-DEMO-003")
		with (
			patch("shop.storefront.stock.get_stock", return_value={"SHOP-DEMO-003": 0}),
			self.assertRaisesRegex(frappe.ValidationError, "left in stock"),
		):
			checkout.place_order(customer=BUYER, address=ADDRESS)

	def test_prefill_empty_for_guests(self):
		frappe.set_user("Guest")
		try:
			prefill = checkout.checkout_prefill()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(prefill["email"], "")
		self.assertEqual(prefill["address_line1"], "")

	def test_prefill_returns_last_details_for_signed_in_customer(self):
		from shop import personas

		personas.ensure_shopper_account()
		cart.add_item("SHOP-DEMO-003")
		buyer = {"email": personas.SHOPPER["email"], "full_name": "Meera"}
		address = {**ADDRESS, "address_line1": "7 Prefill Park", "city": "Pune", "pincode": "411001"}
		checkout.place_order(customer=buyer, address=address)
		frappe.set_user(personas.SHOPPER["email"])
		try:
			prefill = checkout.checkout_prefill()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(prefill["email"], personas.SHOPPER["email"])
		self.assertEqual(prefill["address_line1"], "7 Prefill Park")
		self.assertEqual(prefill["city"], "Pune")
		self.assertEqual(prefill["pincode"], "411001")

	def test_repeat_address_is_reused_not_duplicated(self):
		from shop import personas

		personas.ensure_shopper_account()
		buyer = {"email": personas.SHOPPER["email"], "full_name": "Meera"}
		address = {**ADDRESS, "address_line1": "3 Dedup Drive"}
		cart.add_item("SHOP-DEMO-003")
		first = checkout.place_order(customer=buyer, address=address)
		cart.add_item("SHOP-DEMO-004")
		second = checkout.place_order(customer=buyer, address=address)
		names = {
			frappe.db.get_value("Sales Order", order["sales_order"], "shipping_address_name")
			for order in (first, second)
		}
		self.assertEqual(len(names), 1)
		frappe.set_user(personas.SHOPPER["email"])
		try:
			saved = checkout.saved_addresses()
		finally:
			frappe.set_user("Administrator")
		self.assertIn("3 Dedup Drive, Bengaluru, 560001", [row.get("line") for row in saved])
		self.assertEqual(saved[-1]["name"], "")

	def test_someone_signed_in_without_a_customer_cant_order_on_anothers_account(self):
		from shop import personas

		personas.ensure_shopper_account()
		member = {"email": personas.SHOPPER["email"], "full_name": "Meera"}
		# the member has a customer: staff took an order for them
		cart.add_item("SHOP-DEMO-003")
		checkout.place_order(customer=member, address=ADDRESS)
		stranger = "no-customer.user@example.com"
		if not frappe.db.exists("User", stranger):
			frappe.get_doc(
				{"doctype": "User", "email": stranger, "first_name": "Stranger", "user_type": "Website User"}
			).insert(ignore_permissions=True)
		frappe.set_user(stranger)
		self.addCleanup(frappe.set_user, "Administrator")
		fresh_request()
		cart.add_item("SHOP-DEMO-003")
		with self.assertRaisesRegex(frappe.ValidationError, "Please sign in"):
			checkout.place_order(customer=member, address=ADDRESS)

	def test_a_guest_holds_stock_for_few_unpaid_bank_orders(self):
		from shop.tests.utils import sellable

		sellable("SHOP-DEMO-003", 5)
		buyer = {"email": f"unpaid-{frappe.generate_hash(length=6)}@example.com", "full_name": "Una Paid"}
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")

		def guest_cart():
			fresh_request()
			frappe.db.delete("Shop Cart", {"status": "Active"})
			cart.add_item("SHOP-DEMO-003")
			token = frappe.db.get_value("Shop Cart", {"status": "Active"}, "token")
			frappe.local.request = frappe._dict(cookies={cart.CART_COOKIE: token})
			frappe.local.request_ip = "203.0.113.9"

		self.addCleanup(setattr, frappe.local, "request_ip", None)
		frappe.local.request_ip = "203.0.113.9"
		frappe.cache.delete(checkout.unpaid_orders_key())
		for _order in range(checkout.UNPAID_ORDERS_PER_CUSTOMER):
			guest_cart()
			checkout.place_order(customer=buyer, address=ADDRESS, payment_method="bank")
		guest_cart()
		with self.assertRaisesRegex(frappe.ValidationError, "waiting for a bank transfer"):
			checkout.place_order(customer=buyer, address=ADDRESS, payment_method="bank")

	def test_owner_views_order_without_token(self):
		from shop import personas

		personas.ensure_shopper_account()
		cart.add_item("SHOP-DEMO-003")
		result = checkout.place_order(
			customer={"email": personas.SHOPPER["email"], "full_name": "Meera"}, address=ADDRESS
		)
		with self.assertRaises(frappe.PermissionError):
			orders.get_order_summary(result["sales_order"])
		frappe.set_user(personas.SHOPPER["email"])
		try:
			summary = orders.get_order_summary(result["sales_order"])
			listed = orders.get_orders()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(summary["progress"][0], {"label": "Order placed", "done": "true"})
		self.assertEqual(summary["display_status"], "Processing")
		match = next(row for row in listed if row.name == result["sales_order"])
		self.assertEqual(match.url, f"/order-confirmation/{result['sales_order']}")
