import frappe
from frappe.tests import IntegrationTestCase

from shop.api import fulfillment as fulfillment_api
from shop.fulfillment import service
from shop.fulfillment.provider import available, get_provider
from shop.storefront import cart, checkout

BUYER = {"email": "fulfil-buyer@example.com", "full_name": "Fulfil Buyer"}
ADDRESS = {
	"address_line1": "4 Warehouse Way",
	"city": "Bengaluru",
	"state": "Karnataka",
	"country": "India",
	"pincode": "560001",
}


class TestFulfillment(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		if hasattr(frappe.local, "request"):
			del frappe.local.request

	def place_order(self):
		cart.add_item("SHOP-DEMO-003")
		return checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]

	def test_providers_are_discoverable(self):
		keys = {entry["key"] for entry in available()}
		self.assertIn("manual", keys)
		self.assertIn("amazon_mcf", keys)
		manual = next(entry for entry in available() if entry["key"] == "manual")
		self.assertTrue(manual["configured"])

	def test_amazon_reports_missing_setup_instead_of_failing(self):
		amazon = next(entry for entry in available() if entry["key"] == "amazon_mcf")
		self.assertFalse(amazon["configured"])
		self.assertTrue(amazon["hint"])

	def test_send_sync_and_ship_through_manual_provider(self):
		order = self.place_order()
		name = service.send(order, "manual")
		record = service.summary(name)
		self.assertEqual(record["status"], "Accepted")
		self.assertEqual(record["provider_label"], "Ship it yourself")
		self.assertTrue(record["items"])
		shipped = fulfillment_api.mark_shipped(name, carrier="Delhivery", tracking_number="TRACK123")
		self.assertEqual(shipped["status"], "Shipped")
		self.assertEqual(shipped["carrier"], "Delhivery")
		self.assertIn("TRACK123", shipped["tracking_url"])
		self.assertTrue(shipped["shipped_on"])

	def test_shipping_files_the_delivery_in_erpnext(self):
		order = self.place_order()
		name = service.send(order, "manual")
		fulfillment_api.mark_shipped(name, carrier="DTDC", tracking_number="D-1")
		self.assertGreaterEqual(frappe.db.get_value("Sales Order", order, "per_delivered"), 100)

	def test_one_open_shipment_per_order(self):
		order = self.place_order()
		service.send(order, "manual")
		with self.assertRaises(frappe.ValidationError):
			service.send(order, "manual")

	def test_cancelled_shipment_frees_the_order(self):
		order = self.place_order()
		name = service.send(order, "manual")
		service.cancel(name)
		self.assertEqual(service.summary(name)["status"], "Cancelled")
		self.assertTrue(service.send(order, "manual"))

	def test_order_lookup_returns_latest(self):
		order = self.place_order()
		service.send(order, "manual")
		self.assertEqual(service.for_order(order)["sales_order"], order)

	def test_unknown_provider_is_rejected(self):
		order = self.place_order()
		with self.assertRaises(frappe.ValidationError):
			service.send(order, "does-not-exist")

	def test_amazon_maps_provider_statuses(self):
		from shop.fulfillment.providers.amazon import STATUS_MAP

		self.assertEqual(STATUS_MAP["COMPLETE"], "Delivered")
		self.assertEqual(STATUS_MAP["CANCELLED"], "Cancelled")
		self.assertEqual(STATUS_MAP["UNFULFILLABLE"], "Failed")
		self.assertEqual(get_provider("amazon_mcf").label, "Amazon Multi-Channel Fulfillment")

	def enable_auto_send(self):
		previous = frappe.db.get_single_value("Shop Settings", "fulfillment_provider")
		frappe.db.set_single_value(
			"Shop Settings", {"auto_send_to_fulfillment": 1, "fulfillment_provider": "manual"}
		)
		frappe.clear_cache(doctype="Shop Settings")
		self.addCleanup(
			frappe.db.set_single_value,
			"Shop Settings",
			{"auto_send_to_fulfillment": 0, "fulfillment_provider": previous},
		)

	def test_paid_orders_ship_themselves_when_the_store_asks(self):
		self.enable_auto_send()
		order = self.place_order()
		from shop.api.orders import mark_paid

		mark_paid(order)
		record = service.for_order(order)
		self.assertIsNotNone(record)
		self.assertEqual(record["status"], "Accepted")

	def test_shopper_progress_follows_payment_and_shipping(self):
		from shop.api.orders import mark_paid
		from shop.storefront import orders as store_orders

		order = self.place_order()
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		summary = store_orders.get_order_summary(order, token)
		self.assertEqual([stage["done"] for stage in summary["progress"]], ["true", "false", "false", "false"])
		self.assertIsNone(summary["shipment"])
		self.assertEqual(summary["awaiting_shipment"], "true")

		mark_paid(order)
		record = service.for_order(order)
		name = record["name"] if record else service.send(order, "manual")
		fulfillment_api.mark_shipped(name, carrier="Delhivery", tracking_number="PRG-1")
		summary = store_orders.get_order_summary(order, token)
		self.assertEqual([stage["done"] for stage in summary["progress"]], ["true", "true", "true", "false"])
		self.assertEqual(summary["shipment"]["line"], "Delhivery · PRG-1")
		self.assertIn("PRG-1", summary["shipment"]["tracking_url"])
		self.assertIsNone(summary["awaiting_shipment"])

	def test_orders_are_not_sent_twice_by_the_automatic_route(self):
		self.enable_auto_send()
		order = self.place_order()
		service.send(order, "manual")
		service.auto_send(order)
		self.assertEqual(frappe.db.count("Shop Fulfillment", {"sales_order": order}), 1)
