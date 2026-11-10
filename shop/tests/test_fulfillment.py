from contextlib import contextmanager
from io import BytesIO
from typing import ClassVar
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from pypdf import PdfWriter

from shop.api import fulfillment as fulfillment_api
from shop.fulfillment import service
from shop.fulfillment.provider import FulfillmentProvider, available, get_provider
from shop.fulfillment.provider import registry as original_registry
from shop.storefront import cart, checkout
from shop.tests.utils import fresh_request, sellable

BUYER = {"email": "fulfil-buyer@example.com", "full_name": "Fulfil Buyer"}
ADDRESS = {
	"address_line1": "4 Warehouse Way",
	"city": "Bengaluru",
	"state": "Karnataka",
	"country": "India",
	"pincode": "560001",
}


def blank_pdf() -> bytes:
	writer = PdfWriter()
	writer.add_blank_page(288, 432)
	buffer = BytesIO()
	writer.write(buffer)
	return buffer.getvalue()


LABEL = blank_pdf()


class CourierProvider(FulfillmentProvider):
	"""A provider that books a courier and prints its label, keeping what it did in `booked`."""

	key = "test_courier"
	label = "Test Courier"
	booked: ClassVar[dict] = {}

	def create_shipment(self, order, items, fulfillment=None) -> dict:
		order.check_permission("write")  # as ERPNext's own Delivery Note and Shipment code does
		return {"status": "Accepted", "external_id": f"PARCEL-{order.name}"}

	def fetch_status(self, fulfillment) -> dict:
		return {"status": fulfillment.status}

	def cancel(self, fulfillment) -> dict:
		frappe.get_doc("Sales Order", fulfillment.sales_order).check_permission("write")
		return {"status": "Cancelled"}

	def courier(self, fulfillment) -> dict:
		state = self.booked.get(fulfillment.name)
		return {
			"booked": bool(state),
			"provider": "Test Courier" if state else None,
			"service": state["service"] if state else None,
			"amount": 12.5 if state else None,
			"currency": "INR",
			"labels": len(self.labels(fulfillment)),
			"can_book": not state,
			"can_print_label": bool(state),
		}

	def courier_services(self, fulfillment) -> list[dict]:
		return [
			{"id": "fast", "provider": "Test Courier", "service": "Fast", "amount": 12.5, "currency": "INR"},
			{"id": "slow", "provider": "Test Courier", "service": "Slow", "amount": 6, "currency": "INR"},
		]

	def book_courier(self, fulfillment, service_id: str) -> dict:
		if fulfillment.name in self.booked:
			frappe.throw("Already booked")
		self.booked[fulfillment.name] = {"service": service_id, "labels": []}
		return {"status": "Accepted", "carrier": "Test Courier"}

	def print_label(self, fulfillment) -> dict:
		state = self.booked[fulfillment.name]
		if not state["labels"]:
			label = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"label_{fulfillment.name}.pdf",
					"content": LABEL,
					"attached_to_doctype": "Shop Fulfillment",
					"attached_to_name": fulfillment.name,
					"is_private": 1,
				}
			).insert(ignore_permissions=True)
			state["labels"].append(label.file_url)
			# a provider may bring the fulfillment up to date as the label is printed
			frappe.get_doc("Shop Fulfillment", fulfillment.name).save(ignore_permissions=True)
		return {"status": "Accepted", "tracking_number": "TC-1", "files": list(state["labels"])}

	def labels(self, fulfillment) -> list[str]:
		state = self.booked.get(fulfillment.name)
		return list(state["labels"]) if state else []


@contextmanager
def with_courier():
	providers = {**original_registry(), "test_courier": "shop.tests.test_fulfillment.CourierProvider"}
	# what a booking or a label commits stays in the test's transaction
	with patch("shop.fulfillment.provider.registry", return_value=providers), patch("frappe.db.commit"):
		yield


