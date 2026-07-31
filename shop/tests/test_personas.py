import re

import frappe
from frappe.tests import IntegrationTestCase

from shop import personas


class TestPersonas(IntegrationTestCase):
	def test_every_persona_has_a_complete_guide(self):
		guides = personas.all_personas()
		self.assertEqual(len(guides), 7)
		for guide in guides:
			self.assertTrue(guide["steps"], guide["key"])
			self.assertTrue(guide["verify"], guide["key"])
			self.assertTrue(guide["start_url"], guide["key"])
			self.assertIn(guide["kind"], ("shopper", "merchant"))

	def test_unknown_persona_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			personas.prepare("window-shopper")

	def test_returning_customer_gets_a_working_account(self):
		guide = personas.prepare("returning-customer")
		self.assertTrue(frappe.db.exists("User", personas.SHOPPER["email"]))
		self.assertEqual(guide["credentials"]["username"], personas.SHOPPER["email"])
		self.assertTrue(guide["credentials"]["password"])

	def test_operations_persona_seeds_an_open_order(self):
		guide = personas.prepare("merchant-operations")
		note = next(note for note in guide["prepared"] if "SAL-ORD" in note)
		order = re.search(r"SAL-ORD-\S+", note).group()
		self.assertEqual(frappe.db.get_value("Sales Order", order, "docstatus"), 1)
		confirmation = next(note for note in guide["prepared"] if "token=" in note)
		token = confirmation.split("token=")[1]
		self.assertTrue(frappe.db.exists("Shop Cart", {"token": token, "sales_order": order}))
