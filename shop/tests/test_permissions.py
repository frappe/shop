"""Staff-only actions are refused to shoppers and guests."""

import frappe
from frappe.tests import IntegrationTestCase

from shop.api import customers, orders, pricing, settings, trade
from shop.storefront import accounts
from shop.tests.utils import fresh_request

SHOPPER = "permissions.shopper@example.com"


class TestPermissions(IntegrationTestCase):
	def setUp(self):
		fresh_request()
		if not frappe.db.exists("User", SHOPPER):
			frappe.get_doc(
				{"doctype": "User", "email": SHOPPER, "first_name": "Shopper", "user_type": "Website User"}
			).insert(ignore_permissions=True)
		self.lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"first_name": "Permission",
				"lead_name": "Permission Test",
				"email_id": "permission.lead@example.com",
				"utm_source": accounts.trade_source(),
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.set_user, "Administrator")

	def staff_only(self):
		return [
			lambda: pricing.save_rates("trade", "Item Group", "_Test", []),
			lambda: pricing.remove_rates("trade", "Item Group", "_Test"),
			lambda: pricing.get_rates("trade"),
			lambda: trade.get_trade_accounts(),
			lambda: trade.make_trade_customer(customer="_Test"),
			lambda: trade.end_trade(customer="_Test"),
			lambda: trade.get_trade(),
			lambda: orders.refund(name="_Test", credit_note="_Test", method="card"),
			lambda: orders.cancel_order(name="_Test"),
			lambda: orders.mark_paid(name="_Test"),
			lambda: settings.save_settings({"store_name": "Changed"}),
			lambda: settings.save_shipping_restrictions([], []),
			lambda: settings.save_shipping_surcharges([]),
			lambda: accounts.approve_trade(lead=self.lead.name),
			lambda: accounts.decline_trade(lead=self.lead.name),
			lambda: customers.add_person(customer="_Test", full_name="Someone", email="someone@example.com"),
			lambda: customers.remove_person(customer="_Test", user=SHOPPER),
			lambda: customers.send_password_reset(customer="_Test", user=SHOPPER),
			lambda: customers.set_sign_in(customer="_Test", user=SHOPPER, enabled=0),
		]

	def test_shoppers_and_guests_cant_run_staff_actions(self):
		for user in (SHOPPER, "Guest"):
			frappe.set_user(user)
			for index, action in enumerate(self.staff_only()):
				with self.assertRaises(frappe.PermissionError, msg=f"{user}, action {index}"):
					action()
