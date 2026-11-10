"""Trade accounts: sign-up with terms, applications and approval, customer prices, paying on
account, and quotes accepted online."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from shop.api.settings import GATEWAY_FIELDS
from shop.storefront import accounts, cart, checkout, pricing, quotes, totals
from shop.tests.utils import fresh_request, gateway, service

ITEM = "SHOP-DEMO-003"
ADDRESS = {"address_line1": "12 Industrial Way", "city": "Town", "pincode": "3204"}


def ensure(doctype, name, values):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
	return name


def lead_for(email: str) -> str:
	return frappe.db.get_value("Lead", {"email_id": email})


class TestTradeAccounts(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()
		for name in ("shop_session_customer", "shop_customer_rates"):
			if hasattr(frappe.local, name):
				delattr(frappe.local, name)
		self.settings = frappe.get_doc("Shop Settings")
		from shop.tests.utils import terms_record

		self.original = {
			f: self.settings.get(f)
			for f in (
				"require_terms",
				"terms_and_conditions",
				"card_fee_item",
			)
		}
		self.original_gateways = [
			{f: row.get(f) for f in GATEWAY_FIELDS} for row in self.settings.payment_gateways
		]
		frappe.db.set_single_value(
			"Shop Settings", {"require_terms": 1, "terms_and_conditions": terms_record()}
		)
		frappe.clear_cache(doctype="Shop Settings")
		self.address = dict(
			ADDRESS, country=frappe.get_cached_value("Company", self.settings.company, "country")
		)
		currency = self.settings.currency
		self.retail = flt(
			frappe.db.get_value(
				"Item Price", {"item_code": ITEM, "price_list": self.settings.price_list}, "price_list_rate"
			)
		)
		ensure(
			"Price List",
			"_Test Trade",
			{"price_list_name": "_Test Trade", "currency": currency, "selling": 1, "enabled": 1},
		)
		if not frappe.db.exists("Item Price", {"item_code": ITEM, "price_list": "_Test Trade"}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": ITEM,
					"price_list": "_Test Trade",
					"price_list_rate": flt(self.retail * 0.8, 2),
				}
			).insert(ignore_permissions=True)
		ensure(
			"Customer Group",
			"_Test Trade Group",
			{
				"customer_group_name": "_Test Trade Group",
				"parent_customer_group": "All Customer Groups",
				"default_price_list": "_Test Trade",
			},
		)
		ensure(
			"Payment Terms Template",
			"_Test 20th",
			{
				"template_name": "_Test 20th",
				"terms": [
					{
						"invoice_portion": 100,
						"due_date_based_on": "Day(s) after the end of the invoice month",
						"credit_days": 20,
					}
				],
			},
		)
		self.sendmail = patch("frappe.sendmail")
		self.sendmail.start()
		self.addCleanup(self.sendmail.stop)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Shop Settings", self.original)
		self.set_gateways(*self.original_gateways)

	def set_gateways(self, *rows):
		settings = frappe.get_doc("Shop Settings")
		settings.payment_gateways = []
		for row in rows:
			settings.append("payment_gateways", row)
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")

	def register(self, email, name="Trade Tester"):
		if not frappe.db.exists("User", email):
			accounts.register(full_name=name, email=email, accept_terms=1)
		return email

	def approved_trade_customer(self, email, on_account=1, credit_limit=None):
		self.register(email)
		frappe.set_user(email)
		result = accounts.apply_trade(
			{
				"company_name": f"Trade Co {email.split('@')[0]}",
				"contact_name": "Trade Tester",
				"email": email,
				"country": self.address["country"],
				"address_line1": "12 Industrial Way",
				"city": "Town",
			},
			accept_terms=1,
		)
		frappe.set_user("Administrator")
		self.assertNotIn("name", result)  # the reply never says which Lead or account it found
		# the application is an ERPNext Lead from the store
		lead = frappe.get_doc("Lead", lead_for(email))
		self.assertEqual(lead.utm_source, "Store Trade Application")
		self.assertEqual(lead.shop_user, email)
		self.assertTrue(lead.shop_terms_version)
		approved = accounts.approve_trade(
			lead.name,
			customer_group="_Test Trade Group",
			allow_on_account=on_account,
			payment_terms="_Test 20th" if on_account else None,
			credit_limit=credit_limit,
		)
		lead.reload()
		self.assertEqual(lead.status, "Converted")
		self.assertEqual(lead.customer, approved["customer"])
		customer = frappe.get_doc("Customer", approved["customer"])
		self.assertEqual(customer.lead_name, lead.name)
		self.assertIn(email, [row.user for row in customer.portal_users])
		self.assertTrue(
			frappe.db.exists(
				"Dynamic Link",
				{"parenttype": "Address", "link_doctype": "Customer", "link_name": customer.name},
			)
		)
		return customer.name

	def test_guest_application_becomes_a_customer_made_from_the_lead(self):
		frappe.set_user("Guest")
		try:
			accounts.apply_trade(
				{
					"company_name": "Guest Trade Ltd",
					"contact_name": "Gina Guest",
					"email": "gina.guest@example.com",
					"tax_id": "123-456-789",
					"country": self.address["country"],
					"address_line1": "1 Depot Road",
					"city": "Town",
				},
				accept_terms=1,
			)
		finally:
			frappe.set_user("Administrator")
		approved = accounts.approve_trade(
			lead_for("gina.guest@example.com"), customer_group="_Test Trade Group"
		)
		customer = frappe.get_doc("Customer", approved["customer"])
		self.assertEqual(
			(customer.customer_name, customer.customer_type, customer.tax_id),
			("Guest Trade Ltd", "Company", "123-456-789"),
		)
		self.assertEqual(customer.customer_group, "_Test Trade Group")
		# ERPNext moved the Lead's contact to the Customer, and the applicant can sign in to the store
		self.assertEqual(
			frappe.db.get_value("Contact", customer.customer_primary_contact, "email_id"),
			"gina.guest@example.com",
		)
		self.assertTrue(frappe.db.exists("User", "gina.guest@example.com"))
		self.assertIn("gina.guest@example.com", [row.user for row in customer.portal_users])

	def test_declined_application_is_an_unqualified_lead(self):
		email = self.register("trade.declined@example.com")
		frappe.set_user(email)
		result = accounts.apply_trade(
			{
				"company_name": "Declined Co",
				"contact_name": "Trade Tester",
				"email": email,
				"country": self.address["country"],
				"tax_id": "123-456-789",
				"address_line1": "4 Mill Lane",
				"city": "Town",
				"message": "We buy about 50 a year",
			},
			accept_terms=1,
		)
		# applying again updates the same Lead, with the same reply
		again = accounts.apply_trade(
			{
				"company_name": "Declined Co",
				"contact_name": "T",
				"email": email,
				"country": self.address["country"],
				"address_line1": "4 Mill Lane",
				"city": "Town",
			},
			accept_terms=1,
		)
		self.assertEqual(again, result)
		self.assertEqual(frappe.db.count("Lead", {"email_id": email}), 1)
		# what was left blank the second time is kept, and the address isn't added twice
		self.assertEqual(frappe.db.get_value("Lead", lead_for(email), "shop_tax_id"), "123-456-789")
		self.assertEqual(
			frappe.db.count(
				"Dynamic Link",
				{"parenttype": "Address", "link_doctype": "Lead", "link_name": lead_for(email)},
			),
			1,
		)
		self.assertEqual(accounts.trade_status()["status"], "Pending")
		frappe.set_user("Administrator")
		accounts.decline_trade(lead_for(email), reason="Not a business")
		lead = frappe.get_doc("Lead", lead_for(email))
		self.assertEqual(lead.qualification_status, "Unqualified")
		self.assertTrue(any("Not a business" in row.note for row in lead.notes))
		self.assertTrue(any("50 a year" in row.note for row in lead.notes))
		frappe.set_user(email)
		self.assertEqual(accounts.trade_status()["status"], "Declined")
		# after a decline the business can apply again
		accounts.apply_trade(
			{
				"company_name": "Declined Co",
				"contact_name": "T",
				"email": email,
				"country": self.address["country"],
			},
			accept_terms=1,
		)
		self.assertEqual(accounts.trade_status()["status"], "Pending")

	def test_an_unverified_email_does_not_take_over_an_existing_customer(self):
		existing = accounts.ensure_customer("someone.else@example.com", "Someone Else")
		frappe.db.set_value("Customer", existing, "payment_terms", "_Test 20th")
		frappe.set_user("Guest")
		try:
			accounts.apply_trade(
				{
					"company_name": "Imposter Ltd",
					"contact_name": "I",
					"email": "someone.else@example.com",
					"country": self.address["country"],
				},
				accept_terms=1,
			)
		finally:
			frappe.set_user("Administrator")
		approved = accounts.approve_trade(
			lead_for("someone.else@example.com"), customer_group="_Test Trade Group"
		)
		self.assertNotEqual(approved["customer"], existing)
		self.assertEqual(
			frappe.db.get_value("Customer", existing, ["customer_name", "payment_terms"]),
			("Someone Else", "_Test 20th"),
		)

	def test_an_application_doesnt_change_someone_elses_lead(self):
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": "Crm Person",
				"email_id": "crm.person@example.com",
				"phone": "021",
			}
		).insert(ignore_permissions=True)
		frappe.set_user("Guest")
		try:
			with patch("frappe.sendmail"):
				accounts.apply_trade(
					{
						"company_name": "Mallory Corp",
						"contact_name": "M",
						"email": "crm.person@example.com",
						"phone": "0999",
						"country": self.address["country"],
					},
					accept_terms=1,
				)
		finally:
			frappe.set_user("Administrator")
		lead.reload()
		self.assertEqual((lead.phone, lead.company_name, lead.utm_source), ("021", None, None))
		self.assertTrue(any("Mallory Corp" in row.note for row in lead.notes))

	def test_a_guest_order_isnt_put_on_a_customer_made_in_desk(self):
		desk = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Desk Trade Co (test)",
				"customer_group": "_Test Trade Group",
				"payment_terms": "_Test 20th",
			}
		).insert(ignore_permissions=True)
		from shop.storefront.checkout import create_contact

		create_contact(desk.name, {"full_name": "Desk Buyer"}, "desk.buyer@example.com")
		# a shopper who isn't signed in types that customer's email
		cart.add_item(ITEM)
		order = checkout.place_order(
			customer={"email": "desk.buyer@example.com", "full_name": "Someone"},
			address=self.address,
			accept_terms=1,
		)["sales_order"]
		self.assertNotEqual(frappe.db.get_value("Sales Order", order, "customer"), desk.name)

	def test_staff_answer_applications_in_the_shop_admin(self):
		from shop.api import trade

		group = frappe.db.get_single_value("Shop Settings", "trade_customer_group")
		self.addCleanup(frappe.clear_cache, doctype="Shop Settings")
		self.addCleanup(frappe.db.set_single_value, "Shop Settings", "trade_customer_group", group)
		frappe.db.set_single_value("Shop Settings", "trade_customer_group", "_Test Trade Group")
		frappe.clear_cache(doctype="Shop Settings")
		for email, company in (
			("admin.approve@example.com", "Approve Co"),
			("admin.decline@example.com", "Decline Co"),
		):
			frappe.set_user("Guest")
			try:
				accounts.apply_trade(
					{
						"company_name": company,
						"contact_name": "Applicant",
						"email": email,
						"country": self.address["country"],
						"address_line1": "8 Yard Street",
						"city": "Town",
						"message": "We fit out <b>workshops</b>",
					},
					accept_terms=1,
				)
			finally:
				frappe.set_user("Administrator")
		approve, decline = lead_for("admin.approve@example.com"), lead_for("admin.decline@example.com")
		manager = "trade.manager@example.com"
		if not frappe.db.exists("User", manager):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": manager,
					"first_name": "Manager",
					"roles": [{"role": "Shop Manager"}],
				}
			).insert(ignore_permissions=True)
		# a Shop Manager answers applications without permissions on Leads or Customers in Desk
		frappe.set_user(manager)
		self.assertIn(approve, [row.name for row in trade.get_applications("Waiting")["applications"]])
		application = trade.get_application(approve)
		self.assertEqual(
			(application["state"], application["company_name"], application["customer_group"]),
			("Waiting", "Approve Co", "_Test Trade Group"),
		)
		self.assertTrue(application["addresses"])
		self.assertIn("We fit out workshops", [note["note"] for note in application["notes"]])
		approved = trade.approve_application(
			approve, payment_terms="_Test 20th", allow_on_account=1, credit_limit=500
		)
		customer = frappe.get_doc("Customer", approved["customer"])
		self.assertEqual(
			(customer.customer_group, customer.payment_terms, customer.shop_allow_on_account),
			("_Test Trade Group", "_Test 20th", 1),
		)
		self.assertEqual(frappe.db.get_value("Lead", approve, "qualified_by"), manager)
		self.assertIn(approve, [row.name for row in trade.get_applications("Approved")["applications"]])
		self.assertRaises(frappe.ValidationError, trade.approve_application, approve)
		trade.decline_application(decline, "Not a business")
		self.assertEqual(trade.get_application(decline)["state"], "Declined")
		self.assertRaises(frappe.ValidationError, trade.decline_application, decline)
		# staff can change their mind about a declined application
		trade.approve_application(decline)
		self.assertEqual(trade.get_application(decline)["state"], "Approved")
		frappe.set_user("Administrator")
		other = frappe.get_doc({"doctype": "Lead", "lead_name": "Not From The Store"}).insert(
			ignore_permissions=True
		)
		self.assertRaises(frappe.ValidationError, trade.get_application, other.name)
		frappe.set_user("admin.approve@example.com")
		for call in (
			lambda: trade.get_applications(),
			lambda: trade.get_application(approve),
			lambda: trade.approve_application(decline),
			lambda: trade.decline_application(decline),
		):
			self.assertRaises(frappe.PermissionError, call)

	def test_approving_from_the_lead_form_is_allowed(self):
		self.assertIn(accounts.approve_trade, frappe.whitelisted)
		self.assertNotIn(accounts.set_trade_terms, frappe.whitelisted)

	def test_sign_up_needs_the_terms_and_records_them(self):
		with self.assertRaises(frappe.ValidationError):
			accounts.register(full_name="No Terms", email="no.terms@example.com", accept_terms=0)
		email = self.register("with.terms@example.com", "With Terms")
		from shop.storefront import terms

		self.assertEqual(frappe.db.get_value("User", email, "shop_terms_version"), terms.version())
		self.assertEqual(frappe.db.get_value("User", email, "user_type"), "Website User")
		with self.assertRaises(frappe.ValidationError):
			accounts.register(full_name="Again", email=email, accept_terms=1)

	def test_approved_trade_customer_sees_trade_prices(self):
		customer = self.approved_trade_customer("trade.prices@example.com")
		self.assertEqual(frappe.db.get_value("Customer", customer, "customer_group"), "_Test Trade Group")
		self.assertEqual(frappe.db.get_value("Customer", customer, "customer_type"), "Company")
		frappe.set_user("trade.prices@example.com")
		price = pricing.get_price(ITEM)
		self.assertEqual(price["rate"], flt(self.retail * 0.8, 2))
		self.assertEqual(price["retail"], self.retail)
		# what the storefront shows: the customer's own price, with the currency
		self.assertEqual(price["display"], pricing.display_price(price["rate"]))
		self.assertIn(pricing.store_currency(), price["display"])
		frappe.set_user("Guest")
		self.assertEqual(pricing.get_price(ITEM)["rate"], self.retail)

	def test_customer_pricing_rule_applies(self):
		customer = self.approved_trade_customer("trade.rule@example.com", on_account=0)
		if not frappe.db.exists("Pricing Rule", {"title": "_Test 10% for trade.rule"}):
			frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": "_Test 10% for trade.rule",
					"apply_on": "Item Code",
					"items": [{"item_code": ITEM}],
					"applicable_for": "Customer",
					"customer": customer,
					"selling": 1,
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": 10,
					"company": self.settings.company,
					"currency": self.settings.currency,
				}
			).insert(ignore_permissions=True)
		frappe.set_user("trade.rule@example.com")
		self.assertEqual(pricing.get_price(ITEM)["rate"], flt(self.retail * 0.8 * 0.9, 2))

	def test_pay_on_account_invoices_the_order(self):
		customer = self.approved_trade_customer("trade.account@example.com")
		frappe.set_user("trade.account@example.com")
		methods = [m["method"] for m in totals.payment_methods()]
		self.assertIn(totals.ACCOUNT, methods)
		cart.add_item(ITEM)
		result = checkout.place_order(
			customer={"email": "trade.account@example.com", "full_name": "Trade Tester"},
			address=dict(self.address, address_line1="7 Site Road"),
			payment_method=totals.ACCOUNT,
			accept_terms=1,
		)
		frappe.set_user("Administrator")
		order = frappe.get_doc("Sales Order", result["sales_order"])
		self.assertEqual(order.customer, customer)
		self.assertEqual(order.items[0].rate, flt(self.retail * 0.8, 2))
		self.assertEqual(order.customer_group, "_Test Trade Group")
		# billed to the business's own address, sent to the address given at checkout
		self.assertEqual(
			frappe.db.get_value("Address", order.customer_address, "address_line1"), "12 Industrial Way"
		)
		self.assertEqual(
			frappe.db.get_value("Address", order.shipping_address_name, "address_line1"), "7 Site Road"
		)
		invoice = frappe.db.get_value(
			"Sales Invoice Item", {"sales_order": order.name, "docstatus": 1}, "parent"
		)
		self.assertTrue(invoice)
		self.assertEqual(
			frappe.db.get_value("Sales Invoice", invoice, "payment_terms_template"), "_Test 20th"
		)

		# cancelled before it was paid: the credit note settles the invoice, nothing is refunded
		from unittest.mock import patch

		from shop.storefront import payment

		with patch("frappe.sendmail"):
			payment.cancel_by_store(order.name)
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice, "outstanding_amount"), 0)
		self.assertEqual(payment.refunds_due(order.name), [])
		# nothing was paid: it is credited, not paid
		self.assertEqual(payment.payment_status(frappe.get_doc("Sales Order", order.name)), "Credited")

	def test_credit_limit_holds_only_orders_on_account(self):
		email = "limited.buyer@example.com"
		customer = self.approved_trade_customer(email, credit_limit=flt(self.retail))
		frappe.set_user(email)
		cart.add_item(ITEM, qty=3)
		with self.assertRaisesRegex(frappe.ValidationError, "credit limit"):
			checkout.place_order(
				customer={"email": email, "full_name": "Trade Tester"},
				address=self.address,
				payment_method=totals.ACCOUNT,
				accept_terms=1,
			)
		# paid up front, the same order goes through
		result = checkout.place_order(
			customer={"email": email, "full_name": "Trade Tester"},
			address=self.address,
			payment_method=totals.BANK,
			accept_terms=1,
		)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Sales Order", result["sales_order"], "customer"), customer)

	def test_retail_customers_cannot_pay_on_account(self):
		self.register("retail.only@example.com")
		frappe.set_user("retail.only@example.com")
		self.assertNotIn(totals.ACCOUNT, [m["method"] for m in totals.payment_methods()])

	def test_quote_requested_sent_and_accepted(self):
		settings = frappe.get_doc("Shop Settings")
		banks = [row.as_dict() for row in settings.bank_accounts]
		enabled = settings.enable_bank_transfer
		settings.card_fee_item = None
		settings.enable_bank_transfer = 1
		settings.bank_accounts = []
		from shop.tests.utils import company_bank_account

		settings.append(
			"bank_accounts", {"bank_account": company_bank_account(settings.company, settings.currency)}
		)
		settings.save(ignore_permissions=True)

		def restore():
			doc = frappe.get_doc("Shop Settings")
			doc.enable_bank_transfer = enabled
			doc.bank_accounts = []
			for row in banks:
				doc.append(
					"bank_accounts",
					{k: row[k] for k in ("bank_account", "label", "conversion_fee_percent", "instructions")},
				)
			doc.save(ignore_permissions=True)

		self.addCleanup(restore)
		frappe.clear_cache(doctype="Shop Settings")
		cart.add_item(ITEM, qty=3)
		result = quotes.request_quote(
			customer={"email": "quote.buyer@example.com", "full_name": "Quote Buyer"},
			address=self.address,
			message="PO 123",
		)
		quotation = frappe.get_doc("Quotation", result["quote"])
		self.assertEqual(quotation.docstatus, 0)
		self.assertEqual(quotation.shop_request_message, "PO 123")
		quotation.submit()
		quotes.send_quote(quotation.name)
		summary = quotes.quote_summary(quotation.name, quotation.shop_access_token)
		self.assertTrue(summary["can_accept"])
		with self.assertRaises(frappe.PermissionError):
			quotes.quote_summary(quotation.name, "wrong-token")
		frappe.set_user("Guest")
		accepted = quotes.accept_quote(
			quotation.name, quotation.shop_access_token, totals.BANK, accept_terms=1
		)
		frappe.set_user("Administrator")
		order = frappe.get_doc("Sales Order", accepted["sales_order"])
		self.assertEqual(flt(order.grand_total), flt(quotation.grand_total))
		self.assertEqual(order.shop_payment_method, totals.BANK)
		self.assertIn(order.shop_access_token, accepted["redirect"])
		with self.assertRaises(frappe.ValidationError):
			quotes.accept_quote(quotation.name, quotation.shop_access_token, totals.BANK, accept_terms=1)

	def test_a_quote_is_paid_online_only_through_a_gateway_in_its_currency(self):
		from unittest.mock import patch

		company = self.settings.company
		home = frappe.get_cached_value("Company", company, "default_currency")
		other = "USD" if home != "USD" else "EUR"
		local = gateway(company, "_Test Shop Local Gateway")
		both = gateway(company, "_Test Shop Both Gateway", (home, other))
		self.set_gateways(
			{"payment_gateway": local, "label": "Local"}, {"payment_gateway": both, "label": "Both"}
		)
		with (
			patch.object(quotes, "is_export", return_value=True),
			patch.object(quotes, "payment_fee", return_value=0),
		):
			for currency, offered in ((other, [both]), (home, [local, both])):
				quotation = frappe._dict(currency=currency, party_name="Someone Else")
				self.assertEqual(
					[
						m["method"]
						for m in quotes.quote_payment_methods(quotation)
						if totals.is_gateway(m["method"])
					],
					[totals.gateway_method(name) for name in offered],
				)

	def test_card_fee_is_added_to_quotes_paid_by_card(self):
		frappe.db.set_single_value(
			"Shop Settings", "card_fee_item", service("TEST-CARD-FEE", self.settings.company)
		)
		self.set_gateways(
			{"payment_gateway": gateway(self.settings.company), "fee_percent": 2.65, "fee_fixed": 0.3}
		)
		cart.add_item(ITEM, qty=1)
		result = quotes.request_quote(
			customer={"email": "fee.buyer@example.com", "full_name": "Fee Buyer"}, address=self.address
		)
		quotation = frappe.get_doc("Quotation", result["quote"])
		quotation.submit()
		fee = quotes.payment_fee(quotation, totals.gateway_method(gateway(self.settings.company)))
		self.assertGreater(fee, 0)
		total = flt(quotation.grand_total)
		self.assertAlmostEqual(fee, 0.0265 * (total + fee) + 0.3, delta=0.02)


class TestCustomerPrices(IntegrationTestCase):
	def setUp(self):
		for name in ("shop_session_customer", "shop_customer_rates"):
			if hasattr(frappe.local, name):
				delattr(frappe.local, name)
		self.parent = ensure(
			"Item Group",
			"_Test Store Hardware",
			{
				"item_group_name": "_Test Store Hardware",
				"parent_item_group": "All Item Groups",
				"is_group": 1,
			},
		)
		self.child = ensure(
			"Item Group",
			"_Test Store Tools",
			{"item_group_name": "_Test Store Tools", "parent_item_group": "_Test Store Hardware"},
		)
		self.item = "_Test Store Tool Item"
		if not frappe.db.exists("Item", self.item):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": self.item,
					"item_name": self.item,
					"item_group": self.child,
					"stock_uom": "Nos",
					"is_stock_item": 0,
				}
			).insert(ignore_permissions=True)
		settings = frappe.get_doc("Shop Settings")
		if not frappe.db.exists("Item Price", {"item_code": self.item, "price_list": settings.price_list}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": self.item,
					"price_list": settings.price_list,
					"price_list_rate": 100,
				}
			).insert(ignore_permissions=True)
		self.group = ensure(
			"Customer Group",
			"_Test Discount Group",
			{"customer_group_name": "_Test Discount Group", "parent_customer_group": "All Customer Groups"},
		)
		self.customer = ensure(
			"Customer",
			"_Test Discount Customer",
			{"customer_name": "_Test Discount Customer", "customer_group": "_Test Discount Group"},
		)

	def rate(self):
		frappe.local.shop_customer_rates = {}
		return pricing.customer_rate(
			self.item, self.customer, frappe.get_cached_doc("Shop Settings").price_list, 1
		)

	def test_a_customer_group_pricing_rule_gives_its_customers_their_price(self):
		from shop import setup_store

		self.assertEqual(self.rate(), 100)
		setup_store.group_discount(self.group, self.parent, 15)
		self.assertEqual(self.rate(), 85)  # the rule's Item Group includes its sub-groups
		setup_store.group_discount(self.group, self.parent, 30)
		self.assertEqual(self.rate(), 85)  # an existing rule is left as the store set it


class TestStatements(IntegrationTestCase):
	GROUP, OTHER = "_Test Statement Group", "_Test Other Group"

	def setUp(self):
		for group in (self.GROUP, self.OTHER):
			ensure(
				"Customer Group",
				group,
				{"customer_group_name": group, "parent_customer_group": "All Customer Groups"},
			)
		settings = frappe.get_doc("Shop Settings")
		original = {field: settings.get(field) for field in ("trade_customer_group", "email_statements")}
		self.addCleanup(lambda: frappe.db.set_single_value("Shop Settings", original))
		frappe.db.set_single_value(
			"Shop Settings", {"trade_customer_group": self.GROUP, "email_statements": 1}
		)
		frappe.clear_cache(doctype="Shop Settings")
		self.stays = frappe.get_doc(
			"Customer", accounts.ensure_customer("statement.stays@example.com", "Statement Stays")
		)
		self.stays.customer_group = self.GROUP
		self.stays.save(ignore_permissions=True)
		self.RUN = frappe.db.get_value(
			"Process Statement Of Accounts",
			{"customer_collection": "Customer Group", "collection_name": self.GROUP},
		)

	def rows(self):
		return frappe.get_all(
			"Process Statement Of Accounts Customer",
			filters={"parent": self.RUN},
			fields=["customer", "primary_email"],
		)

	def test_store_customer_gets_a_primary_contact_and_email(self):
		customer = accounts.ensure_customer("statement.one@example.com", "Statement One")
		values = frappe.db.get_value(
			"Customer", customer, ["customer_primary_contact", "email_id"], as_dict=True
		)
		self.assertTrue(values.customer_primary_contact)
		self.assertEqual(values.email_id, "statement.one@example.com")

	def test_the_store_statement_run_is_made_when_the_trade_group_has_a_customer(self):
		self.assertTrue(self.RUN)
		self.assertIn("statement.stays@example.com", [r.primary_email for r in self.rows()])

	def test_customer_joins_and_leaves_the_statement_run_with_their_group(self):
		customer = frappe.get_doc(
			"Customer", accounts.ensure_customer("statement.two@example.com", "Statement Two")
		)
		customer.customer_group = self.GROUP
		customer.save(ignore_permissions=True)
		self.assertIn(
			{"customer": customer.name, "primary_email": "statement.two@example.com"},
			[dict(r) for r in self.rows()],
		)
		customer.customer_group = self.OTHER
		customer.save(ignore_permissions=True)
		self.assertNotIn(customer.name, [r.customer for r in self.rows()])

	def test_the_last_customer_leaving_stops_the_statements_and_one_run_is_kept(self):
		self.stays.customer_group = self.OTHER
		self.stays.save(ignore_permissions=True)
		self.assertFalse(frappe.db.get_value("Process Statement Of Accounts", self.RUN, "enable_auto_email"))
		# renaming the store doesn't make a second run for the group
		from shop.setup_store import statement_run

		company = frappe.get_cached_doc("Shop Settings").company
		self.assertEqual(statement_run(company, self.GROUP, "A Renamed Store"), self.RUN)
		self.stays.customer_group = self.GROUP
		self.stays.save(ignore_permissions=True)
		self.assertTrue(frappe.db.get_value("Process Statement Of Accounts", self.RUN, "enable_auto_email"))

	def test_statement_needs_a_signed_in_customer(self):
		from shop.storefront import statements

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				statements.statement_pdf()
		finally:
			frappe.set_user("Administrator")
