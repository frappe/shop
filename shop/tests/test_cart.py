import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import cart


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

	def test_remove_via_zero_qty(self):
		cart.add_item("SHOP-DEMO-003")
		payload = cart.set_qty("SHOP-DEMO-003", qty=0)
		self.assertEqual(payload["items"], [])

	def test_variant_item_resolves_to_product(self):
		variant = frappe.get_all(
			"Item", filters={"variant_of": "SHOP-DEMO-001"}, pluck="name", limit=1
		)[0]
		payload = cart.add_item(variant)
		self.assertEqual(payload["items"][0]["slug"], "crew-neck-t-shirt")

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
