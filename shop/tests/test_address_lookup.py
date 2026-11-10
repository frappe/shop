import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import address_lookup

# this module stands in for the app that looks addresses up
asked = []


def suggestions(text, country, session):
	asked.append((text, country, session))
	return {"enabled": True, "suggestions": [{"id": "1", "label": "12 Queen Street", "detail": "Auckland"}]}


def details(id, session):
	return {"address_line1": "12 Queen Street", "city": "Auckland", "country": "New Zealand"}


def status():
	return {"enabled": True, "service": "Photon", "settings_url": "/app/address-lookup-settings"}


class TestAddressLookup(IntegrationTestCase):
	def test_off_without_an_app_that_looks_addresses_up(self):
		with self.patch_hooks({"shop_address_lookup": []}):
			self.assertEqual(address_lookup.suggest("12 Queen Street"), {"enabled": False, "suggestions": []})
			self.assertEqual(address_lookup.status(), {"installed": False, "enabled": False})

	def test_the_storefront_asks_the_app_registered_for_it(self):
		asked.clear()
		with self.patch_hooks({"shop_address_lookup": [__name__]}):
			result = address_lookup.suggest("12 Queen", country="New Zealand", session="s1")
			found = address_lookup.address("1", session="s1")
			state = address_lookup.status()

		self.assertEqual(asked, [("12 Queen", "New Zealand", "s1")])
		self.assertEqual(result["suggestions"][0]["label"], "12 Queen Street")
		self.assertEqual(found["city"], "Auckland")
		self.assertEqual(state["service"], "Photon")
		self.assertTrue(state["installed"])
