import frappe
from frappe.tests import IntegrationTestCase

from shop.api import fulfillment as fulfillment_api
from shop.api import returns as returns_api
from shop.fulfillment import service
from shop.storefront import cart, checkout, returns

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
		if hasattr(frappe.local, "request"):
			del frappe.local.request

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

	def test_unshipped_orders_are_not_returnable(self):
		cart.add_item("SHOP-DEMO-004")
		order = checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		with self.assertRaises(frappe.ValidationError):
			returns.create_request(
				order=order, item_code="SHOP-DEMO-004", request_type="Return", reason="x", token=token
			)

	def test_one_open_request_per_item(self):
		order, token = self.shipped_order()
		returns.create_request(
			order=order, item_code="SHOP-DEMO-003", request_type="Return", reason="Wrong size", token=token
		)
		with self.assertRaises(frappe.ValidationError):
			returns.create_request(
				order=order, item_code="SHOP-DEMO-003", request_type="Replacement", reason="Again", token=token
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
