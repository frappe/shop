"""Who signs in and buys for a customer: its people (Portal Users) as staff manage them, the
customer a login linked to several buys for, and where customers land after signing in."""

from unittest.mock import patch
from urllib.parse import quote

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from shop.api import customers as customers_api
from shop.storefront import accounts, orders, pricing
from shop.tests.utils import fresh_request

PERSON = "people.person@example.com"
STAFF = "people.staff@example.com"


class TestCustomerAccess(IntegrationTestCase):
	def setUp(self):
		fresh_request()
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(fresh_request)
		self.company = self.customer("_Test People Company", "Company")
		self.personal = self.customer("_Test People Personal", "Individual")
		if not frappe.db.exists("User", STAFF):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": STAFF,
					"first_name": "Staff",
					"user_type": "System User",
					"roles": [{"role": "Sales User"}],
				}
			).insert(ignore_permissions=True)

	def customer(self, name: str, kind: str) -> str:
		if not frappe.db.exists("Customer", name):
			frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": kind}).insert(
				ignore_permissions=True
			)
		doc = frappe.get_doc("Customer", name)
		doc.set("portal_users", [])
		doc.save(ignore_permissions=True)
		return name

	def as_shopper(self, cookie: str | None = None):
		fresh_request()
		headers = {"Cookie": f"{pricing.BUYING_FOR_COOKIE}={quote(cookie)}"} if cookie else {}
		frappe.local.request = Request(EnvironBuilder(path="/", headers=headers).get_environ())
		frappe.local.cookie_manager = frappe.auth.CookieManager()
		frappe.set_user(PERSON)

	def test_staff_add_a_person_who_signs_in_and_buys_for_the_customer(self):
		people = customers_api.add_person(self.company, "Pat Person", PERSON)
		self.assertEqual([p["user"] for p in people], [PERSON])
		user = frappe.get_doc("User", PERSON)
		self.assertEqual(user.user_type, "Website User")
		self.assertIn("Customer", frappe.get_roles(PERSON))
		self.assertIn(self.company, orders.session_customers(PERSON))
		contact = frappe.db.get_value("Contact Email", {"email_id": PERSON}, "parent")
		self.assertTrue(
			frappe.db.exists(
				"Dynamic Link",
				{"parent": contact, "link_doctype": "Customer", "link_name": self.company},
			)
		)
		# adding them again changes nothing
		self.assertEqual(len(customers_api.add_person(self.company, "Pat Person", PERSON)), 1)

	def test_a_staff_login_is_not_made_a_customer(self):
		with self.assertRaises(frappe.ValidationError):
			customers_api.add_person(self.company, "Staff", STAFF)
		self.assertEqual(frappe.db.get_value("User", STAFF, "user_type"), "System User")

	def test_removing_a_person_keeps_their_login(self):
		customers_api.add_person(self.company, "Pat Person", PERSON)
		self.assertEqual(customers_api.remove_person(self.company, PERSON), [])
		self.assertNotIn(self.company, orders.session_customers(PERSON))
		self.assertTrue(frappe.db.exists("User", PERSON))

	def test_sign_in_on_and_off_and_a_reset_link(self):
		customers_api.add_person(self.company, "Pat Person", PERSON)
		off = customers_api.set_sign_in(self.company, PERSON, 0)
		self.assertFalse(off[0]["can_sign_in"])
		with self.assertRaises(frappe.ValidationError):
			customers_api.send_password_reset(self.company, PERSON)
		customers_api.set_sign_in(self.company, PERSON, 1)
		with patch("frappe.core.doctype.user.user.User._reset_password") as reset:
			customers_api.send_password_reset(self.company, PERSON)
		reset.assert_called_once_with(send_email=True)
		# only the customer's own people
		with self.assertRaises(frappe.ValidationError):
			customers_api.set_sign_in(self.personal, PERSON, 0)

	def test_only_staff_manage_people(self):
		customers_api.add_person(self.company, "Pat Person", PERSON)
		frappe.set_user(PERSON)
		for call in (
			lambda: customers_api.add_person(self.company, "Someone", "someone@example.com"),
			lambda: customers_api.remove_person(self.company, PERSON),
			lambda: customers_api.set_sign_in(self.company, PERSON, 0),
			lambda: customers_api.send_password_reset(self.company, PERSON),
		):
			self.assertRaises(frappe.PermissionError, call)

	def test_a_login_on_two_customers_chooses_which_it_buys_for(self):
		customers_api.add_person(self.personal, "Pat Person", PERSON)
		customers_api.add_person(self.company, "Pat Person", PERSON)
		self.as_shopper()
		self.assertEqual(pricing.session_customer(), orders.session_customers(PERSON)[0])
		self.assertIn("<select", pricing.buying_for_html())
		pricing.set_buying_for(self.company)
		self.assertEqual(pricing.session_customer(), self.company)
		self.as_shopper(self.company)
		self.assertEqual(pricing.session_customer(), self.company)
		self.assertIn(f'value="{self.company}" selected', pricing.buying_for_html())

	def test_a_choice_that_is_not_theirs_is_ignored_and_refused(self):
		customers_api.add_person(self.company, "Pat Person", PERSON)
		self.as_shopper(self.personal)
		self.assertEqual(pricing.session_customer(), self.company)
		with self.assertRaises(frappe.PermissionError):
			pricing.set_buying_for(self.personal)

	def test_a_company_buyer_sees_who_they_buy_for(self):
		customers_api.add_person(self.company, "Pat Person", PERSON)
		self.as_shopper()
		self.assertIn("_Test People Company", pricing.buying_for_html())
		self.assertNotIn("<select", pricing.buying_for_html())

	def test_customers_land_in_the_store(self):
		settings = frappe.get_doc("Shop Settings")
		original = (settings.customers_land_in_store, frappe.db.get_value("Role", "Customer", "home_page"))
		self.addCleanup(frappe.db.set_value, "Role", "Customer", "home_page", original[1])
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "customers_land_in_store", original[0])
		frappe.db.set_single_value("Shop Settings", "customers_land_in_store", 1)
		frappe.clear_cache(doctype="Shop Settings")
		accounts.sync_customer_home_page()
		home = frappe.db.get_value("Role", "Customer", "home_page")
		self.assertTrue(home.endswith("account/orders"))
		self.assertFalse(home.startswith("/"))
		frappe.db.set_single_value("Shop Settings", "customers_land_in_store", 0)
		frappe.clear_cache(doctype="Shop Settings")
		accounts.sync_customer_home_page()
		self.assertFalse(frappe.db.get_value("Role", "Customer", "home_page"))

	def test_frappes_account_page_sends_customers_to_the_store(self):
		original = frappe.db.get_single_value("Shop Settings", "customers_land_in_store")
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "customers_land_in_store", original)
		self.addCleanup(setattr, frappe.flags, "redirect_location", None)
		frappe.db.set_single_value("Shop Settings", "customers_land_in_store", 1)
		customers_api.add_person(self.company, "Pat Person", PERSON)
		frappe.set_user(PERSON)
		with self.assertRaises(frappe.Redirect) as raised:
			accounts.account_page_redirect(frappe._dict(path="me"))
		self.assertEqual(raised.exception.http_status_code, 302)
		self.assertTrue(frappe.flags.redirect_location.endswith("account/orders"))
		accounts.account_page_redirect(frappe._dict(path="about"))
		frappe.set_user(STAFF)
		accounts.account_page_redirect(frappe._dict(path="me"))
		frappe.set_user(PERSON)
		frappe.db.set_single_value("Shop Settings", "customers_land_in_store", 0)
		accounts.account_page_redirect(frappe._dict(path="me"))


class TestOwingSummary(IntegrationTestCase):
	def test_the_account_page_says_what_is_owed_and_what_is_overdue(self):
		from shop.storefront.page_data import owing_summary

		row = lambda owed, overdue=False, due="2026-12-20": frappe._dict(  # noqa: E731
			outstanding_amount=owed, currency="NZD", overdue=overdue, due_date=frappe.utils.getdate(due)
		)
		self.assertIn("Nothing owing", owing_summary([row(0)]))
		summary = owing_summary([row(100), row(50.5, due="2026-12-01"), row(0)])
		self.assertIn("on 2 invoices", summary)
		self.assertIn("150.50", summary)
		self.assertIn("Next due 01-12-2026", summary)
		self.assertIn("1 overdue", owing_summary([row(100, overdue=True), row(20)]))
