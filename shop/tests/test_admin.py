import frappe
from frappe.tests import IntegrationTestCase

from shop.api import analytics, carts, customers, discounts, inventory, orders, products, reviews, settings
from shop.storefront import cart as storefront_cart
from shop.storefront import checkout

BUYER = {"email": "admin-test-buyer@example.com", "full_name": "Admin Test Buyer"}
ADDRESS = {"address_line1": "11 Admin Way", "city": "Bengaluru", "country": "India"}


class TestAdminApi(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		if hasattr(frappe.local, "request"):
			del frappe.local.request

	def place_order(self):
		storefront_cart.add_item("SHOP-DEMO-003")
		return checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]

	def test_analytics_overview(self):
		self.place_order()
		overview = analytics.get_overview(days=7)
		self.assertGreater(overview["orders"], 0)
		self.assertEqual(len(overview["series"]), 7)
		self.assertTrue(overview["formatted_revenue"])
		self.assertTrue(overview["top_products"])

	def test_order_listing_and_payment_flow(self):
		name = self.place_order()
		listing = orders.get_orders(search=name)
		self.assertEqual(listing["orders"][0]["name"], name)
		self.assertEqual(listing["orders"][0]["payment_status"], "Unpaid")
		detail = orders.mark_paid(name)
		self.assertEqual(detail["payment_status"], "Paid")
		self.assertIn("Payment recorded", [event["label"] for event in detail["timeline"]])

	def test_fulfillment(self):
		name = self.place_order()
		detail = orders.fulfill(name)
		self.assertEqual(detail["fulfillment_status"], "Fulfilled")

	def test_product_lifecycle(self):
		created = products.create_product(
			product_name="Test Desk Lamp", price=1500, opening_stock=3, published=True
		)
		self.addCleanup(products.delete_product, created["name"])
		self.assertEqual(created["stock"], 3)
		self.assertEqual(created["price"], 1500)
		updated = products.save_product(
			{"name": created["name"], "price": 1200, "compare_at_price": 1800, "published": False}
		)
		self.assertEqual(updated["price"], 1200)
		self.assertFalse(updated["published"])
		listing = products.get_products(search="Test Desk Lamp")
		self.assertEqual(listing["products"][0]["name"], created["name"])

	def test_inventory_and_stock_adjustment(self):
		created = products.create_product(product_name="Test Stock Item", price=500, opening_stock=2)
		self.addCleanup(products.delete_product, created["name"])
		inventory.set_stock(created["item"], 12)
		rows = inventory.get_inventory(search="Test Stock Item")
		self.assertEqual(rows["items"][0]["stock"], 12)
		self.assertFalse(rows["items"][0]["low"])

	def test_customers(self):
		name = self.place_order()
		customer = frappe.db.get_value("Sales Order", name, "customer")
		listing = customers.get_customers(search=customer)
		self.assertTrue(listing["customers"])
		detail = customers.get_customer(customer)
		self.assertIn(name, [order["name"] for order in detail["orders"]])

	def test_reviews_moderation(self):
		listing = reviews.get_reviews(product="ceramic-mug")
		self.assertTrue(listing["reviews"])
		target = listing["reviews"][0]["name"]
		reviews.delete_review(target)
		self.assertFalse(frappe.db.exists("Shop Review", target))

	def test_coupon_management(self):
		discounts.save_coupon(
			{"coupon_code": "ADMINTEST15", "discount_type": "Percentage", "value": 15, "enabled": True}
		)
		coupon = next(c for c in discounts.get_coupons() if c["coupon_code"] == "ADMINTEST15")
		self.assertEqual(coupon["value_label"], "15.0% off")
		self.assertTrue(coupon["enabled"])
		discounts.set_enabled(coupon["name"], False)
		coupon = next(c for c in discounts.get_coupons() if c["coupon_code"] == "ADMINTEST15")
		self.assertFalse(coupon["enabled"])
		discounts.delete_coupon(coupon["name"])
		self.assertFalse(frappe.db.exists("Coupon Code", {"coupon_code": "ADMINTEST15"}))

	def test_carts_view(self):
		storefront_cart.add_item("SHOP-DEMO-004")
		listing = carts.get_carts()
		self.assertTrue(listing["carts"])
		self.assertTrue(listing["carts"][0]["item_count"])

	def test_settings_round_trip(self):
		original = settings.get_settings()
		settings.save_settings({"low_stock_threshold": 9, "flat_shipping_rate": 49})
		updated = settings.get_settings()
		self.assertEqual(updated["low_stock_threshold"], 9)
		self.assertEqual(updated["flat_shipping_rate"], 49)
		settings.save_settings(
			{
				"low_stock_threshold": original["low_stock_threshold"] or 5,
				"flat_shipping_rate": original["flat_shipping_rate"] or 0,
			}
		)
