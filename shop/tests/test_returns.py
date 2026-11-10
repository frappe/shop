from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from shop.api import fulfillment as fulfillment_api
from shop.api import returns as returns_api
from shop.fulfillment import service
from shop.storefront import cart, checkout, returns
from shop.tests.utils import fresh_request

BUYER = {"email": "returns-buyer@example.com", "full_name": "Returns Buyer"}
ADDRESS = {
	"address_line1": "9 Return Road",
	"city": "Bengaluru",
	"state": "Karnataka",
	"country": "India",
	"pincode": "560001",
}


class TestReturns(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()

	def shipped_order(self):
		cart.add_item("SHOP-DEMO-003")
		order = checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		name = service.send(order, "manual")
		fulfillment_api.mark_shipped(name, carrier="Delhivery", tracking_number="RTN-1")
		return order, token

	def test_guest_requests_a_return_with_the_order_token(self):
		order, token = self.shipped_order()
		result = returns.create_request(
			order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Wrong size", token=token
		)
		self.assertEqual(result["status"], "Requested")
		request = frappe.get_doc("Shop Return Request", result["name"])
		self.assertEqual(request.item_name, "Ceramic Mug")
		self.assertEqual(request.customer, frappe.db.get_value("Sales Order", order, "customer"))

	def test_wrong_token_is_rejected(self):
		order, _token = self.shipped_order()
		with self.assertRaises(frappe.PermissionError):
			returns.create_request(
				order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="x", token="wrong"
			)

	def test_the_return_window_is_the_stores_setting(self):
		days = frappe.db.get_single_value("Shop Settings", "return_window_days")
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "return_window_days", days)
		frappe.db.set_single_value("Shop Settings", "return_window_days", 30)
		frappe.clear_cache(doctype="Shop Settings")
		self.assertEqual(returns.returns_note(), "30-day returns")
		frappe.db.set_single_value("Shop Settings", "return_window_days", 0)
		frappe.clear_cache(doctype="Shop Settings")
		self.assertIsNone(returns.returns_note())

	def test_unshipped_orders_are_not_returnable(self):
		cart.add_item("SHOP-DEMO-004")
		order = checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		with self.assertRaises(frappe.ValidationError):
			returns.create_request(
				order=order, item_code="SHOP-DEMO-004", request_type="Return", reason="x", token=token
			)

	def test_an_order_handed_to_a_courier_is_returnable_once_it_ships(self):
		cart.add_item("SHOP-DEMO-004")
		order = checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		name = service.send(order, "manual")
		# booked with the courier (the stock may already be delivered in ERPNext), not picked up yet
		frappe.db.set_value("Shop Fulfillment", name, "status", "Accepted")
		self.assertFalse(returns.summary(order)["eligible"])
		with self.assertRaisesRegex(frappe.ValidationError, "once the order has shipped"):
			returns.create_request(
				order=order, item_code="SHOP-DEMO-004", request_type="Return", reason="x", token=token
			)
		fulfillment_api.mark_shipped(name, carrier="Delhivery", tracking_number="RTN-2")
		self.assertTrue(returns.summary(order)["eligible"])

	def test_a_cancelled_shipment_is_not_returnable(self):
		cart.add_item("SHOP-DEMO-004")
		order = checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]
		name = service.send(order, "manual")
		service.cancel(name)
		self.assertFalse(returns.summary(order)["eligible"])

	def test_one_open_request_per_item(self):
		order, token = self.shipped_order()
		returns.create_request(
			order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Wrong size", token=token
		)
		with self.assertRaises(frappe.ValidationError):
			returns.create_request(
				order=order,
				item_code="SHOP-DEMO-003",
				request_type="Replacement",
				reason="Again",
				token=token,
			)

	def test_only_what_hasnt_come_back_can_be_returned(self):
		order, token = self.shipped_order()
		for qty in (0, -1):
			with self.assertRaisesRegex(frappe.ValidationError, "how many"):
				returns.create_request(
					order=order,
					item_code="SHOP-DEMO-003",
					request_type="Return",
					reason="x",
					qty=qty,
					token=token,
				)
		created = returns.create_request(
			order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Chipped", token=token
		)
		frappe.db.set_value("Shop Return Request", created["name"], "status", "Completed")
		with self.assertRaisesRegex(frappe.ValidationError, "came back already"):
			returns.create_request(
				order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Again", token=token
			)

	def test_items_outside_the_order_are_rejected(self):
		order, token = self.shipped_order()
		with self.assertRaises(frappe.ValidationError):
			returns.create_request(
				order=order, item_code="SHOP-DEMO-008", request_type="Return", reason="x", token=token
			)

	def test_manager_resolves_the_request(self):
		order, token = self.shipped_order()
		created = returns.create_request(
			order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Chipped", token=token
		)
		updated = returns_api.set_status(created["name"], "Approved", note="Pickup on Friday")
		self.assertEqual(updated["status"], "Approved")
		summary = returns.summary(order)
		self.assertEqual(summary["requests"][0]["status"], "Approved")
		self.assertEqual(summary["requests"][0]["resolution_note"], "Pickup on Friday")
		listed = returns_api.get_requests(status="Approved")
		self.assertIn(created["name"], [row.name for row in listed["requests"]])

	def test_a_return_on_a_paid_order_never_invoiced_is_still_owed_back(self):
		from shop.api import orders as orders_api

		cart.add_item("SHOP-DEMO-003", qty=1)
		order = checkout.place_order(customer=BUYER, address=ADDRESS, payment_method="bank")["sales_order"]
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		orders_api.mark_paid(order)
		name = service.send(order, "manual")
		fulfillment_api.mark_shipped(name, carrier="Delhivery", tracking_number="RTN-5")
		created = returns.create_request(
			order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Broken", qty=1, token=token
		)
		returns_api.set_status(created["name"], "Approved")
		with patch("frappe.sendmail"):
			result = returns_api.set_status(created["name"], "Completed")
		self.assertTrue(result["credit_note"])
		self.assertEqual(
			[row["credit_note"] for row in orders_api.get_order(order)["refunds_due"]],
			[result["credit_note"]],
		)

	def test_shipping_and_fees_arent_sent_back(self):
		from types import SimpleNamespace

		from shop.storefront import totals

		order = SimpleNamespace(name="SO-1", items=[frappe._dict(item_code="SHIP-FEE", qty=1)])
		with patch.object(totals, "is_charge_item", return_value=True), self.assertRaises(frappe.ValidationError):
			returns.validate_item(order, "SHIP-FEE", 1)

	def test_a_card_refund_records_what_the_gateway_paid_back(self):
		from shop.storefront import payment

		entry = MagicMock(paid_from_account_currency="USD", paid_amount=18.99, name="PE-1")
		gateway = MagicMock()
		gateway.refund.return_value = "re_test"
		request = frappe._dict(name="PR-1", payment_account="Stripe USD")
		with (
			patch.object(payment, "online_refund_controller", return_value=(request, gateway)),
			patch.object(payment, "owed", return_value=20.0),
			patch("erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry", return_value=entry),
			patch("frappe.db.get_value", return_value="USD"),
		):
			payment.refund_online("SO-1", "CN-1")
		# what left the gateway's account, with ERPNext's exchange gain or loss for the rest
		self.assertEqual(entry.paid_amount, 20.0)
		entry.set_amounts.assert_called_once()
		gateway.refund.assert_called_once_with("Payment Request", "PR-1", 20.0, "CN-1")

	def test_a_gateways_settings_are_found_for_its_refunds(self):
		from shop.storefront import payment

		if not frappe.db.exists("DocType", "PayPal Settings"):
			self.skipTest("the payments app isn't installed")
		# one settings record per gateway (Stripe), or one settings page named after it (PayPal)
		stripe = frappe.db.get_value("Payment Gateway", {"gateway_settings": "Stripe Settings"})
		if stripe:
			self.assertEqual(payment.gateway_controller(stripe).doctype, "Stripe Settings")
		if not frappe.db.exists("Payment Gateway", "PayPal"):
			frappe.get_doc({"doctype": "Payment Gateway", "gateway": "PayPal"}).insert(ignore_permissions=True)
		self.assertEqual(payment.gateway_controller("PayPal").doctype, "PayPal Settings")
		if not frappe.db.exists("Payment Gateway", "_Test No Settings"):
			frappe.get_doc({"doctype": "Payment Gateway", "gateway": "_Test No Settings"}).insert(
				ignore_permissions=True
			)
		self.assertIsNone(payment.gateway_controller("_Test No Settings"))

	def test_a_refund_says_which_gateway_it_goes_back_through(self):
		from shop.storefront import emails, payment, totals

		with patch.object(totals, "gateway_row", return_value=frappe._dict(label="PayPal", payment_gateway="PayPal")):
			self.assertEqual(payment.paid_through(frappe._dict(payment_gateway="PayPal")), "PayPal")
		# a gateway the store no longer offers is called by its name
		with patch.object(totals, "gateway_row", return_value=None):
			self.assertEqual(payment.paid_through(frappe._dict(payment_gateway="Stripe-Old")), "Stripe-Old")
		emails.ensure_templates()
		_subject, body = emails.render(
			"refund_sent", frappe._dict(name="SO-1"), amount="$10.00", to_card=True, gateway="PayPal"
		)
		self.assertIn("the way you paid (PayPal)", body)

	def test_a_refund_is_in_the_currency_the_customer_paid_in(self):
		from shop.storefront import payment

		note = frappe._dict(
			outstanding_amount=-150.0, currency="USD", party_account_currency="INR", conversion_rate=1.5
		)
		with patch("frappe.db.get_value", return_value=note):
			self.assertEqual(payment.owed("CN-1"), 100.0)
		with patch("frappe.db.get_value", return_value=frappe._dict(note, party_account_currency="USD")):
			self.assertEqual(payment.owed("CN-1"), 150.0)

	def test_completed_return_credits_and_staff_approve_the_card_refund(self):
		from shop.api import orders as orders_api
		from shop.storefront import payment

		cart.add_item("SHOP-DEMO-003", qty=2)
		order = checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		orders_api.mark_paid(order)
		payment.invoice_paid_order(frappe.get_doc("Sales Order", order))
		name = service.send(order, "manual")
		fulfillment_api.mark_shipped(name, carrier="Delhivery", tracking_number="RTN-3")
		created = returns.create_request(
			order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Broken", qty=1, token=token
		)
		returns_api.set_status(created["name"], "Approved")

		# a card payment: the order's gateway refunds it
		gateway = MagicMock()
		gateway.refund.return_value = "re_test_refund"
		paid_request = frappe._dict(name="PR-TEST", payment_gateway="Stripe", payment_account=None)
		real_get_doc = frappe.get_doc

		def get_doc(*args, **kwargs):
			if args and args[0] == "Payment Request":
				return paid_request
			if args and args[0] == "Payment Gateway":
				return frappe._dict(gateway_settings="Stripe Settings", gateway_controller="Test")
			if args and args[0] == "Stripe Settings":
				return gateway
			return real_get_doc(*args, **kwargs)

		with patch("frappe.sendmail") as sendmail:
			result = returns_api.set_status(created["name"], "Completed")
		self.assertEqual(frappe.db.get_value("Delivery Note", result["return_delivery_note"], "is_return"), 1)
		self.assertEqual(
			frappe.db.get_value("Delivery Note Item", {"parent": result["return_delivery_note"]}, "qty"), -1
		)
		credit_note = frappe.get_doc("Sales Invoice", result["credit_note"])
		self.assertTrue(credit_note.is_return)
		self.assertEqual(credit_note.items[0].qty, -1)
		subjects = [call.kwargs["subject"] for call in sendmail.call_args_list]
		self.assertIn(f"Your return for order {order} is complete", subjects)
		# nothing is paid back until staff approve the refund
		self.assertFalse(result["refund"])
		gateway.refund.assert_not_called()
		self.assertEqual(
			[row["credit_note"] for row in orders_api.get_order(order)["refunds_due"]], [credit_note.name]
		)

		owed = abs(flt(credit_note.outstanding_amount))
		with (
			patch(
				"frappe.db.get_value",
				side_effect=lambda *a, **k: "PR-TEST"
				if a and a[0] == "Payment Request"
				else real_get_value(*a, **k),
			),
			patch("frappe.get_doc", side_effect=get_doc),
			patch("frappe.sendmail") as sendmail,
		):
			orders_api.refund(order, credit_note.name, "card")
		self.assertEqual(
			gateway.refund.call_args.args[:3],
			("Payment Request", "PR-TEST", owed),
		)
		refund = frappe.db.get_value("Shop Return Request", created["name"], "refund")
		self.assertEqual(frappe.db.get_value("Payment Entry", refund, "docstatus"), 1)
		self.assertEqual(flt(frappe.db.get_value("Payment Entry", refund, "paid_amount")), owed)
		self.assertEqual(frappe.db.get_value("Payment Entry", refund, "reference_no"), "re_test_refund")
		self.assertEqual(frappe.db.get_value("Sales Invoice", credit_note.name, "outstanding_amount"), 0)
		subjects = [call.kwargs["subject"] for call in sendmail.call_args_list]
		self.assertIn(f"Your refund for order {order}", subjects)


real_get_value = frappe.db.get_value
