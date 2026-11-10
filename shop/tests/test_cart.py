from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import cart, stock


class TestCart(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		clear_request()

	def tearDown(self):
		clear_request()

	def test_add_and_update(self):
		payload = cart.add_item("SHOP-DEMO-003")
		self.assertEqual(payload["item_count"], 1)
		payload = cart.add_item("SHOP-DEMO-003", qty=2)
		self.assertEqual(payload["item_count"], 3)
		payload = cart.set_qty("SHOP-DEMO-003", qty=1)
		self.assertEqual(payload["item_count"], 1)
		self.assertEqual(payload["items"][0]["slug"], "ceramic-mug")
		self.assertTrue(payload["formatted_total"])

	def test_a_left_cart_is_reminded_of_once_and_its_link_brings_it_back(self):
		frappe.db.set_single_value("Shop Settings", "cart_reminder_hours", 2)
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "cart_reminder_hours", 0)
		frappe.clear_document_cache("Shop Settings", "Shop Settings")
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		cart.add_item("SHOP-DEMO-003")
		token = frappe.db.get_value("Shop Cart", {"status": "Active"}, "token")
		set_request_cookie(token)
		frappe.local.request_ip = "203.0.113.10"
		self.addCleanup(setattr, frappe.local, "request_ip", None)
		cart.remember_email(" Left.Cart@Example.com ")
		frappe.set_user("Administrator")
		# reminders go out from the scheduler, with no request
		clear_request()
		name = frappe.db.get_value("Shop Cart", {"token": token})
		self.assertEqual(frappe.db.get_value("Shop Cart", name, "email"), "left.cart@example.com")

		# changed an hour ago: not yet
		hour_ago = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-1)
		frappe.db.set_value("Shop Cart", name, "last_active", hour_ago, update_modified=False)
		with patch("frappe.sendmail") as sendmail:
			cart.remind_left_carts()
		sendmail.assert_not_called()

		three_hours_ago = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-3)
		frappe.db.set_value("Shop Cart", name, "last_active", three_hours_ago, update_modified=False)
		with patch("frappe.sendmail") as sendmail:
			cart.remind_left_carts()
			cart.remind_left_carts()
		self.assertEqual(sendmail.call_count, 1)
		mail = sendmail.call_args.kwargs
		self.assertEqual(mail["recipients"], ["left.cart@example.com"])
		self.assertIn(f"restore={token}", mail["message"])
		self.assertIn("Ceramic Mug", mail["message"])

		# a new browser following the link gets the cart
		clear_request()
		frappe.local.request = frappe._dict(cookies={})
		frappe.set_user("Guest")
		with patch.object(cart, "set_cart_cookie") as set_cookie:
			cart.restore_cart(token)
		set_cookie.assert_called_once()
		self.assertEqual(cart.get_cart()["item_count"], 1)

	def test_remove_via_zero_qty(self):
		cart.add_item("SHOP-DEMO-003")
		payload = cart.set_qty("SHOP-DEMO-003", qty=0)
		self.assertEqual(payload["items"], [])

	def test_whole_items_are_sold_whole(self):
		cart.add_item("SHOP-DEMO-003")
		uom = frappe.db.get_value("Item", "SHOP-DEMO-003", "stock_uom")
		whole = frappe.db.get_value("UOM", uom, "must_be_whole_number")
		frappe.db.set_value("UOM", uom, "must_be_whole_number", 1)
		self.addCleanup(frappe.db.set_value, "UOM", uom, "must_be_whole_number", whole)
		frappe.clear_cache(doctype="UOM")
		with self.assertRaisesRegex(frappe.ValidationError, "whole numbers"):
			cart.set_qty("SHOP-DEMO-003", qty=0.5)
		with self.assertRaisesRegex(frappe.ValidationError, "whole numbers"):
			cart.add_item("SHOP-DEMO-003", qty=1.5)
		self.assertEqual(cart.get_cart()["item_count"], 1)

	def test_the_quantity_added_is_the_quantity_chosen(self):
		uom = frappe.db.get_value("Item", "SHOP-DEMO-003", "stock_uom")
		whole = frappe.db.get_value("UOM", uom, "must_be_whole_number")
		frappe.db.set_value("UOM", uom, "must_be_whole_number", 0)
		self.addCleanup(frappe.db.set_value, "UOM", uom, "must_be_whole_number", whole)
		frappe.clear_cache(doctype="UOM")
		self.assertEqual(cart.add_item("SHOP-DEMO-003", qty=0.5)["items"][0]["qty"], 0.5)
		self.assertEqual(cart.add_item("SHOP-DEMO-003", qty=12)["items"][0]["qty"], 12.5)
		for qty in (0, -1):
			with self.assertRaises(frappe.ValidationError):
				cart.add_item("SHOP-DEMO-003", qty=qty)

	def test_an_item_taken_off_sale_is_named(self):
		frappe.db.set_value("Item", "SHOP-DEMO-003", "disabled", 1)
		self.addCleanup(frappe.db.set_value, "Item", "SHOP-DEMO-003", "disabled", 0)
		name = frappe.db.get_value("Item", "SHOP-DEMO-003", "item_name")
		with self.assertRaisesRegex(frappe.ValidationError, f"{name} is no longer available"):
			cart.add_item("SHOP-DEMO-003")

	def test_variant_item_resolves_to_product(self):
		variant = frappe.get_all("Item", filters={"variant_of": "SHOP-DEMO-001"}, pluck="name", limit=1)[0]
		payload = cart.add_item(variant)
		self.assertEqual(payload["items"][0]["slug"], "crew-neck-t-shirt")
		values = frappe.get_all(
			"Item Variant Attribute", filters={"parent": variant}, pluck="attribute_value", order_by="idx asc"
		)
		self.assertTrue(payload["items"][0]["product_name"].endswith(" / ".join(values)))

	def in_stock(self, qty, allow_out_of_stock=0, threshold=0):
		settings = frappe.get_doc("Shop Settings")
		original = (settings.allow_out_of_stock, settings.low_stock_threshold)
		frappe.db.set_single_value(
			"Shop Settings", {"allow_out_of_stock": allow_out_of_stock, "low_stock_threshold": threshold}
		)
		frappe.clear_cache(doctype="Shop Settings")

		def restore():
			frappe.db.set_single_value(
				"Shop Settings", {"allow_out_of_stock": original[0], "low_stock_threshold": original[1]}
			)
			frappe.clear_cache(doctype="Shop Settings")

		self.addCleanup(restore)
		return patch("shop.storefront.stock.get_stock", return_value={"SHOP-DEMO-003": qty})

	def test_cart_takes_only_what_is_in_stock(self):
		self.assertTrue(frappe.db.get_value("Item", "SHOP-DEMO-003", "is_stock_item"))
		with self.in_stock(2):
			cart.add_item("SHOP-DEMO-003", qty=2)
			with self.assertRaisesRegex(frappe.ValidationError, "Only 2 of"):
				cart.add_item("SHOP-DEMO-003")
			with self.assertRaisesRegex(frappe.ValidationError, "Only 2 of"):
				cart.set_qty("SHOP-DEMO-003", qty=5)
		frappe.db.delete("Shop Cart")
		clear_request()
		with self.in_stock(0), self.assertRaisesRegex(frappe.ValidationError, "out of stock"):
			cart.add_item("SHOP-DEMO-003")
		with self.in_stock(0, allow_out_of_stock=1):
			self.assertEqual(cart.add_item("SHOP-DEMO-003")["item_count"], 1)

	def test_an_item_without_a_price_is_not_sold(self):
		with patch("shop.storefront.pricing.get_prices", return_value={}):
			with self.assertRaisesRegex(frappe.ValidationError, "isn't available online"):
				cart.add_item("SHOP-DEMO-003")
			self.assertEqual(
				stock.availability("SHOP-DEMO-003", priced=False)["stock_status"], "Not available online"
			)

	def test_what_the_product_page_says_about_stock(self):
		with self.in_stock(3, threshold=5):
			self.assertEqual(stock.availability("SHOP-DEMO-003"), stock.state(True, "low", "Only 3 left"))
		with self.in_stock(9, threshold=5):
			self.assertEqual(stock.availability("SHOP-DEMO-003")["stock_state"], "in")
		with self.in_stock(0):
			self.assertEqual(stock.availability("SHOP-DEMO-003"), stock.state(False, "out", "Out of stock"))

	def test_template_item_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			cart.add_item("SHOP-DEMO-001")

	def test_guest_cart_by_token(self):
		frappe.set_user("Guest")
		try:
			payload = cart.add_item("SHOP-DEMO-003")
			self.assertEqual(payload["item_count"], 1)
			token = frappe.db.get_value("Shop Cart", {"status": "Active"}, "token")
			set_request_cookie(token)
			payload = cart.get_cart()
			self.assertEqual(payload["item_count"], 1)
		finally:
			frappe.set_user("Administrator")

	def test_merge_guest_cart_on_login(self):
		frappe.set_user("Guest")
		try:
			cart.add_item("SHOP-DEMO-003")
		finally:
			frappe.set_user("Administrator")
		guest_token = frappe.db.get_value("Shop Cart", {"user": ["is", "not set"]}, "token")
		cart.add_item("SHOP-DEMO-004")
		set_request_cookie(guest_token)
		cart.merge_guest_cart()
		merged = cart.get_cart()
		self.assertEqual({row["item_code"] for row in merged["items"]}, {"SHOP-DEMO-003", "SHOP-DEMO-004"})
		self.assertEqual(frappe.db.count("Shop Cart", {"status": "Active"}), 1)


def set_request_cookie(token):
	frappe.local.request = frappe._dict(cookies={cart.CART_COOKIE: token})


def clear_request():
	if hasattr(frappe.local, "request"):
		del frappe.local.request
	if hasattr(frappe.local, "shop_cart_token"):
		del frappe.local.shop_cart_token
