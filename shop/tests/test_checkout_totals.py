"""Checkout totals worked out by ERPNext: tax in or on top of prices, exports, coupons, shipping,
import duties, card and conversion fees, other currencies, and what happens once an order is placed."""

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate

from shop.api.settings import GATEWAY_FIELDS
from shop.storefront import cart, checkout, payment, totals
from shop.tests.utils import (
	company_bank_account,
	fresh_request,
	gateway,
	sellable,
	service,
	template,
	terms_record,
)

BUYER = {"email": "totals.buyer@example.com", "full_name": "Totals Buyer", "phone": "021000000"}
ITEM = "SHOP-DEMO-003"
SETTINGS_FIELDS = (
	"prices_include_tax",
	"show_prices_with_tax",
	"tax_template",
	"export_tax_template",
	"shipping_item",
	"shipping_account",
	"card_fee_item",
	"enable_bank_transfer",
	"conversion_fee_item",
	"transfer_fee_item",
	"bank_charges_account",
	"bank_transfer_days",
	"require_terms",
	"allow_quote_requests",
	"terms_url",
	"terms_and_conditions",
	"terms_checkbox_note",
	"business_buyer_label",
	"flat_shipping_rate",
	"free_shipping_above",
	"enable_cod",
	"invoice_paid_orders",
	"cancel_unpaid_orders",
	"other_currencies_with_tax",
	"duties_item",
)

TEST_PROVIDER = "shop.tests.test_checkout_totals.test_rates"


def test_rates(context):
	"""A shipping app: one courier service, 12.00 before tax; none to Antarctica."""
	if context.address.country == "Antarctica":
		return {"options": [], "messages": ["We don't ship there"]}
	return [{"id": "test:courier", "label": "Test Courier", "amount": 12.0, "tax_included": False}]


def rates_with_tax(context):
	"""A shipping app whose prices include the store's tax: 13.80 is 12.00 plus 15%."""
	return [{"id": "test:taxed", "label": "Taxed Courier", "amount": 13.80, "tax_included": True}]


def inactive_rates(context):
	return None


BUSY = {"busy": True}


def busy_then_rates(context):
	"""A shipping app that is busy the first time it is asked."""
	if BUSY["busy"]:
		BUSY["busy"] = False
		return {"options": [], "messages": ["Live shipping prices aren't available right now"]}
	return test_rates(context)


def line(quote, kind):
	return [row["amount"] for row in totals.summary_lines(quote.order)[0] if row["kind"] == kind]


def grand(quote) -> float:
	"""The order total before any rounding, for checking the sums."""
	return flt(quote.order.grand_total)


def fee_row(quote, item):
	return next(row for row in quote.order.items if row.item_code == item)


