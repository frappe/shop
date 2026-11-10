from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import product
from shop.tests.utils import fresh_request

ITEM = "SHOP-DEMO-003"


class TestStockAlerts(IntegrationTestCase):
	def setUp(self):
		fresh_request()
		frappe.db.delete("Shop Stock Alert")

	def test_a_shopper_is_told_once_when_an_item_is_back(self):
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		product.alert_when_in_stock(ITEM, " Waiting@Example.com ")
		product.alert_when_in_stock(ITEM, "waiting@example.com")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Shop Stock Alert", {"email": "waiting@example.com"}), 1)

		with (
			patch("shop.storefront.stock.availability", return_value={"purchasable": False}),
			patch("frappe.sendmail") as sendmail,
		):
			product.send_stock_alerts()
		sendmail.assert_not_called()

		with (
			patch("shop.storefront.stock.availability", return_value={"purchasable": True}),
			patch("frappe.sendmail") as sendmail,
		):
			product.send_stock_alerts()
			product.send_stock_alerts()
		self.assertEqual(sendmail.call_count, 1)
		mail = sendmail.call_args.kwargs
		self.assertEqual(mail["recipients"], ["waiting@example.com"])
		self.assertIn("back in stock", mail["subject"])
		slug = frappe.db.get_value("Shop Product", {"item": ITEM}, "slug")
		self.assertIn(f"product/{slug}", mail["message"])

	def test_only_items_the_store_sells_can_be_waited_for(self):
		with self.assertRaises(frappe.DoesNotExistError):
			product.alert_when_in_stock("_Test Item That Isnt Sold", "someone@example.com")
		with self.assertRaises(frappe.ValidationError):
			product.alert_when_in_stock(ITEM, "not an email")
