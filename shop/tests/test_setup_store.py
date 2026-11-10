"""Setting a store up on ERPNext's own records, and doing it again changes nothing."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.nestedset import get_root_of

from shop import setup_store
from shop.tests.utils import service


class TestSetUpStore(IntegrationTestCase):
	def setUp(self):
		self.settings = frappe.get_doc("Shop Settings")
		self.original = {
			f: self.settings.get(f)
			for f in (
				"shipping_item",
				"card_fee_item",
				"conversion_fee_item",
				"trade_customer_group",
				"tax_template",
				"export_tax_template",
				"email_statements",
			)
		}
		self.addCleanup(lambda: frappe.db.set_single_value("Shop Settings", self.original))

	def test_store_is_set_up_on_erpnext_records_and_again_changes_nothing(self):
		settings = setup_store.set_up(
			trade_group="_Test Setup Trade", trade_discounts={get_root_of("Item Group"): 10}, statements=True
		)
		company = settings.company
		for field, code, _name, account_name in setup_store.CHARGE_ITEMS:
			self.assertEqual(settings.get(field), code)
			income = frappe.db.get_value(
				"Item Default", {"parent": code, "company": company}, "income_account"
			)
			self.assertEqual(frappe.db.get_value("Account", income, "account_name"), account_name)
		self.assertEqual(settings.trade_customer_group, "_Test Setup Trade")
		rule = frappe.db.get_value(
			"Pricing Rule",
			{"customer_group": "_Test Setup Trade"},
			["name", "discount_percentage"],
			as_dict=True,
		)
		self.assertEqual(rule.discount_percentage, 10)
		if settings.tax_template:
			self.assertTrue(settings.export_tax_template)
		self.assertEqual(frappe.db.get_single_value("Shop Settings", "email_statements"), 1)

		# an owner's changes are kept when set-up runs again
		frappe.db.set_value("Pricing Rule", rule.name, "discount_percentage", 12)
		frappe.db.set_single_value(
			"Shop Settings", "shipping_item", service("TEST-SHIPPING", settings.company)
		)
		frappe.clear_cache(doctype="Shop Settings")
		rules = frappe.db.count("Pricing Rule")
		setup_store.set_up(trade_group="_Test Setup Trade", trade_discounts={get_root_of("Item Group"): 10})
		self.assertEqual(frappe.db.get_value("Pricing Rule", rule.name, "discount_percentage"), 12)
		self.assertEqual(frappe.db.count("Pricing Rule"), rules)
		self.assertEqual(frappe.db.get_single_value("Shop Settings", "shipping_item"), "TEST-SHIPPING")