class TestCheckoutTotals(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()
		# what the store works out once per request, kept across tests in one process otherwise
		frappe.local.shop_customer_rates = {}
		frappe.local.shop_item_tax_rates = {}
		settings = frappe.get_doc("Shop Settings")
		self.original = {field: settings.get(field) for field in SETTINGS_FIELDS}
		self.original_banks = [row.as_dict() for row in settings.bank_accounts]
		self.original_gateways = [
			{f: row.get(f) for f in GATEWAY_FIELDS} for row in settings.payment_gateways
		]
		self.company = settings.company
		sellable(ITEM, 20)
		self.company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.home = frappe.get_cached_value("Company", self.company, "country")
		self.other = "United States" if self.home != "United States" else "Australia"
		self.foreign = "USD" if self.company_currency != "USD" else "EUR"
		self.export_template = template(self.company, "Test VAT 0 export", 0, 0)
		self.set(
			prices_include_tax=1,
			show_prices_with_tax=0,
			other_currencies_with_tax=0,
			tax_template=template(self.company, "Test VAT 15 included", 15, 1),
			export_tax_template=self.export_template,
			shipping_item=service("TEST-SHIPPING", self.company),
			card_fee_item=service("TEST-CARD-FEE", self.company),
			conversion_fee_item=service("TEST-CONVERSION", self.company),
			transfer_fee_item=service("TEST-TRANSFER-FEE", self.company),
			bank_charges_account=frappe.db.get_value(
				"Account", {"company": self.company, "root_type": "Expense", "is_group": 0}
			),
			enable_bank_transfer=1,
			bank_transfer_days=7,
			enable_cod=1,
			require_terms=0,
			flat_shipping_rate=0,
			free_shipping_above=0,
			invoice_paid_orders=0,
			cancel_unpaid_orders=0,
		)
		settings = frappe.get_doc("Shop Settings")
		settings.bank_accounts = []
		settings.append(
			"bank_accounts",
			{"bank_account": company_bank_account(self.company, self.company_currency), "label": "Home"},
		)
		settings.append(
			"bank_accounts",
			{
				"bank_account": company_bank_account(self.company, self.foreign),
				"label": "Foreign",
				"conversion_fee_percent": 1,
				"swift_transfer_fee": 6.11,
				"instructions": "Pay by ACH",
			},
		)
		settings.payment_gateways = []
		settings.append(
			"payment_gateways",
			{
				"payment_gateway": gateway(self.company),
				"label": "Card",
				"fee_percent": 2.65,
				"fee_fixed": 0.30,
				"fee_percent_international": 3.5,
				"fee_fixed_international": 0.30,
			},
		)
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")
		for source, target, rate in (
			(self.company_currency, self.foreign, 0.5),
			(self.foreign, self.company_currency, 2.0),
		):
			if not frappe.db.exists("Currency Exchange", {"from_currency": source, "to_currency": target}):
				frappe.get_doc(
					{
						"doctype": "Currency Exchange",
						"date": add_days(nowdate(), -1),
						"from_currency": source,
						"to_currency": target,
						"exchange_rate": rate,
						"for_selling": 1,
					}
				).insert(ignore_permissions=True)
		self.price = flt(
			frappe.db.get_value(
				"Item Price", {"item_code": ITEM, "price_list": settings.price_list}, "price_list_rate"
			)
		)
		self.home_address = {
			"address_line1": "5 High Street",
			"city": "Town",
			"pincode": "9016",
			"country": self.home,
		}
		self.abroad_address = {
			"address_line1": "1 Ice Shelf",
			"city": "Base",
			"pincode": "0001",
			"country": self.other,
		}

	def tearDown(self):
		settings = frappe.get_doc("Shop Settings")
		settings.update(self.original)
		settings.bank_accounts = []
		for row in self.original_banks:
			settings.append(
				"bank_accounts",
				{
					k: row[k]
					for k in (
						"bank_account",
						"label",
						"conversion_fee_percent",
						"local_transfer_fee",
						"swift_transfer_fee",
						"instructions",
					)
				},
			)
		settings.payment_gateways = []
		for row in self.original_gateways:
			settings.append("payment_gateways", row)
		settings.import_duties = []
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")

	def set(self, **values):
		frappe.db.set_single_value("Shop Settings", values)
		frappe.clear_cache(doctype="Shop Settings")

	def free_coupon(self) -> str:
		"""A coupon for 100% off, as ERPNext's coupons are set up."""
		code = "TESTFREE100"
		if not frappe.db.exists("Coupon Code", {"coupon_code": code}):
			rule = frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": "Test free order",
					"apply_on": "Transaction",
					"selling": 1,
					"coupon_code_based": 1,
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": 100,
					"company": self.company,
					"currency": self.company_currency,
				}
			).insert(ignore_permissions=True)
			frappe.get_doc(
				{
					"doctype": "Coupon Code",
					"coupon_name": code,
					"coupon_code": code,
					"coupon_type": "Promotional",
					"pricing_rule": rule.name,
				}
			).insert(ignore_permissions=True)
		return code

	def basket(self, qty=2, item=ITEM):
		cart.add_item(item, qty=qty)
		return cart.resolve_cart()

	def without_tax(self):
		"""A store whose prices exclude tax, which is added on top."""
		self.set(prices_include_tax=0, tax_template=template(self.company, "Test VAT 15 added", 15, 0))

	def place(self, **kwargs):
		kwargs.setdefault("payment_method", "bank")
		kwargs.setdefault("address", self.home_address)
		return checkout.place_order(customer=BUYER, **kwargs)["sales_order"]

	def pay(self, name, amount=None):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		entry = get_payment_entry("Sales Order", name, party_amount=amount)
		entry.reference_no, entry.reference_date = "TEST", nowdate()
		entry.insert(ignore_permissions=True)
		entry.submit()
		return entry

	def two_gateways(self):
		"""The store's card gateway plus a second one, in the store's and a foreign currency, with its
		own fee."""
		other = gateway(self.company, "_Test Shop Wallet", (self.company_currency, self.foreign))
		settings = frappe.get_doc("Shop Settings")
		settings.append(
			"payment_gateways",
			{"payment_gateway": other, "label": "Wallet", "fee_label": "Wallet fee", "fee_percent": 4},
		)
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")
		return totals.gateway_method(other)

	# --- import duties -------------------------------------------------------

	def with_duties(self, **row):
		"""Orders sent to the other country pay its duty: 15%, a 5% fee on it and 5.00 a parcel."""
		settings = frappe.get_doc("Shop Settings")
		settings.duties_item = service("TEST-DUTIES", self.company)
		frappe.db.set_value("Item", "TEST-DUTIES", "item_name", "Duties and Import Fees")
		settings.import_duties = []
		settings.append(
			"import_duties",
			{"country": self.other, "duty_rate": 15, "fee_on_duty": 5, "fee_per_parcel": 5} | row,
		)
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")

	def test_an_order_sent_duties_paid_pays_duty_and_fees_as_one_line(self):
		self.with_duties()
		quote = totals.compute(self.basket(1), self.abroad_address, None, "bank", self.company_currency)
		goods = flt(self.price / 1.15, 2)
		self.assertEqual(line(quote, "duties"), [flt(goods * 0.15 * 1.05 + 5, 2)])
		self.assertEqual(fee_row(quote, "TEST-DUTIES").description, "Duties and Import Fees")
		self.assertEqual(grand(quote), flt(goods + goods * 0.15 * 1.05 + 5, 2))
		self.assertIn(
			"Duties are paid before delivery: there is nothing more to pay when it arrives.",
			totals.payload(quote)["notes"],
		)

	def test_duties_are_only_for_the_countries_listed(self):
		self.with_duties()
		home = totals.compute(self.basket(1), self.home_address, None, "bank")
		self.assertEqual(line(home, "duties"), [])
		elsewhere = dict(self.abroad_address, country="Antarctica")
		other = totals.compute(cart.resolve_cart(), elsewhere, None, "bank", self.company_currency)
		self.assertEqual(line(other, "duties"), [])
		collected = totals.compute(
			cart.resolve_cart(), self.abroad_address, None, "bank", self.company_currency, collected=True
		)
		self.assertEqual(line(collected, "duties"), [])

	def test_goods_worth_up_to_the_duty_free_value_pay_no_duty(self):
		self.with_duties(duty_free_up_to=flt(self.price / 1.15, 2))
		one = totals.compute(self.basket(1), self.abroad_address, None, "bank", self.company_currency)
		self.assertEqual(line(one, "duties"), [])
		cart.add_item(ITEM, qty=1)
		two = totals.compute(cart.resolve_cart(), self.abroad_address, None, "bank", self.company_currency)
		self.assertEqual(line(two, "duties"), [flt(2 * flt(self.price / 1.15, 2) * 0.15 * 1.05 + 5, 2)])

	def test_the_fee_per_parcel_is_in_the_stores_currency(self):
		self.with_duties()
		quote = totals.compute(self.basket(1), self.abroad_address, None, "swift", self.foreign)
		self.assertEqual(quote.currency, self.foreign)
		goods = sum(row.net_amount for row in quote.order.items if row.item_code == ITEM)
		# 5.00 in the store's currency is 2.50 in the foreign one
		self.assertAlmostEqual(line(quote, "duties")[0], goods * 0.15 * 1.05 + 2.5, delta=0.01)

	def test_the_card_fee_covers_the_duties_paid_by_card(self):
		self.with_duties()
		quote = totals.compute(self.basket(1), self.abroad_address, None, "gateway")
		self.assertTrue(line(quote, "duties"))
		self.assertAlmostEqual(
			fee_row(quote, "TEST-CARD-FEE").amount, 0.035 * grand(quote) + 0.30, delta=0.01
		)

	def test_a_placed_order_keeps_the_duties_line(self):
		self.with_duties()
		quote = totals.compute(self.basket(1), self.abroad_address, None, "bank", self.company_currency)
		order = frappe.get_doc(
			"Sales Order",
			self.place(
				address=self.abroad_address, currency=self.company_currency, expected_total=quote.total
			),
		)
		duties = [row for row in order.items if row.item_code == "TEST-DUTIES"]
		self.assertEqual([row.amount for row in duties], line(quote, "duties"))
		self.assertEqual(totals.order_total(order), quote.total)

	def test_import_duties_need_a_duties_item_and_one_row_a_country(self):
		settings = frappe.get_doc("Shop Settings")
		settings.duties_item = None
		settings.import_duties = []
		settings.append("import_duties", {"country": self.other, "duty_rate": 10})
		self.assertRaises(frappe.ValidationError, settings.save)
		settings.duties_item = service("TEST-DUTIES", self.company)
		settings.append("import_duties", {"country": self.other, "duty_rate": 12})
		self.assertRaises(frappe.ValidationError, settings.save)

	# --- online payment gateways ---------------------------------------------

	def test_each_online_gateway_is_offered_with_its_own_fee(self):
		from shop.storefront import pricing

		wallet = self.two_gateways()
		card = totals.gateway_method(gateway(self.company))
		methods = {m["method"]: m for m in totals.payment_methods()}
		self.assertEqual(methods[card]["label"], "Card")
		self.assertEqual(methods[wallet]["label"], "Wallet")
		self.assertTrue(methods[card]["fee_note"].startswith("Card fee 2.65%"), methods[card]["fee_note"])
		self.assertEqual(methods[wallet]["fee_note"], "Wallet fee 4%, added to the total")
		# a fixed fee is in the store's currency, said so when other currencies are shown
		if len(pricing.display_currencies()) > 1:
			self.assertIn(f"0.30 {self.company_currency}", methods[card]["fee_note"])

		by_card = totals.compute(self.basket(), self.home_address, None, card)
		by_wallet = totals.compute(cart.resolve_cart(), self.home_address, None, wallet)
		self.assertAlmostEqual(
			fee_row(by_wallet, "TEST-CARD-FEE").net_amount, 0.04 * grand(by_wallet), delta=0.01
		)
		self.assertNotEqual(
			fee_row(by_card, "TEST-CARD-FEE").amount, fee_row(by_wallet, "TEST-CARD-FEE").amount
		)
		self.assertIn("Wallet fee", [line["label"] for line in totals.payload(by_wallet)["lines"]])
		self.assertEqual(fee_row(by_wallet, "TEST-CARD-FEE").item_name, "Wallet fee")
		# a plain "gateway" is the first one
		self.assertEqual(totals.resolve_method(totals.GATEWAY), card)

	def test_a_gateway_without_an_account_for_the_company_is_not_offered(self):
		if not frappe.db.exists("Payment Gateway", "_Test Shop No Account"):
			frappe.get_doc({"doctype": "Payment Gateway", "gateway": "_Test Shop No Account"}).insert()
		settings = frappe.get_doc("Shop Settings")
		settings.append("payment_gateways", {"payment_gateway": "_Test Shop No Account"})
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")
		self.assertNotIn(
			totals.gateway_method("_Test Shop No Account"), [m["method"] for m in totals.payment_methods()]
		)

	def test_an_online_order_is_paid_through_the_chosen_gateway_in_its_currency(self):
		from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest

		wallet = self.two_gateways()
		card = totals.gateway_method(gateway(self.company))
		with patch.object(PaymentRequest, "get_payment_url", return_value="https://pay.example.com/x"):
			self.basket(1)
			by_wallet = frappe.get_doc(
				"Sales Order", self.place(payment_method=wallet, currency=self.foreign)
			)
			self.basket(1)
			by_card = frappe.get_doc("Sales Order", self.place(payment_method=card, currency=self.foreign))
		# the wallet has an account in the shopper's currency; the card gateway only in the store's
		self.assertEqual(
			(by_wallet.shop_payment_method, by_wallet.shop_payment_gateway, by_wallet.currency),
			(totals.GATEWAY, "_Test Shop Wallet", self.foreign),
		)
		self.assertEqual(
			(by_card.shop_payment_gateway, by_card.currency), (gateway(self.company), self.company_currency)
		)
		self.assertEqual(
			[row.item_name for row in by_wallet.items if row.item_code == "TEST-CARD-FEE"], ["Wallet fee"]
		)
		for order in (by_wallet, by_card):
			request = frappe.get_doc("Payment Request", {"reference_name": order.name, "docstatus": 1})
			self.assertEqual(request.payment_gateway, order.shop_payment_gateway)
			self.assertEqual(
				frappe.db.get_value("Payment Gateway Account", request.payment_gateway_account, "currency"),
				order.currency,
			)

	def test_the_stores_one_gateway_and_card_fee_become_its_first_gateway(self):
		from shop.patches import move_payment_gateway_to_table

		account = totals.gateway_account(gateway(self.company)).name
		settings = frappe.get_doc("Shop Settings")
		settings.payment_gateways = []
		settings.save(ignore_permissions=True)
		for field, value in (
			("payment_gateway_account", account),
			("online_payment_label", "Pay by card"),
			("card_fee_percent", 2.5),
			("card_fee_fixed_international", 0.5),
		):
			frappe.db.sql(
				"insert into `tabSingles` (doctype, field, value) values ('Shop Settings', %s, %s)",
				(field, value),
			)
		move_payment_gateway_to_table.execute()
		row = frappe.get_doc("Shop Settings").payment_gateways[0]
		self.assertEqual(
			(row.payment_gateway, row.label, row.fee_label, row.fee_percent, row.fee_fixed_international),
			(gateway(self.company), "Pay by card", "Card fee", 2.5, 0.5),
		)
		self.assertFalse(
			frappe.db.exists("Singles", {"doctype": "Shop Settings", "field": "payment_gateway_account"})
		)

	# --- totals ---------------------------------------------------------------

	def test_card_fee_covers_the_provider_fee_on_the_final_total(self):
		quote = totals.compute(self.basket(), self.home_address, None, "gateway")
		fee = fee_row(quote, "TEST-CARD-FEE")
		self.assertEqual(grand(quote), flt(self.price * 2 + fee.amount, 2))
		# what the store keeps of the fee, after its tax, pays the provider's charge on the total
		self.assertAlmostEqual(fee.net_amount, 0.0265 * grand(quote) + 0.30, delta=0.01)
		self.assertGreaterEqual(fee.net_amount, 0.0265 * grand(quote) + 0.30 - 0.005)

	def test_bank_transfer_has_no_card_fee(self):
		quote = totals.compute(self.basket(), self.home_address, None, "bank")
		self.assertEqual(quote.fees, [])
		self.assertEqual(grand(quote), flt(self.price * 2, 2))

	def test_quote_and_order_are_the_same_erpnext_totals(self):
		with patch("frappe.get_hooks", side_effect=hooks_with([TEST_PROVIDER])):
			quote = totals.compute(self.basket(), self.home_address, None, "bank")
			order = frappe.get_doc("Sales Order", self.place(expected_total=quote.total))
		self.assertEqual(totals.order_total(order), quote.total)
		self.assertEqual([row.item_code for row in order.items], [row.item_code for row in quote.order.items])

	def test_export_takes_included_tax_off_and_uses_the_export_template(self):
		quote = totals.compute(self.basket(1), self.abroad_address, None, "bank", self.company_currency)
		self.assertTrue(quote.export)
		self.assertEqual(quote.tax_template, self.export_template)
		self.assertEqual(quote.order.items[0].rate, flt(self.price / 1.15, 2))
		self.assertIn("Tax-free export", totals.payload(quote)["notes"])
		card = totals.compute(cart.resolve_cart(), self.abroad_address, None, "gateway")
		self.assertAlmostEqual(fee_row(card, "TEST-CARD-FEE").amount, 0.035 * grand(card) + 0.30, delta=0.01)

	def test_a_shopping_cart_tax_rule_comes_before_the_export_template(self):
		rule_template = template(self.company, "Test VAT 5 rule", 5, 0)
		rule = frappe.get_doc(
			{
				"doctype": "Tax Rule",
				"tax_type": "Sales",
				"company": self.company,
				"use_for_shopping_cart": 1,
				"shipping_country": self.other,
				"sales_tax_template": rule_template,
				"priority": 1,
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Tax Rule", rule.name, force=True)
		quote = totals.compute(self.basket(1), self.abroad_address, None, "bank", self.company_currency)
		self.assertEqual(quote.tax_template, rule_template)

	def test_foreign_currency_bank_transfer(self):
		quote = totals.compute(self.basket(1), self.abroad_address, None, "bank", self.foreign)
		self.assertEqual(quote.currency, self.foreign)
		goods = flt(self.price / 1.15 * 0.5, 2)
		self.assertAlmostEqual(line(quote, "subtotal")[0], goods, delta=0.01)
		self.assertEqual([fee.kind for fee in quote.fees], ["conversion_fee"])
		self.assertAlmostEqual(fee_row(quote, "TEST-CONVERSION").net_amount, goods * 0.01, delta=0.01)
		name = self.place(address=self.abroad_address, currency=self.foreign)
		order = frappe.get_doc("Sales Order", name)
		self.assertEqual(order.currency, self.foreign)
		self.assertEqual(totals.order_total(order), quote.total)
		self.assertEqual(order.contact_email, BUYER["email"])
		info = payment.bank_instructions(order)
		self.assertEqual(info["reference"], order.name)
		branch = "ACH routing number" if self.foreign == "USD" else "Branch code"
		self.assertIn(f"{branch}: 2", info["details"])
		self.assertIn("Account number: 3", info["details"])
		self.assertIn("BIC/SWIFT: TESTXX22", info["details"])
		self.assertIn("Pay by ACH", info["details"])

	def quantity_break(self, qty: int, percent: float) -> str:
		"""An ERPNext Pricing Rule: buy `qty` or more of the test item, get `percent` off."""
		title = f"Test {qty}+ break"
		name = frappe.db.get_value("Pricing Rule", {"title": title})
		if not name:
			rule = frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": title,
					"apply_on": "Item Code",
					"items": [{"item_code": ITEM}],
					"selling": 1,
					"min_qty": qty,
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": percent,
					"company": self.company,
					"currency": self.company_currency,
				}
			).insert(ignore_permissions=True)
			name = rule.name
		self.addCleanup(frappe.db.set_value, "Pricing Rule", name, "disable", 1)
		frappe.db.set_value("Pricing Rule", name, "disable", 0)
		return name

	def test_pricing_rule_discount_is_charged_as_quoted(self):
		self.quantity_break(3, 15)
		self.basket(3)
		for method in ("bank", "cod"):
			with self.subTest(method=method):
				quote = totals.compute(cart.resolve_cart(), self.home_address, None, method)
				item = next(row for row in quote.order.items if row.item_code == ITEM)
				self.assertEqual(flt(item.discount_percentage), 15)
				name = self.place(payment_method=method, expected_total=quote.total)
				order = frappe.get_doc("Sales Order", name)
				line = next(row for row in order.items if row.item_code == ITEM)
				self.assertEqual(flt(line.rate), flt(item.rate))
				self.assertEqual(totals.order_total(order), quote.total)
				self.basket(3)

	def test_a_guests_cart_shows_the_quantity_break(self):
		self.quantity_break(3, 15)
		basket = self.basket(3)
		cart.refresh_rates(basket)
		self.assertAlmostEqual(basket.items[0].rate, flt(self.price * 0.85, 2), delta=0.01)
		quote = totals.compute(basket, self.home_address, None, "bank")
		line = next(item for item in quote.order.items if item.item_code == ITEM)
		self.assertAlmostEqual(basket.items[0].rate, flt(line.rate), delta=0.01)

	def test_quote_keeps_its_pricing_rule(self):
		from shop.storefront import quotes

		self.quantity_break(3, 15)
		self.set(allow_quote_requests=1)
		self.basket(3)
		result = quotes.request_quote(customer=BUYER, address=self.home_address)
		quotation = frappe.get_doc("Quotation", result["quote"])
		line = next(row for row in quotation.items if row.item_code == ITEM)
		self.assertEqual(flt(line.discount_percentage), 15)
		quoted = flt(line.rate)
		# staff review the quote in the desk and send it
		quotation.save()
		quotation.submit()
		line = next(row for row in quotation.items if row.item_code == ITEM)
		self.assertEqual(flt(line.rate), quoted)
		# the customer opens the emailed link without signing in
		with self.set_user("Guest"):
			summary = quotes.quote_summary(quotation.name, quotation.shop_access_token)
		self.assertTrue(summary["can_accept"])
		self.assertIn("bank", [method["method"] for method in summary["payment_methods"]])
		order = quotes.make_order(quotation)
		order.insert(ignore_permissions=True)
		order.submit()
		self.assertEqual(flt(order.grand_total), flt(quotation.grand_total))

	def test_a_quote_isnt_accepted_at_other_prices(self):
		from shop.storefront import quotes

		rule = self.quantity_break(3, 15)
		self.set(allow_quote_requests=1)
		self.basket(3)
		result = quotes.request_quote(customer=BUYER, address=self.home_address)
		quotation = frappe.get_doc("Quotation", result["quote"])
		quotation.submit()
		# after the quote is sent, the store raises the price and ends the quantity break
		price = frappe.db.get_value(
			"Item Price", {"item_code": ITEM, "price_list": frappe.get_cached_doc("Shop Settings").price_list}
		)
		frappe.db.set_value("Item Price", price, "price_list_rate", self.price * 2)
		self.addCleanup(frappe.db.set_value, "Item Price", price, "price_list_rate", self.price)
		frappe.db.set_value("Pricing Rule", rule, "disable", 1)

		orders = frappe.db.count("Sales Order")
		with patch("frappe.enqueue") as enqueue, self.set_user("Guest"):
			with self.assertRaisesRegex(frappe.ValidationError, "prices have changed"):
				quotes.accept_quote(quotation.name, quotation.shop_access_token, "bank")
		self.assertEqual(frappe.db.count("Sales Order"), orders)
		staff = enqueue.call_args.kwargs
		self.assertEqual(staff["quotation"], quotation.name)

		quotes.tell_staff_prices_changed(quotation.name, staff["order_total"])
		quotes.tell_staff_prices_changed(quotation.name, staff["order_total"])
		notes = frappe.get_all(
			"Comment", filters={"reference_name": quotation.name, "content": ["like", "%would now cost%"]}
		)
		self.assertEqual(len(notes), 1)

	def test_stock_an_order_waits_for_isnt_sold_again(self):
		from shop.storefront import stock

		left = stock.available_qty(ITEM)
		self.assertGreater(left, 0)
		self.basket(int(left))
		order = self.place()
		self.addCleanup(lambda: frappe.get_doc("Sales Order", order).cancel())
		self.assertEqual(stock.available_qty(ITEM), 0)
		self.assertEqual(stock.availability(ITEM)["stock_state"], "out")
		frappe.db.delete("Shop Cart")
		with self.assertRaisesRegex(frappe.ValidationError, "out of stock"):
			cart.add_item(ITEM)

	def amount_coupon(self, code: str, amount: float, apply_discount_on: str) -> str:
		if not frappe.db.exists("Coupon Code", {"coupon_code": code}):
			rule = frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": f"Test {code}",
					"apply_on": "Transaction",
					"selling": 1,
					"coupon_code_based": 1,
					"rate_or_discount": "Discount Amount",
					"discount_amount": amount,
					"apply_discount_on": apply_discount_on,
					"company": self.company,
					"currency": self.company_currency,
				}
			).insert(ignore_permissions=True)
			frappe.get_doc(
				{
					"doctype": "Coupon Code",
					"coupon_name": code,
					"coupon_code": code,
					"coupon_type": "Promotional",
					"pricing_rule": rule.name,
				}
			).insert(ignore_permissions=True)
		return code

	def test_the_cart_takes_off_what_checkout_takes_off(self):
		coupons = [
			self.free_coupon(),
			self.amount_coupon("TESTNET20", 20, "Net Total"),
			self.amount_coupon("TESTGRAND20", 20, "Grand Total"),
		]
		for prices_include_tax in (1, 0):
			if not prices_include_tax:
				self.without_tax()
			for code in coupons:
				frappe.db.delete("Shop Cart")
				self.basket(1)
				shown = cart.apply_coupon(code)
				quote = totals.compute(cart.resolve_cart(), self.home_address, None, "bank")
				if prices_include_tax:
					self.assertAlmostEqual(shown["total"], quote.total, delta=0.01, msg=code)
				else:
					# without tax the cart shows the order before its tax is added
					self.assertAlmostEqual(shown["total"], flt(quote.order.net_total), delta=0.01, msg=code)

	def test_international_transfer_adds_the_banks_fee(self):
		basket = self.basket(1)
		local = totals.compute(basket, self.abroad_address, None, "bank", self.foreign)
		self.assertEqual([fee.kind for fee in local.fees], ["conversion_fee"])
		swift = totals.compute(cart.resolve_cart(), self.abroad_address, None, "swift", self.foreign)
		self.assertEqual([fee.kind for fee in swift.fees], ["conversion_fee", "transfer_fee"])
		# an export carries no tax, so the fee line is the bank's fee
		self.assertEqual(fee_row(swift, "TEST-TRANSFER-FEE").amount, 6.11)
		self.assertAlmostEqual(swift.total - local.total, 6.11, delta=0.01)

		# the currencies offered stay the same whichever way the shopper pays
		self.assertEqual(
			[row["currency"] for row in totals.payload(swift)["bank_currencies"]],
			[row["currency"] for row in totals.payload(local)["bank_currencies"]],
		)
		routes = totals.payload(swift)["bank_routes"]
		self.assertEqual([route["method"] for route in routes], ["bank", "swift"])
		self.assertIn(totals.money(6.11, self.foreign), routes[1]["label"])

		name = self.place(payment_method="swift", address=self.abroad_address, currency=self.foreign)
		order = frappe.get_doc("Sales Order", name)
		self.assertEqual(order.shop_payment_method, "swift")
		self.assertEqual(totals.order_total(order), swift.total)
		details = payment.bank_instructions(order)["details"]
		self.assertIn("BIC/SWIFT: TESTXX22", details)
		self.assertFalse(
			[line for line in details if line.startswith(totals.branch_code_label(self.foreign))]
		)

	def test_a_bank_accounts_branch_code_is_named_as_the_store_sets(self):
		home = totals.bank_accounts()[0]
		self.assertIn(f"{totals.branch_code_label(home.currency)}: 2", home.details)
		settings = frappe.get_doc("Shop Settings")
		settings.bank_accounts[0].branch_code_label = "Branch number"
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")
		self.assertIn("Branch number: 2", totals.bank_accounts()[0].details)

	def test_with_tax_the_summary_adds_up_and_fees_include_the_tax(self):
		self.without_tax()
		self.set(show_prices_with_tax=1, transfer_fee_item=service("TEST-TRANSFER-FEE", self.company))
		settings = frappe.get_doc("Shop Settings")
		settings.bank_accounts[0].local_transfer_fee = 2
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")
		quote = totals.compute(self.basket(1), self.home_address, None, "bank", self.company_currency)
		shown = totals.payload(quote)
		self.assertEqual([line["kind"] for line in shown["lines"]].count("rounding"), 0)
		self.assertAlmostEqual(sum(line["amount"] for line in shown["lines"]), quote.total, delta=0.001)
		item = next(row for row in quote.order.items if row.item_code == ITEM)
		self.assertEqual(
			shown["items"][0]["formatted_amount"], totals.money(item.amount * 1.15, self.company_currency)
		)
		self.assertIn(totals.money(2.3, self.company_currency), shown["bank_routes"][0]["label"])

	def test_bank_transfer_from_abroad_is_suggested_as_swift(self):
		quote = totals.compute(self.basket(1), self.home_address, None, "bank", self.foreign)
		self.assertEqual(totals.payload(quote)["suggested_bank_method"], "swift")
		quote = totals.compute(cart.resolve_cart(), self.home_address, None, "bank", self.company_currency)
		self.assertEqual(totals.payload(quote)["suggested_bank_method"], "bank")

	def test_swift_needs_the_banks_swift_code(self):
		frappe.db.set_value("Bank", "_Test Shop Bank", "swift_number", None)
		frappe.clear_document_cache("Bank", "_Test Shop Bank")
		self.assertFalse(totals.bank_accounts("swift"))
		self.assertEqual(totals.bank_routes(self.foreign)[0]["method"], "bank")
		self.assertEqual(len(totals.bank_routes(self.foreign)), 1)
		with self.assertRaises(frappe.ValidationError):
			self.basket(1)
			self.place(payment_method="swift", currency=self.foreign)

	def bank_deposit(self, order, deposit, fee, reference):
		account = totals.bank_account(order.currency, order.shop_payment_method).bank_account
		transaction = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"date": nowdate(),
				"bank_account": account,
				"currency": order.currency,
				"deposit": deposit,
				"included_fee": fee,
				"reference_number": reference,
				"transaction_id": frappe.generate_hash(length=12),
			}
		).insert(ignore_permissions=True)
		transaction.submit()
		return transaction

	def test_bank_deposit_pays_the_order_it_names(self):
		self.basket(1)
		name = self.place(payment_method="swift", address=self.abroad_address, currency=self.foreign)
		order = frappe.get_doc("Sales Order", name)
		owed = payment.amount_due(order)
		transaction = self.bank_deposit(order, flt(owed - 6.11, 2), 6.11, f"Order {name}, thanks")

		entry = frappe.get_doc("Payment Entry", payment.pay_from_bank_transaction(transaction.name))
		self.assertAlmostEqual(entry.received_amount, owed, delta=0.01)
		self.assertEqual(
			entry.taxes[0].account_head, frappe.get_cached_doc("Shop Settings").bank_charges_account
		)
		bank_gl = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
		into_bank = frappe.db.sql(
			"""select sum(debit_in_account_currency - credit_in_account_currency) from `tabGL Entry`
			where voucher_no=%s and account=%s and is_cancelled=0""",
			(entry.name, bank_gl),
		)[0][0]
		self.assertAlmostEqual(flt(into_bank), flt(owed - 6.11, 2), delta=0.01)
		self.assertEqual(frappe.db.get_value("Bank Transaction", transaction.name, "status"), "Reconciled")
		self.assertEqual(payment.amount_due(frappe.get_doc("Sales Order", name)), 0)

	def test_short_bank_deposit_leaves_the_balance_owed(self):
		self.basket(1)
		name = self.place(payment_method="swift", address=self.abroad_address, currency=self.foreign)
		order = frappe.get_doc("Sales Order", name)
		owed = payment.amount_due(order)
		transaction = self.bank_deposit(order, flt(owed - 6.11 - 5, 2), 6.11, name)
		with patch("frappe.sendmail") as sendmail:
			payment.pay_from_bank_transaction(transaction.name)
		order.reload()
		self.assertAlmostEqual(payment.amount_due(order), 5, delta=0.02)
		self.assertFalse(payment.is_paid(order))
		self.assertEqual(sendmail.call_args.kwargs["subject"], f"Part payment received for order {name}")
		self.assertIn(
			totals.money(payment.amount_due(order), order.currency), sendmail.call_args.kwargs["message"]
		)

	def rate_moves_to(self, rate):
		from frappe.utils import nowdate

		for source, target, value in (
			(self.foreign, self.company_currency, rate),
			(self.company_currency, self.foreign, 1 / rate),
		):
			filters = {"date": nowdate(), "from_currency": source, "to_currency": target}
			frappe.db.delete("Currency Exchange", filters)
			rate_doc = frappe.get_doc(
				{"doctype": "Currency Exchange", **filters, "exchange_rate": value, "for_selling": 1}
			).insert(ignore_permissions=True)
			self.addCleanup(frappe.db.delete, "Currency Exchange", {"name": rate_doc.name})
		self.addCleanup(lambda: setattr(frappe.local, "cache", {}))
		frappe.local.cache = {}

	def test_a_short_payment_in_another_currency_pays_that_much_of_the_order(self):
		self.basket(1)
		name = self.place(payment_method="bank", address=self.abroad_address, currency=self.foreign)
		order = frappe.get_doc("Sales Order", name)
		owed = payment.amount_due(order)
		# the rate moves before the customer pays, then they send 13.04 less than owed
		self.rate_moves_to(flt(order.conversion_rate) * 1.1)
		transaction = self.bank_deposit(order, flt(owed - 13.04, 2), 0, name)
		with patch("frappe.sendmail"):
			entry = frappe.get_doc("Payment Entry", payment.pay_from_bank_transaction(transaction.name))
		order.reload()
		self.assertAlmostEqual(payment.amount_due(order), 13.04, delta=0.02)
		self.assertFalse(payment.is_paid(order))
		self.assertTrue([row for row in entry.deductions if row.is_exchange_gain_loss])

	def test_a_refund_from_a_bank_account_pays_back_what_the_customer_paid(self):
		self.basket(1)
		name = self.place(payment_method="bank", address=self.abroad_address, currency=self.foreign)
		order = frappe.get_doc("Sales Order", name)
		owed = payment.amount_due(order)
		payment.pay_from_bank_transaction(self.bank_deposit(order, owed, 0, name).name)
		with patch("frappe.sendmail"):
			credit_note = payment.cancel_by_store(name)["credit_note"]
		self.rate_moves_to(flt(order.conversion_rate) * 1.1)
		account = totals.bank_account(self.foreign, "bank").bank_account
		with patch("shop.storefront.emails.send"):
			entry = frappe.get_doc("Payment Entry", payment.refund(name, credit_note, account))
		self.assertEqual((entry.paid_amount, entry.paid_from_account_currency), (owed, self.foreign))

	def test_returning_part_of_an_order_credits_that_part(self):
		from shop.storefront import returns

		account = frappe.db.get_value(
			"Account", {"company": self.company, "root_type": "Income", "is_group": 0}
		)
		self.set(shipping_item=None, shipping_account=account, flat_shipping_rate=10)
		rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "Part return 50 off",
				"apply_on": "Transaction",
				"selling": 1,
				"coupon_code_based": 1,
				"rate_or_discount": "Discount Amount",
				"discount_amount": 50,
				"company": self.company,
				"currency": self.company_currency,
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Pricing Rule", rule.name, force=True)
		coupon = frappe.get_doc(
			{
				"doctype": "Coupon Code",
				"coupon_name": "PARTRETURN",
				"coupon_code": "PARTRETURN",
				"coupon_type": "Promotional",
				"pricing_rule": rule.name,
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Coupon Code", coupon.name, force=True)
		self.basket(2)
		cart.apply_coupon("PARTRETURN")
		name = self.place(currency=self.company_currency)
		order = frappe.get_doc("Sales Order", name)
		payment.pay_from_bank_transaction(self.bank_deposit(order, payment.amount_due(order), 0, name).name)
		invoice = frappe.get_doc("Sales Invoice", payment.invoice_paid_order(order.reload() or order))

		request = frappe._dict(sales_order=name, item_code=ITEM, item_name=ITEM, qty=1, credit_note=None)
		request.db_set = lambda field, value: request.update({field: value})
		returns.credit(request)
		note = frappe.get_doc("Sales Invoice", request.credit_note)
		# half the coupon comes back with one of the two, and the shipping charge isn't refunded
		self.assertEqual(note.discount_amount, -flt(invoice.discount_amount / 2, 2))
		self.assertFalse([tax for tax in note.taxes if tax.charge_type == "Actual"])

	def test_a_deposit_for_a_cancelled_order_is_left_for_staff(self):
		self.basket(1)
		name = self.place(currency=self.company_currency)
		order = frappe.get_doc("Sales Order", name)
		owed = payment.amount_due(order)
		with patch("frappe.sendmail"):
			payment.cancel_by_store(name)
		transaction = self.bank_deposit(order, owed, 0, name)
		self.assertIsNone(payment.pay_from_bank_transaction(transaction.name))
		self.assertTrue(
			frappe.db.exists(
				"Comment", {"reference_name": name, "content": ["like", f"%{transaction.name}%cancelled%"]}
			)
		)

	def test_an_item_with_a_sales_unit_is_sold_in_its_stock_unit(self):
		from shop.storefront import pricing, stock

		if not frappe.db.exists("UOM", "_Test Box of 10"):
			frappe.get_doc(
				{"doctype": "UOM", "uom_name": "_Test Box of 10", "must_be_whole_number": 1}
			).insert()
		item = frappe.get_doc("Item", ITEM)
		item.append("uoms", {"uom": "_Test Box of 10", "conversion_factor": 10})
		item.sales_uom = "_Test Box of 10"
		item.save()

		def restore():
			doc = frappe.get_doc("Item", ITEM)
			doc.sales_uom = None
			doc.uoms = [row for row in doc.uoms if row.uom != "_Test Box of 10"]
			doc.save()

		self.addCleanup(restore)
		shown = pricing.get_price(ITEM)["rate"]
		left = stock.available_qty(ITEM)
		basket = self.basket(int(left))
		row = totals.compute(basket, self.home_address, None, "bank").order.items[0]
		# charged per unit at the price shown, and the stock it takes is what was checked
		self.assertEqual((row.rate, row.stock_qty), (shown, left))

	def test_a_product_bundle_is_limited_by_its_parts_and_ships(self):
		from shop.storefront import shipping, stock

		code = "_TEST-BUNDLE-OF-TWO"
		if not frappe.db.exists("Item", code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": code,
					"item_name": code,
					"item_group": "All Item Groups",
					"stock_uom": "Nos",
					"is_stock_item": 0,
				}
			).insert()
		bundle = frappe.get_doc(
			{"doctype": "Product Bundle", "new_item_code": code, "items": [{"item_code": ITEM, "qty": 2}]}
		).insert()
		self.addCleanup(frappe.delete_doc, "Product Bundle", bundle.name, force=True)
		self.assertTrue(stock.is_stock_item(code))
		self.assertEqual(stock.available_qty(code), stock.available_qty(ITEM) // 2)
		self.assertTrue(shipping.ships(SimpleNamespace(items=[frappe._dict(item_code=code)])))

	def test_a_zero_rated_item_is_charged_its_price_abroad(self):
		from shop.storefront import pricing

		with patch.object(pricing, "item_tax_rate", return_value=0):
			basket = self.basket(1)
			row = totals.compute(basket, self.abroad_address, None, "bank").order.items[0]
		# no tax was in its price at home, so none is taken off for an export
		self.assertAlmostEqual(row.base_rate, self.price, delta=0.01)

	def test_a_guest_sees_the_pricing_rules_everyone_gets(self):
		from shop.storefront import pricing

		rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test everyone 20 off",
				"apply_on": "Item Code",
				"items": [{"item_code": ITEM}],
				"selling": 1,
				"rate_or_discount": "Discount Percentage",
				"discount_percentage": 20,
				"company": self.company,
				"currency": self.company_currency,
			}
		).insert()
		self.addCleanup(frappe.delete_doc, "Pricing Rule", rule.name, force=True)
		self.assertEqual(pricing.get_prices([ITEM], customer=None)[ITEM]["rate"], flt(self.price * 0.8, 2))

	def test_more_than_owed_is_kept_as_the_customers_advance(self):
		self.basket(1)
		name = self.place(currency=self.company_currency)
		order = frappe.get_doc("Sales Order", name)
		owed = payment.amount_due(order)
		transaction = self.bank_deposit(order, flt(owed + 7.8, 2), 0, name)
		entry = frappe.get_doc("Payment Entry", payment.pay_from_bank_transaction(transaction.name))
		# the customer's advance would keep their other orders from being cancelled
		self.addCleanup(entry.cancel)
		self.addCleanup(entry.reload)
		self.addCleanup(transaction.reload)
		self.assertAlmostEqual(entry.received_amount, owed + 7.8, delta=0.01)
		self.assertAlmostEqual(entry.unallocated_amount, 7.8, delta=0.01)
		self.assertEqual(frappe.db.get_value("Bank Transaction", transaction.name, "status"), "Reconciled")
		self.assertTrue(payment.is_paid(frappe.get_doc("Sales Order", name)))
		self.assertTrue(
			frappe.db.exists("Comment", {"reference_name": name, "content": ["like", "%more than owed%"]})
		)

	def test_a_deposit_entered_without_a_date_pays_the_order(self):
		self.basket(1)
		name = self.place(currency=self.company_currency)
		order = frappe.get_doc("Sales Order", name)
		transaction = self.bank_deposit(order, payment.amount_due(order), 0, name)
		transaction.db_set("date", None)
		payment.match_bank_transaction(transaction.name)
		self.assertTrue(payment.is_paid(frappe.get_doc("Sales Order", name)))

	def test_reference_typed_the_bank_way_still_pays_the_order(self):
		self.basket(1)
		name = self.place(currency=self.company_currency)
		order = frappe.get_doc("Sales Order", name)
		typed = name.lower().replace("-", " ")
		transaction = self.bank_deposit(order, payment.amount_due(order), 0, f"payment {typed} thanks")
		self.assertTrue(payment.pay_from_bank_transaction(transaction.name))
		self.assertTrue(payment.is_paid(frappe.get_doc("Sales Order", name)))

	def test_store_orders_use_the_store_naming_series(self):
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		options = frappe.get_meta("Sales Order").get_field("naming_series").options
		setter = {"doc_type": "Sales Order", "field_name": "naming_series", "property": "options"}
		existing = frappe.db.get_value("Property Setter", setter, "value")

		def restore():
			if existing is None:
				frappe.db.delete("Property Setter", setter)
			else:
				frappe.db.set_value("Property Setter", setter, "value", existing)
			frappe.clear_cache(doctype="Sales Order")

		make_property_setter("Sales Order", "naming_series", "options", f"{options}\nTSO-.#####", "Text")
		frappe.clear_cache(doctype="Sales Order")
		self.addCleanup(restore)
		self.set(order_naming_series="TSO-.#####")
		self.addCleanup(self.set, order_naming_series=None)
		self.basket(1)
		self.assertTrue(self.place().startswith("TSO-"))
		with self.assertRaises(frappe.ValidationError):
			settings = frappe.get_doc("Shop Settings")
			settings.order_naming_series = "NOT-IN-THE-LIST-.###"
			settings.save()

	def test_deposit_without_one_order_reference_is_left_for_staff(self):
		self.basket(1)
		name = self.place(currency=self.company_currency)
		order = frappe.get_doc("Sales Order", name)
		transaction = self.bank_deposit(order, payment.amount_due(order), 0, "Invoice 123")
		self.assertIsNone(payment.pay_from_bank_transaction(transaction.name))
		self.assertFalse(payment.is_paid(frappe.get_doc("Sales Order", name)))

	def test_coupon_is_charged_as_quoted_when_tax_is_added(self):
		self.without_tax()
		self.basket(1, "SHOP-DEMO-011")
		cart.apply_coupon("WELCOME10")
		quote = totals.compute(cart.resolve_cart(), self.home_address, None, "bank")
		order = frappe.get_doc("Sales Order", self.place(expected_total=quote.total))
		self.assertEqual(totals.order_total(order), quote.total)
		self.assertEqual(order.coupon_code, frappe.db.get_value("Coupon Code", {"coupon_code": "WELCOME10"}))
		# the coupon's Pricing Rule says what the discount is taken from
		rule = frappe.db.get_value("Coupon Code", order.coupon_code, "pricing_rule")
		on = frappe.db.get_value("Pricing Rule", rule, "apply_discount_on")
		self.assertEqual(order.apply_discount_on, on)
		base = (
			order.net_total + order.discount_amount
			if on == "Net Total"
			else order.grand_total + order.discount_amount
		)
		self.assertAlmostEqual(order.discount_amount, flt(base * 0.1, 2), delta=0.01)

	def test_flat_shipping_on_the_shipping_account_is_charged_as_quoted(self):
		self.without_tax()
		account = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Chargeable", "is_group": 0}
		) or frappe.db.get_value("Account", {"company": self.company, "root_type": "Income", "is_group": 0})
		self.set(shipping_item=None, shipping_account=account, flat_shipping_rate=10)
		quote = totals.compute(self.basket(1), self.home_address, None, "bank")
		self.assertEqual(line(quote, "shipping"), [10.0])
		order = frappe.get_doc("Sales Order", self.place(expected_total=quote.total))
		self.assertEqual(totals.order_total(order), quote.total)

	def zero_rate(self, item_code):
		tax_account = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Tax", "is_group": 0}
		)
		title = "_Test Shop Zero Rated"
		if not frappe.db.exists("Item Tax Template", {"title": title, "company": self.company}):
			frappe.get_doc(
				{
					"doctype": "Item Tax Template",
					"title": title,
					"company": self.company,
					"taxes": [{"tax_type": tax_account, "tax_rate": 0}],
				}
			).insert(ignore_permissions=True)
		item_tax = frappe.db.get_value("Item Tax Template", {"title": title, "company": self.company})
		item = frappe.get_doc("Item", item_code)
		if item_tax not in [row.item_tax_template for row in item.taxes]:
			item.append("taxes", {"item_tax_template": item_tax})
			item.save(ignore_permissions=True)
		if hasattr(frappe.local, "shop_item_tax_rates"):
			del frappe.local.shop_item_tax_rates

	def test_an_item_tax_template_is_charged_as_erpnext_charges_it(self):
		self.without_tax()
		self.zero_rate("SHOP-DEMO-011")
		self.basket(1)
		quote = totals.compute(self.basket(1, "SHOP-DEMO-011"), self.home_address, None, "bank")
		taxed = sum(row.net_amount for row in quote.order.items if row.item_code == ITEM)
		self.assertAlmostEqual(line(quote, "tax")[0], taxed * 0.15, delta=0.01)
		order = frappe.get_doc("Sales Order", self.place(expected_total=quote.total))
		self.assertEqual(totals.order_total(order), quote.total)

	def test_a_zero_rated_item_is_shown_without_tax(self):
		from shop.storefront import pricing

		self.without_tax()
		self.set(show_prices_with_tax=1)
		self.zero_rate("SHOP-DEMO-011")
		self.assertEqual(pricing.item_tax_rate("SHOP-DEMO-011"), 0)
		self.assertEqual(pricing.item_tax_rate(ITEM), pricing.domestic_tax_rate())
		shown = pricing.display_fields(100, "SHOP-DEMO-011")
		self.assertEqual(shown["display"], pricing.display_amount(100, 0))
		self.assertIsNone(shown["display_excl"])

		self.basket(1)
		basket = self.basket(1, "SHOP-DEMO-011")
		in_cart = {row["item_code"]: row for row in cart.cart_payload(basket)["items"]}
		zero = in_cart["SHOP-DEMO-011"]
		self.assertEqual(zero["formatted_amount"], pricing.display_amount(zero["amount"], 0))
		taxed = in_cart[ITEM]
		self.assertEqual(taxed["formatted_amount"], pricing.display_amount(taxed["amount"]))

		quote = totals.compute(basket, self.home_address, None, "bank")
		payload = totals.payload(quote)
		amounts = {row["item_code"]: row["formatted_amount"] for row in payload["items"]}
		rows = {row.item_code: row for row in quote.order.items}
		self.assertEqual(amounts["SHOP-DEMO-011"], totals.money(rows["SHOP-DEMO-011"].amount, quote.currency))
		self.assertEqual(
			amounts[ITEM],
			totals.money(flt(rows[ITEM].amount) * (1 + pricing.domestic_tax_rate() / 100), quote.currency),
		)
		self.assertEqual(flt(sum(line["amount"] for line in payload["lines"]), 2), quote.total)

	def test_rounded_total_is_what_the_customer_pays(self):
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		# ERPNext's Global Defaults sets this default on each transaction type
		make_property_setter(
			"Sales Order", "disable_rounded_total", "default", 0, "Text", validate_fields_for_doctype=False
		)
		self.addCleanup(frappe.clear_cache, doctype="Sales Order")
		quote = totals.compute(self.basket(1), self.home_address, None, "gateway")
		self.assertEqual(quote.total, flt(quote.order.rounded_total))
		shown = totals.payload(quote)
		self.assertAlmostEqual(sum(row["amount"] for row in shown["lines"]), quote.total, delta=0.001)

	# --- shipping ----------------------------------------------------------------

	def test_provider_rates_are_charged_as_quoted_with_tax(self):
		with patch("frappe.get_hooks", side_effect=hooks_with([TEST_PROVIDER])):
			quote = totals.compute(self.basket(1), self.home_address, None, "bank")
			self.assertEqual(quote.shipping["id"], "test:courier")
			self.assertEqual(line(quote, "shipping"), [13.80])  # 12.00 plus 15% tax, as prices include tax
			order = frappe.get_doc("Sales Order", self.place(shipping_option="test:courier"))
		shipping_line = [row for row in order.items if row.item_code == "TEST-SHIPPING"]
		self.assertEqual(shipping_line[0].rate, 13.80)
		self.assertIn("test:courier", order.shop_shipping_option)

	def test_prices_without_tax_get_tax_added_and_the_invoice_matches(self):
		self.without_tax()
		self.set(invoice_paid_orders=1)
		with patch("frappe.get_hooks", side_effect=hooks_with([TEST_PROVIDER])):
			quote = totals.compute(self.basket(1), self.home_address, "test:courier", "bank")
			self.assertEqual(line(quote, "subtotal"), [flt(self.price, 2)])
			self.assertEqual(line(quote, "shipping"), [12.0])
			self.assertEqual(line(quote, "tax"), [flt((self.price + 12.0) * 0.15, 2)])
			name = self.place(shipping_option="test:courier", expected_total=quote.total)
		order = frappe.get_doc("Sales Order", name)
		rows = {row.item_code: row for row in order.items}
		self.assertEqual(rows["TEST-SHIPPING"].rate, 12.0)
		self.assertEqual(rows["TEST-SHIPPING"].description, "Test Courier")
		with patch("frappe.sendmail"):
			self.pay(name)
		invoice = frappe.get_doc("Sales Invoice", payment.order_invoice(name))
		self.assertEqual(
			{row.item_code: row.rate for row in invoice.items},
			{ITEM: flt(self.price, 2), "TEST-SHIPPING": 12.0},
		)
		self.assertEqual(totals.order_total(invoice), quote.total)
		self.assertEqual(flt(invoice.outstanding_amount), 0)

	def test_a_coupon_shown_with_tax_is_the_discount_erpnext_gives(self):
		self.without_tax()
		self.set(show_prices_with_tax=1)
		self.basket(1, "SHOP-DEMO-011")
		cart.apply_coupon("WELCOME10")
		quote = totals.compute(cart.resolve_cart(), self.home_address, None, "bank")
		lines = totals.payload(quote)["lines"]
		discount = next(line for line in lines if line["kind"] == "discount")
		expected = flt(quote.order.discount_amount)
		if quote.order.apply_discount_on == "Net Total":
			expected = expected * flt(quote.order.grand_total) / flt(quote.order.net_total)
		self.assertAlmostEqual(-discount["amount"], expected, delta=0.02)
		self.assertAlmostEqual(sum(line["amount"] for line in lines), quote.total, delta=0.001)

	def test_lines_can_be_shown_with_tax(self):
		self.without_tax()
		self.set(show_prices_with_tax=1)
		with patch("frappe.get_hooks", side_effect=hooks_with([TEST_PROVIDER])):
			quote = totals.compute(self.basket(1), self.home_address, "test:courier", "bank")
		shown = totals.payload(quote)
		self.assertNotIn("tax", [row["kind"] for row in shown["lines"]])
		self.assertEqual(flt(sum(row["amount"] for row in shown["lines"]), 2), quote.total)
		self.assertEqual([row["amount"] for row in shown["lines"] if row["kind"] == "shipping"], [13.80])
		self.assertIn(totals.money(line(quote, "tax")[0], quote.currency), " ".join(shown["notes"]))
		self.assertEqual(
			[option["formatted"] for option in shown["shipping_options"]],
			[totals.money(13.80, quote.currency)],
		)

	def test_prices_are_shown_as_the_price_list_has_them_unless_shown_with_tax(self):
		from frappe.utils import fmt_money

		from shop.storefront import pricing

		self.without_tax()
		home = self.company_currency
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		self.assertEqual(pricing.display_price(100), f"{fmt_money(100, currency=home)} {home}")
		self.assertIsNone(pricing.display_price_without_tax(100))
		self.set(show_prices_with_tax=1)
		self.assertEqual(pricing.display_price(100), f"{fmt_money(115, currency=home)} {home} incl. VAT")
		self.assertEqual(
			pricing.display_price_without_tax(100), f"{fmt_money(100, currency=home)} {home} excl. VAT"
		)
		self.with_currency_cookie(self.foreign)
		rate = pricing.display_rate(self.foreign)
		self.assertEqual(
			pricing.display_price(100),
			f"≈ {fmt_money(100 * rate, currency=self.foreign)} {self.foreign} excl. VAT",
		)
		self.assertIsNone(pricing.display_price_without_tax(100))
		self.assertEqual(
			pricing.display_price(100, 0), f"≈ {fmt_money(100 * rate, currency=self.foreign)} {self.foreign}"
		)
		self.set(other_currencies_with_tax=1)
		self.assertEqual(
			pricing.display_price(100),
			f"≈ {fmt_money(115 * rate, currency=self.foreign)} {self.foreign} incl. VAT",
		)

	def test_currency_code_is_shown_only_when_the_store_has_several(self):
		from frappe.utils import fmt_money

		from shop.storefront import pricing

		settings = frappe.get_doc("Shop Settings")
		settings.bank_accounts = settings.bank_accounts[:1]
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")
		self.assertEqual(pricing.display_amount(100), fmt_money(100, currency=self.company_currency))

	def test_carrier_price_with_tax_is_the_stores_cost_wherever_the_parcel_goes(self):
		self.without_tax()
		with patch(
			"frappe.get_hooks", side_effect=hooks_with(["shop.tests.test_checkout_totals.rates_with_tax"])
		):
			quote = totals.compute(self.basket(1), self.home_address, None, "bank")
			self.assertEqual(line(quote, "shipping"), [12.0])
			self.assertEqual(grand(quote), flt((self.price + 12.0) * 1.15, 2))
			export = totals.compute(
				cart.resolve_cart(), self.abroad_address, None, "bank", self.company_currency
			)
		# a carrier charges no tax on a parcel sent abroad: all of its price is what the store pays,
		# and the export order charges it in full, with no tax
		self.assertEqual(line(export, "shipping"), [13.8])
		self.assertEqual(export.order.items[0].rate, flt(self.price, 2))
		self.assertEqual(line(export, "tax"), [])
		self.assertEqual(grand(export), flt(self.price + 13.8, 2))

	def test_a_store_with_tax_in_its_prices_charges_a_carriers_export_price_in_full(self):
		# setUp's store includes its 15% tax in its prices
		with patch(
			"frappe.get_hooks", side_effect=hooks_with(["shop.tests.test_checkout_totals.rates_with_tax"])
		):
			home = totals.compute(self.basket(1), self.home_address, None, "bank")
			export = totals.compute(
				cart.resolve_cart(), self.abroad_address, None, "bank", self.company_currency
			)
		self.assertEqual(line(home, "shipping"), [13.8])
		self.assertEqual(line(export, "shipping"), [13.8])

	def test_no_rates_means_no_order_and_says_why(self):
		with patch("frappe.get_hooks", side_effect=hooks_with([TEST_PROVIDER])):
			self.basket(1)
			address = dict(self.abroad_address, country="Antarctica")
			quote = totals.compute(cart.resolve_cart(), address, None, "bank")
			self.assertIsNone(quote.shipping)
			self.assertEqual(quote.shipping_messages, ["We don't ship there"])
			with self.assertRaises(frappe.ValidationError):
				self.place(address=address)

	def test_a_busy_shipping_app_is_asked_again(self):
		BUSY["busy"] = True
		with patch(
			"frappe.get_hooks", side_effect=hooks_with(["shop.tests.test_checkout_totals.busy_then_rates"])
		):
			self.basket(1)
			first = totals.compute(cart.resolve_cart(), self.home_address, None, "bank")
			self.assertIsNone(first.shipping)
			second = totals.compute(cart.resolve_cart(), self.home_address, None, "bank")
			self.assertEqual(second.shipping["id"], "test:courier")

	def test_a_service_needs_no_delivery(self):
		from shop.storefront import shipping

		services = frappe.get_doc(
			{
				"doctype": "Shop Cart",
				"items": [{"item_code": service("TEST-INSTALL", self.company), "qty": 1}],
			}
		)
		with patch("frappe.get_hooks", side_effect=hooks_with([TEST_PROVIDER])):
			options = shipping.get_options(services, shipping.normalize_address(self.home_address), 100)
		self.assertEqual(
			[(o["label"], o["amount"]) for o in options["options"]], [("No delivery needed", 0.0)]
		)

	def test_switched_off_provider_means_free_shipping(self):
		with patch(
			"frappe.get_hooks", side_effect=hooks_with(["shop.tests.test_checkout_totals.inactive_rates"])
		):
			quote = totals.compute(self.basket(1), self.home_address, None, "bank")
			self.assertEqual(quote.shipping["amount"], 0)

	def test_free_shipping_threshold_follows_the_coupon(self):
		account = frappe.db.get_value(
			"Account", {"company": self.company, "root_type": "Income", "is_group": 0}
		)
		self.set(
			shipping_item=None,
			shipping_account=account,
			flat_shipping_rate=10,
			free_shipping_above=self.price,
		)
		quote = totals.compute(self.basket(1), self.home_address, None, "bank")
		self.assertEqual(line(quote, "shipping"), [])
		cart.apply_coupon("WELCOME10")
		quote = totals.compute(cart.resolve_cart(), self.home_address, None, "bank")
		self.assertEqual(line(quote, "shipping"), [10.0])

	# --- order rules ---------------------------------------------------------------

	def test_terms_must_be_accepted_and_are_recorded(self):
		from shop.storefront import terms

		self.set(require_terms=1, terms_url="", terms_and_conditions=terms_record())
		self.basket(1)
		with self.assertRaises(frappe.ValidationError):
			self.place()
		order = frappe.get_doc("Sales Order", self.place(accept_terms=1, business_buyer=1))
		self.assertEqual(order.shop_terms_version, terms.version())
		self.assertTrue(order.shop_terms_version.startswith("_Test Store Terms ("))
		self.assertTrue(order.shop_terms_accepted_on)
		# ERPNext fills in the terms' text for the order when it prints it
		self.assertEqual(order.tc_name, "_Test Store Terms")
		order.set_missing_terms()
		self.assertIn(f"Terms for {order.customer_name}", order.terms)
		self.assertTrue(terms.url().endswith("/terms"))
		self.assertEqual(order.shop_business_buyer, 1)

	def test_changed_total_stops_the_order(self):
		self.basket(1)
		with self.assertRaises(frappe.ValidationError):
			self.place(expected_total=1)

	def test_a_cart_is_ordered_once(self):
		self.basket(1)
		basket = cart.resolve_cart()
		self.place()
		with self.assertRaises(frappe.ValidationError):
			checkout.lock_cart(basket)

	def test_a_product_without_a_price_cant_be_ordered(self):
		price = frappe.db.get_value(
			"Item Price", {"item_code": ITEM, "price_list": frappe.get_cached_doc("Shop Settings").price_list}
		)
		frappe.db.set_value("Item Price", price, "price_list_rate", 0)
		self.addCleanup(frappe.db.set_value, "Item Price", price, "price_list_rate", self.price)
		self.basket(1)
		with self.assertRaises(frappe.ValidationError):
			self.place()

	def test_a_guest_must_sign_in_to_order_for_an_account(self):
		from shop.storefront import accounts

		email = "has.account@example.com"
		if not frappe.db.exists("User", email):
			accounts.register(full_name="Has Account", email=email, accept_terms=1)
		self.basket(1)
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.ValidationError):
			checkout.place_order(
				customer={"email": email, "full_name": "Someone"},
				address=self.home_address,
				payment_method="cod",
			)

	def test_unpaid_orders_are_cancelled_only_when_the_store_wants_it(self):
		self.basket(1)
		name = self.place()
		frappe.db.set_value("Sales Order", name, "shop_payment_due", add_days(nowdate(), -1))
		payment.cancel_overdue_orders()
		self.assertEqual(frappe.db.get_value("Sales Order", name, "docstatus"), 1)
		self.set(cancel_unpaid_orders=1)
		with patch("frappe.sendmail") as sendmail, patch("frappe.db.commit"):
			payment.cancel_overdue_orders()
		self.assertEqual(frappe.db.get_value("Sales Order", name, "docstatus"), 2)
		self.assertIn([BUYER["email"]], [call.kwargs["recipients"] for call in sendmail.call_args_list])

	def test_orders_the_daily_cancel_leaves_alone(self):
		from erpnext.selling.doctype.sales_order.sales_order import update_status

		self.set(cancel_unpaid_orders=1)
		self.basket(1)
		no_date = self.place()
		frappe.db.set_value("Sales Order", no_date, "shop_payment_due", None)
		self.basket(1)
		on_hold = self.place()
		frappe.db.set_value("Sales Order", on_hold, "shop_payment_due", add_days(nowdate(), -1))
		update_status("On Hold", on_hold)
		self.basket(1)
		sent = self.place()
		frappe.db.set_value("Sales Order", sent, "shop_payment_due", add_days(nowdate(), -1))
		frappe.get_doc(
			{"doctype": "Shop Fulfillment", "sales_order": sent, "provider": "manual", "status": "Accepted"}
		).insert(ignore_permissions=True)
		self.basket(1)
		deposited = self.place()
		frappe.db.set_value("Sales Order", deposited, "shop_payment_due", add_days(nowdate(), -1))
		order = frappe.get_doc("Sales Order", deposited)
		# the deposit is in the bank, not matched yet (here: in another currency than the order)
		transaction = self.bank_deposit(order, payment.amount_due(order), 0, deposited)
		self.assertGreater(
			flt(frappe.db.get_value("Bank Transaction", transaction.name, "unallocated_amount")), 0
		)

		with patch("frappe.sendmail"), patch("frappe.db.commit"):
			payment.cancel_overdue_orders()
		for name in (no_date, on_hold, sent, deposited):
			self.assertEqual(frappe.db.get_value("Sales Order", name, "docstatus"), 1, name)

	def test_a_copied_or_amended_order_doesnt_keep_the_checkout(self):
		self.basket(1)
		order = frappe.get_doc("Sales Order", self.place())
		# as Desk's Duplicate copies it
		copy = frappe.copy_doc(order, ignore_no_copy=False)
		self.assertFalse(copy.get("shop_payment_due"))
		self.assertFalse(copy.get("shop_payment_method"))
		amended = frappe.copy_doc(order)
		amended.shop_payment_due = order.shop_payment_due
		amended.amended_from = order.name
		payment.forget_checkout_on_amend(amended)
		self.assertFalse(amended.shop_payment_due)

	def test_unpaid_bank_order_is_not_cancelled_before_its_due_date(self):
		self.basket(1)
		name = self.place()
		self.assertFalse(payment.cancel_if_unpaid(name))

	def test_an_order_is_kept_while_the_customer_has_an_unmatched_payment(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		self.set(cancel_unpaid_orders=1)
		self.basket(1)
		name = self.place()
		order = frappe.get_doc("Sales Order", name)
		frappe.db.set_value("Sales Order", name, "shop_payment_due", add_days(nowdate(), -1))
		# staff record the deposit from the bank without linking it to the order
		entry = get_payment_entry("Sales Order", name)
		entry.references = []
		entry.reference_no, entry.reference_date = "BANK-DEPOSIT", nowdate()
		entry.insert(ignore_permissions=True)
		entry.submit()
		self.addCleanup(entry.cancel)
		self.assertFalse(payment.cancel_if_unpaid(name))
		self.assertEqual(frappe.db.get_value("Sales Order", name, "docstatus"), 1)
		# the next run doesn't say it again
		self.assertFalse(payment.cancel_if_unpaid(name))
		self.assertEqual(
			frappe.db.count("Comment", {"reference_name": order.name, "content": ["like", "%not matched%"]}),
			1,
		)

	def test_a_part_paid_order_past_its_date_is_chased_once_not_cancelled(self):
		self.set(cancel_unpaid_orders=1)
		self.basket(1)
		name = self.place(currency=self.company_currency)
		order = frappe.get_doc("Sales Order", name)
		transaction = self.bank_deposit(order, flt(payment.amount_due(order) / 2, 2), 0, name)
		with patch("frappe.sendmail"):
			entry = payment.pay_from_bank_transaction(transaction.name)
		self.addCleanup(lambda: frappe.get_doc("Payment Entry", entry).cancel())
		frappe.db.set_value("Sales Order", name, "shop_payment_due", add_days(nowdate(), -1))
		with patch("frappe.sendmail") as sendmail:
			self.assertFalse(payment.cancel_if_unpaid(name))
			self.assertFalse(payment.cancel_if_unpaid(name))
		self.assertEqual(frappe.db.get_value("Sales Order", name, "docstatus"), 1)
		self.assertEqual(sendmail.call_count, 1)
		self.assertEqual(sendmail.call_args.kwargs["subject"], f"Part payment received for order {name}")
		self.assertEqual(
			frappe.db.count("Comment", {"reference_name": name, "content": ["like", "%pay-by date%"]}), 1
		)
		self.assertEqual(
			payment.bank_instructions(frappe.get_doc("Sales Order", name))["due_note"],
			"Please pay the rest as soon as you can.",
		)

	def test_a_customer_who_left_the_payment_page_is_reminded_once(self):
		from frappe.utils import add_to_date, now_datetime

		self.basket(1)
		name = self.place(payment_method="cod")
		frappe.db.set_value(
			"Sales Order",
			name,
			{
				"shop_payment_method": totals.GATEWAY,
				"shop_payment_due": add_days(nowdate(), 1),
				"creation": add_to_date(now_datetime(), hours=-2),
			},
		)
		with (
			patch("shop.storefront.orders.pay_url", return_value="https://pay.example.com/x"),
			patch("frappe.sendmail") as sendmail,
		):
			payment.remind_unpaid_online_orders()
			payment.remind_unpaid_online_orders()
		mine = [c for c in sendmail.call_args_list if c.kwargs.get("reference_name") == name]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0].kwargs["subject"], f"Your order {name} is waiting for payment")
		self.assertIn("https://pay.example.com/x", mine[0].kwargs["message"])

	def test_store_emails_are_editable_email_templates(self):
		from shop.storefront import emails

		emails.ensure_templates()
		for name, *_rest in emails.TEMPLATES.values():
			self.assertTrue(frappe.db.exists("Email Template", name), name)
		template_doc = frappe.get_doc("Email Template", "Shop: Order Cancelled")
		template_doc.subject = "Order {{ doc.name }} was cancelled ({{ store_name }})"
		template_doc.save(ignore_permissions=True)
		self.basket(1)
		name = self.place()
		frappe.db.set_value("Sales Order", name, "shop_payment_due", add_days(nowdate(), -1))
		with patch("frappe.sendmail") as sendmail:
			payment.cancel_if_unpaid(name)
		kwargs = sendmail.call_args.kwargs
		self.assertTrue(kwargs["subject"].startswith(f"Order {name} was cancelled ("))
		self.assertEqual((kwargs["reference_doctype"], kwargs["reference_name"]), ("Sales Order", name))
		emails.ensure_templates()  # an edited template is never overwritten
		self.assertEqual(
			frappe.db.get_value("Email Template", "Shop: Order Cancelled", "subject"), template_doc.subject
		)

	def test_unedited_email_templates_follow_new_wording(self):
		from shop.storefront import emails

		name, _doctype, subject, _body = emails.TEMPLATES["order_shipped"]
		subject = str(subject)
		frappe.delete_doc("Email Template", name, force=True, ignore_permissions=True)
		old = dict(emails.TEMPLATES)
		emails.TEMPLATES["order_shipped"] = (name, _doctype, "Old wording {{ doc.name }}", "<p>old</p>")
		try:
			emails.ensure_templates()
		finally:
			emails.TEMPLATES.clear()
			emails.TEMPLATES.update(old)
		self.assertEqual(frappe.db.get_value("Email Template", name, "subject"), "Old wording {{ doc.name }}")
		emails.ensure_templates()  # the store's wording changed and staff never edited it
		self.assertEqual(frappe.db.get_value("Email Template", name, "subject"), subject)

		edited = frappe.get_doc("Email Template", name)
		edited.response_html = "<p>Our own words</p>"
		edited.save(ignore_permissions=True)
		emails.TEMPLATES["order_shipped"] = (name, _doctype, "Newer wording", "<p>newer</p>")
		try:
			emails.ensure_templates()
		finally:
			emails.TEMPLATES.clear()
			emails.TEMPLATES.update(old)
		self.assertEqual(frappe.db.get_value("Email Template", name, "response_html"), "<p>Our own words</p>")

		# made before the wording was recorded, and never saved again
		frappe.db.set_global(emails.DEFAULTS_KEY, "{}")
		created = frappe.db.get_value("Email Template", name, "creation")
		frappe.db.set_value(
			"Email Template", name, {"subject": "Before", "modified": created}, update_modified=False
		)
		emails.ensure_templates()
		self.assertEqual(frappe.db.get_value("Email Template", name, "subject"), subject)

	def test_shopper_text_is_escaped_in_emails(self):
		from shop.storefront import emails

		doc = frappe._dict(doctype="Lead", name="X", company_name="<b>Evil</b> Ltd", country="")
		_subject, body = emails.render("trade_application_declined", doc, reason="<script>x</script>")
		self.assertNotIn("<script>", body)
		self.assertNotIn("<b>Evil</b>", body)

	def test_paid_bank_order_is_not_cancelled(self):
		self.basket(1)
		name = self.place()
		self.pay(name)
		frappe.db.set_value("Sales Order", name, "shop_payment_due", add_days(nowdate(), -1))
		self.assertTrue(payment.is_paid(frappe.get_doc("Sales Order", name)))
		self.assertFalse(payment.cancel_if_unpaid(name))

	def test_paid_order_is_invoiced_when_the_store_invoices_paid_orders(self):
		self.basket(1)
		name = self.place()
		with patch("frappe.sendmail"):
			self.pay(name)
		self.assertFalse(payment.order_invoice(name))
		self.set(invoice_paid_orders=1)
		self.basket(1)
		name = self.place()
		self.assertFalse(payment.order_invoice(name))  # not before payment
		with patch("frappe.sendmail"):
			entry = self.pay(name)
		invoice = frappe.get_doc("Sales Invoice", payment.order_invoice(name))
		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(flt(invoice.outstanding_amount), 0)
		self.assertEqual(invoice.status, "Paid")
		self.assertEqual([a.reference_name for a in invoice.advances], [entry.name])

	def test_part_paid_order_is_not_invoiced(self):
		self.set(invoice_paid_orders=1)
		self.basket(1)
		name = self.place()
		with patch("frappe.sendmail"):
			self.pay(name, amount=1)
		self.assertFalse(payment.order_invoice(name))

	def test_a_free_order_is_paid_when_placed(self):
		self.set(invoice_paid_orders=1)
		self.basket(1)
		cart.apply_coupon(self.free_coupon())
		self.assertEqual(totals.compute(cart.resolve_cart(), self.home_address, None, "gateway").fees, [])
		with patch("frappe.sendmail"):
			name = self.place()
		order = frappe.get_doc("Sales Order", name)
		self.assertEqual(totals.order_total(order), 0)
		self.assertTrue(payment.is_paid(order))
		self.assertTrue(payment.order_invoice(name))

	def test_invoice_pdf_needs_the_customer_or_the_order_link(self):
		from shop.storefront import accounts

		self.set(invoice_paid_orders=1)
		self.basket(1)
		name = self.place()
		with patch("frappe.sendmail"):
			self.pay(name)
		invoice = payment.order_invoice(name)
		token = frappe.db.get_value("Shop Cart", {"sales_order": name}, "token")
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				accounts.invoice_pdf(invoice)
			with self.assertRaises(frappe.PermissionError):
				accounts.invoice_pdf(invoice, order=name, token="wrong")
			with patch("frappe.get_print", return_value=b"%PDF") as get_print:
				accounts.invoice_pdf(invoice, order=name, token=token)
			self.assertEqual(
				get_print.call_args.kwargs["print_format"],
				frappe.get_meta("Sales Invoice").default_print_format or None,
			)
		finally:
			frappe.set_user("Administrator")

	def test_overseas_bank_transfer_suggests_the_buyers_currency(self):
		quote = totals.compute(self.basket(1), self.abroad_address, None, "bank")
		self.assertEqual(
			quote.currency, self.foreign if self.other == "United States" else self.company_currency
		)

	def with_currency_cookie(self, currency):
		from werkzeug.test import EnvironBuilder
		from werkzeug.wrappers import Request

		builder = EnvironBuilder(path="/store/products", headers={"Cookie": f"shop_currency={currency}"})
		frappe.local.request = Request(builder.get_environ())
		self.addCleanup(
			lambda: delattr(frappe.local, "request") if hasattr(frappe.local, "request") else None
		)
		if hasattr(frappe.local, "shop_display_rates"):
			delattr(frappe.local, "shop_display_rates")

	def test_prices_show_the_store_currency_by_default(self):
		from shop.storefront import pricing

		self.assertEqual(pricing.display_currencies(), [self.company_currency, self.foreign])
		self.assertTrue(pricing.display_amount(100).endswith(f" {self.company_currency}"))
		self.assertNotIn("≈", pricing.display_amount(100))

	def test_picked_currency_shows_approximate_prices_and_leads_bank_transfer(self):
		from shop.storefront import pricing

		basket = self.basket(1)
		self.with_currency_cookie(self.foreign)
		shown = pricing.display_amount(100)
		self.assertTrue(shown.startswith("≈ ") and shown.endswith(f" {self.foreign}"), shown)
		quote = totals.compute(basket, self.home_address, None, "bank")
		self.assertEqual(quote.currency, self.foreign)
		online = totals.payload(totals.compute(basket, self.home_address, None, "gateway"))
		self.assertEqual(online["currency"], self.company_currency)
		self.assertTrue(any(self.foreign in note for note in online["notes"]))

	def test_unknown_currency_cookie_is_ignored(self):
		from shop.storefront import pricing

		self.with_currency_cookie("XYZ")
		self.assertEqual(pricing.display_currency(), self.company_currency)
		with self.assertRaises(frappe.ValidationError):
			pricing.set_currency("XYZ")

	def test_a_customers_currency_choice_leaves_their_billing_currency(self):
		from shop.storefront import accounts, pricing

		email = "currency.keeper@example.com"
		if not frappe.db.exists("User", email):
			accounts.register(full_name="Currency Keeper", email=email, accept_terms=1)
		frappe.set_user(email)
		try:
			if hasattr(frappe.local, "shop_session_customer"):
				delattr(frappe.local, "shop_session_customer")
			frappe.local.cookie_manager = frappe.auth.CookieManager()
			party = pricing.session_customer()
			billing = frappe.db.get_value("Customer", party, "default_currency")
			pricing.set_currency(self.foreign)
			self.assertEqual(frappe.local.cookie_manager.cookies["shop_currency"]["value"], self.foreign)
			self.assertEqual(frappe.db.get_value("Customer", party, "default_currency"), billing)
			self.with_currency_cookie(self.foreign)
			self.assertEqual(pricing.display_currency(), self.foreign)
		finally:
			frappe.set_user("Administrator")

	def test_charge_lines_are_not_products(self):
		self.assertTrue(totals.is_charge_item("TEST-CARD-FEE"))
		self.assertFalse(totals.is_charge_item(ITEM))

	def test_tax_short_names(self):
		self.assertEqual(totals.tax_name("GST @ 15.0"), "GST")
		self.assertEqual(totals.tax_name("VAT 20% (included)"), "VAT")
		self.assertEqual(totals.tax_name("Sales Tax 8.25%"), "Sales Tax")


original_hooks = frappe.get_hooks


def hooks_with(providers):
	def get_hooks(hook=None, *args, **kwargs):
		if hook == "shop_shipping_rate_providers":
			return providers
		return original_hooks(hook, *args, **kwargs)

	return get_hooks
