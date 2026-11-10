import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import cart, checkout
from shop.tests.utils import fresh_request

BUYER = {"email": "payer@example.com", "full_name": "Pay Er", "phone": "9999900000"}
ADDRESS = {"address_line1": "9 Gateway Rd", "city": "Bengaluru", "country": "India", "pincode": "560002"}


class TestPayments(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()
		self.settings = frappe.get_doc("Shop Settings")
		# a Payment Request needs a gateway app's controller: the site's gateway account, if any
		self.gateway_account = frappe.db.get_value("Payment Gateway Account", {}, "name")
		self.original_gateways = [row.payment_gateway for row in self.settings.payment_gateways]

	def tearDown(self):
		self.use_gateway(*self.original_gateways)

	def use_gateway(self, *gateways):
		"""Checkout offers these Payment Gateways, or the one of the site's gateway account."""
		if not gateways:
			gateways = (
				frappe.db.get_value("Payment Gateway Account", self.gateway_account, "payment_gateway"),
			)
		settings = frappe.get_doc("Shop Settings")
		settings.payment_gateways = []
		for name in gateways:
			settings.append("payment_gateways", {"payment_gateway": name})
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")

	def test_gateway_order_creates_payment_request(self):
		if not self.gateway_account:
			self.skipTest("no payment gateway account configured")
		self.use_gateway()
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
		self.use_gateway()
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

	def test_an_empty_checkout_leads_back_to_the_order_waiting_for_payment(self):
		from unittest.mock import patch

		if not self.gateway_account:
			self.skipTest("no payment gateway account configured")
		self.use_gateway()
		cart.add_item("SHOP-DEMO-003")
		token = cart.find_cart().token
		result = checkout.place_order(customer=BUYER, address=ADDRESS, payment_method="gateway")
		with patch.object(cart, "request_token", return_value=token):
			waiting = checkout.get_checkout_summary()["waiting_order"]
			self.assertEqual(waiting["pay_url"], result["payment_url"])
			self.assertIn(result["sales_order"], waiting["note"])
			payment_request = frappe.get_doc(
				"Payment Request", {"reference_name": result["sales_order"], "docstatus": 1}
			)
			payment_request.run_method("on_payment_authorized", "Completed")
			self.assertIsNone(checkout.get_checkout_summary()["waiting_order"])

	def test_a_request_for_an_order_entered_in_desk_is_left_to_erpnext(self):
		from unittest.mock import patch

		from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

		if not self.gateway_account:
			self.skipTest("no payment gateway account configured")
		self.use_gateway()
		cart.add_item("SHOP-DEMO-004")
		store_order = frappe.get_doc(
			"Sales Order", checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]
		)
		desk_order = frappe.copy_doc(store_order)
		for field in ("shop_payment_method", "shop_access_token", "shop_payment_due"):
			if desk_order.meta.has_field(field):
				desk_order.set(field, None)
		desk_order.insert(ignore_permissions=True).submit()
		payment_request = make_payment_request(
			dt="Sales Order", dn=desk_order.name, submit_doc=1, mute_email=1, return_doc=1
		)
		with patch("shop.fulfillment.service.auto_send") as auto_send:
			self.assertIsNone(payment_request.run_method("on_payment_authorized", "Completed"))
		auto_send.assert_not_called()
		self.assertEqual(frappe.db.get_value("Payment Request", payment_request.name, "status"), "Paid")

	def test_an_online_order_paid_another_way_is_confirmed_and_reminders_say_what_happens(self):
		from unittest.mock import patch

		from shop.api.orders import mark_paid
		from shop.storefront import payment

		if not self.gateway_account:
			self.skipTest("no payment gateway account configured")
		self.use_gateway()
		cart.add_item("SHOP-DEMO-004")
		name = checkout.place_order(customer=BUYER, address=ADDRESS, payment_method="gateway")["sales_order"]
		order = frappe.get_doc("Sales Order", name)

		# the reminder only warns of cancelling when the store cancels unpaid orders
		previous = frappe.db.get_single_value("Shop Settings", "cancel_unpaid_orders")
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "cancel_unpaid_orders", previous)
		frappe.db.set_single_value("Shop Settings", "cancel_unpaid_orders", 0)
		with patch("shop.storefront.emails.send") as send:
			payment.remind(order)
		self.assertEqual(send.call_args.kwargs["due_date"], "")

		# staff record a bank payment for it: the customer is told it was received
		with patch.object(payment, "notify_paid") as notify_paid:
			mark_paid(name)
		notify_paid.assert_called_once()