class TestFulfillment(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()

	def place_order(self):
		sellable("SHOP-DEMO-003", 5)
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

	def test_a_late_update_doesnt_move_a_shipped_parcel_back(self):
		order = self.place_order()
		name = service.send(order, "manual")
		fulfillment = frappe.get_doc("Shop Fulfillment", name)
		with patch.object(service, "notify_customer") as notify:
			service.apply_result(fulfillment, {"status": "Shipped"})
			service.apply_result(fulfillment, {"status": "Accepted"})
			service.apply_result(fulfillment, {"status": "Shipped"})
		self.assertEqual(fulfillment.status, "Shipped")
		# the customer is told once
		self.assertEqual(notify.call_count, 1)

	def test_amazon_maps_provider_statuses(self):
		from shop.fulfillment.providers.amazon import STATUS_MAP, status_key

		# Amazon's schema and its examples spell statuses differently
		for status in ("Complete", "COMPLETE", "CompletePartialled", "COMPLETE_PARTIALLED"):
			self.assertEqual(STATUS_MAP[status_key(status)], "Shipped")
		self.assertEqual(STATUS_MAP[status_key("Cancelled")], "Cancelled")
		self.assertEqual(STATUS_MAP[status_key("UNFULFILLABLE")], "Failed")
		self.assertEqual(get_provider("amazon_mcf").label, "Amazon Multi-Channel Fulfillment")

	def test_amazon_requests_follow_the_selling_partner_api(self):
		from shop.fulfillment.providers import amazon

		order = frappe.get_doc("Sales Order", self.place_order())
		settings = frappe._dict(
			displayable_org_name="Test Store", shipping_speed="Standard", marketplace_id="M1"
		)
		sent = []
		with (
			patch.object(
				amazon.AmazonProvider, "__init__", lambda provider: setattr(provider, "settings", settings)
			),
			patch.object(
				amazon.AmazonProvider,
				"request",
				lambda provider, *args, **kwargs: (args[0] != "GET" and sent.append(args)) or {},
			),
		):
			provider = amazon.AmazonProvider()
			result = provider.create_shipment(order, [{"item_code": "SHOP-DEMO-003", "qty": 2.0}] * 2)
			method, path, payload = sent[0]
			self.assertEqual((method, path), ("POST", "/fba/outbound/2020-07-01/fulfillmentOrders"))
			self.assertEqual(payload["destinationAddress"]["countryCode"], "IN")
			self.assertNotIn("", payload["destinationAddress"].values())
			self.assertEqual(
				[item["sellerFulfillmentOrderItemId"] for item in payload["items"]],
				["1-SHOP-DEMO-003", "2-SHOP-DEMO-003"],
			)
			self.assertEqual(result["external_id"], order.name)

			# sent again after a cancelled attempt, the order needs an ID Amazon hasn't seen
			frappe.get_doc(
				{
					"doctype": "Shop Fulfillment",
					"sales_order": order.name,
					"provider": "amazon_mcf",
					"status": "Cancelled",
					"external_id": order.name,
				}
			).insert(ignore_permissions=True)
			self.assertEqual(provider.create_shipment(order, [])["external_id"], f"{order.name}-2")

		# the first request timed out after Amazon took it: sending again follows that order
		taken = {"payload": {"fulfillmentOrder": {"fulfillmentOrderStatus": "RECEIVED"}}}
		with (
			patch.object(
				amazon.AmazonProvider, "__init__", lambda provider: setattr(provider, "settings", settings)
			),
			patch.object(amazon.AmazonProvider, "request", return_value=taken) as request,
		):
			again = amazon.AmazonProvider().create_shipment(
				frappe.get_doc("Sales Order", self.place_order()), []
			)
		self.assertEqual(again["status"], "Accepted")
		self.assertEqual([call.args[0] for call in request.call_args_list], ["GET"])

		shipped = {
			"payload": {
				"fulfillmentOrder": {"fulfillmentOrderStatus": "COMPLETE"},
				"fulfillmentShipments": [
					{
						"fulfillmentShipmentStatus": "SHIPPED",
						"fulfillmentShipmentPackage": [{"carrierCode": "UPS", "trackingNumber": "1Z1"}],
					}
				],
			}
		}
		with (
			patch.object(
				amazon.AmazonProvider, "__init__", lambda provider: setattr(provider, "settings", settings)
			),
			patch.object(amazon.AmazonProvider, "request", return_value=shipped),
		):
			status = amazon.AmazonProvider().fetch_status(frappe._dict(external_id=order.name))
			self.assertEqual((status["status"], status["tracking_number"]), ("Shipped", "1Z1"))
			shipped["payload"]["fulfillmentShipments"][0]["fulfillmentShipmentPackage"][0][
				"deliveryInformation"
			] = {}
			self.assertEqual(
				amazon.AmazonProvider().fetch_status(frappe._dict(external_id="x"))["status"], "Shipped"
			)
			shipped["payload"]["fulfillmentShipments"][0]["fulfillmentShipmentPackage"][0][
				"deliveryInformation"
			] = {"deliveryDocumentList": []}
			self.assertEqual(
				amazon.AmazonProvider().fetch_status(frappe._dict(external_id="x"))["status"], "Delivered"
			)

	def enable_auto_send(self):
		from shop.storefront.stock import primary_warehouse
		from shop.tests.utils import use_locations

		use_locations(
			self, {"warehouse": primary_warehouse(), "fulfillment_provider": "manual", "auto_send": 1}
		)

	def test_paid_orders_ship_themselves_when_the_store_asks(self):
		self.enable_auto_send()
		order = self.place_order()
		from shop.api.orders import mark_paid

		with patch("frappe.enqueue") as enqueue:
			mark_paid(order)
		self.assertEqual(enqueue.call_args.kwargs["order_name"], order)
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertIsNone(service.for_order(order))
		service.send_paid_order(order)
		record = service.for_order(order)
		self.assertIsNotNone(record)
		self.assertEqual(record["status"], "Accepted")

	def test_shopper_progress_follows_payment_and_shipping(self):
		from shop.api.orders import mark_paid
		from shop.storefront import orders as store_orders

		order = self.place_order()
		token = frappe.db.get_value("Shop Cart", {"sales_order": order}, "token")
		summary = store_orders.get_order_summary(order, token)
		self.assertEqual(
			[stage["done"] for stage in summary["progress"]], ["true", "false", "false", "false"]
		)
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

	def test_a_provider_failure_keeps_the_failure_and_undoes_its_work(self):
		from shop.fulfillment.providers.manual import ManualProvider

		self.enable_auto_send()
		order = self.place_order()

		def half_done(provider, sales_order, items):
			frappe.get_doc("Sales Order", sales_order.name).add_comment("Info", "half done")
			frappe.throw("The provider is down")

		with patch.object(ManualProvider, "create_shipment", half_done):
			service.send_paid_order(order)
		record = service.for_order(order)
		self.assertEqual(record["status"], "Failed")
		self.assertIn("The provider is down", record["error"])
		self.assertFalse(frappe.db.exists("Comment", {"reference_name": order, "content": "half done"}))

	def test_orders_are_not_sent_twice_by_the_automatic_route(self):
		self.enable_auto_send()
		order = self.place_order()
		name = service.send(order, "manual")
		service.send_paid_order(order)
		self.assertEqual(frappe.db.count("Shop Fulfillment", {"sales_order": order}), 1)

		# nor again once that shipment is cancelled, delivered or the order closed: staff decide
		frappe.db.set_value("Shop Fulfillment", name, "status", "Cancelled")
		service.send_paid_order(order)
		self.assertEqual(frappe.db.count("Shop Fulfillment", {"sales_order": order}), 1)

	def test_staff_book_a_courier_and_print_its_label(self):
		order = self.place_order()
		with with_courier():
			name = service.send(order, "test_courier")
			courier = service.summary(name)["courier"]
			self.assertEqual((courier["booked"], courier["can_book"], courier["labels"]), (False, True, 0))
			services = fulfillment_api.get_courier_services(name)
			self.assertEqual([row["id"] for row in services], ["fast", "slow"])
			self.assertTrue(all(row["formatted_amount"] for row in services))

			booked = fulfillment_api.book_courier(name, "fast")
			self.assertEqual(booked["courier"]["service"], "fast")
			self.assertEqual(booked["carrier"], "Test Courier")
			self.assertTrue(booked["courier"]["formatted_amount"])
			with self.assertRaises(frappe.ValidationError):
				fulfillment_api.book_courier(name, "slow")

			printed = fulfillment_api.print_label(name)
			self.assertEqual(len(printed["labels"]), 1)
			self.assertEqual(printed["fulfillment"]["tracking_number"], "TC-1")
			self.assertEqual(printed["fulfillment"]["courier"]["labels"], 1)
			# printed again, the label isn't bought again
			fulfillment_api.print_label(name)
			self.assertEqual(len(CourierProvider.booked[name]["labels"]), 1)

			fulfillment_api.label(name, 0)
			self.assertEqual(frappe.local.response.type, "pdf")
			self.assertEqual(frappe.local.response.filecontent, LABEL)
			with self.assertRaises(frappe.DoesNotExistError):
				fulfillment_api.label(name, 1)

	def test_only_staff_book_couriers_and_open_labels(self):
		order = self.place_order()
		with with_courier():
			name = service.send(order, "test_courier")
			fulfillment_api.book_courier(name, "fast")
			fulfillment_api.print_label(name)
			frappe.set_user(BUYER["email"])
			try:
				for call in (
					lambda: fulfillment_api.get_courier_services(name),
					lambda: fulfillment_api.book_courier(name, "slow"),
					lambda: fulfillment_api.print_label(name),
					lambda: fulfillment_api.label(name, 0),
				):
					self.assertRaises(frappe.PermissionError, call)
			finally:
				frappe.set_user("Administrator")

	def test_a_provider_that_books_no_courier_says_so(self):
		order = self.place_order()
		name = service.send(order, "manual")
		self.assertIsNone(service.summary(name)["courier"])
		for call in (
			lambda: fulfillment_api.get_courier_services(name),
			lambda: fulfillment_api.book_courier(name, "fast"),
			lambda: fulfillment_api.print_label(name),
		):
			self.assertRaises(frappe.ValidationError, call)

	def test_a_shop_manager_sends_ships_delivers_and_cancels_parcels(self):
		manager = "fulfil.manager@example.com"
		if not frappe.db.exists("User", manager):
			frappe.get_doc(
				{"doctype": "User", "email": manager, "first_name": "Fulfil", "roles": [{"role": "Shop Manager"}]}
			).insert(ignore_permissions=True)
		shipped = self.place_order()
		invoiced = self.place_order()
		frappe.set_user(manager)
		try:
			name = fulfillment_api.send_order(shipped, "manual")["name"]
			fulfillment_api.sync_fulfillment(name)
			self.assertEqual(fulfillment_api.mark_shipped(name, "Courier", "C-1")["status"], "Shipped")
			self.assertEqual(fulfillment_api.mark_delivered(name)["status"], "Delivered")

			name = fulfillment_api.send_order(invoiced, "manual")["name"]
			fulfillment_api.mark_shipped(name)
			frappe.set_user("Administrator")
			from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

			make_sales_invoice(invoiced).insert().submit()
			frappe.set_user(manager)
			self.assertEqual(fulfillment_api.cancel_fulfillment(name)["status"], "Cancelled")
		finally:
			frappe.set_user("Administrator")

	def test_a_shop_manager_uses_a_provider_that_needs_desk_permissions(self):
		manager = "fulfil.manager@example.com"
		if not frappe.db.exists("User", manager):
			frappe.get_doc(
				{"doctype": "User", "email": manager, "first_name": "Fulfil", "roles": [{"role": "Shop Manager"}]}
			).insert(ignore_permissions=True)
		order = self.place_order()
		with with_courier():
			frappe.set_user(manager)
			try:
				name = fulfillment_api.send_order(order, "test_courier")["name"]
				self.assertTrue(fulfillment_api.get_courier_services(name))
				fulfillment_api.book_courier(name, "fast")
				self.assertEqual(len(fulfillment_api.print_label(name)["labels"]), 1)
				fulfillment_api.label(name, 0)
				self.assertEqual(frappe.local.response.type, "pdf")
				self.assertEqual(fulfillment_api.cancel_fulfillment(name)["status"], "Cancelled")
				self.assertEqual(frappe.session.user, manager)
			finally:
				frappe.set_user("Administrator")
