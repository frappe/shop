from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from shop.api import analytics, carts, customers, discounts, inventory, orders, products, reviews, settings
from shop.storefront import cart as storefront_cart
from shop.storefront import checkout
from shop.storefront.orders import order_summary
from shop.tests.utils import fresh_request, sellable

BUYER = {"email": "admin-test-buyer@example.com", "full_name": "Admin Test Buyer"}
ADDRESS = {"address_line1": "11 Admin Way", "city": "Bengaluru", "country": "India"}


class TestAdminApi(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()
		# every test sells from the same stock
		sellable("SHOP-DEMO-003", 5)

	def place_order(self):
		storefront_cart.add_item("SHOP-DEMO-003")
		return checkout.place_order(customer=BUYER, address=ADDRESS)["sales_order"]

	def test_analytics_overview(self):
		self.place_order()
		overview = analytics.get_overview(days=7)
		self.assertGreater(overview["orders"], 0)
		self.assertEqual(len(overview["series"]), 7)
		self.assertTrue(overview["formatted_revenue"])
		self.assertTrue(overview["top_products"])

	def test_order_listing_and_payment_flow(self):
		name = self.place_order()
		listing = orders.get_orders(search=name)
		self.assertEqual(listing["orders"][0]["name"], name)
		self.assertEqual(listing["orders"][0]["payment_status"], "Unpaid")
		detail = orders.mark_paid(name)
		self.assertEqual(detail["payment_status"], "Paid")
		self.assertIn("Payment recorded", [event["label"] for event in detail["timeline"]])

	def test_part_payment_into_a_chosen_bank_account(self):
		from shop.storefront import payment
		from shop.tests.utils import company_bank_account

		name = self.place_order()
		order = frappe.get_doc("Sales Order", name)
		account = company_bank_account(order.company, order.currency)
		due = orders.get_order(name)["amount_due"]
		detail = orders.mark_paid(name, bank_account=account, amount=frappe.utils.flt(due / 2, 2))
		self.assertEqual(detail["payment_status"], "Part paid")
		entry = frappe.get_last_doc("Payment Entry", filters={"reference_no": name})
		self.assertEqual(entry.bank_account, account)
		self.assertEqual(entry.paid_to, frappe.db.get_value("Bank Account", account, "account"))
		detail = orders.mark_paid(name, bank_account=account, amount=detail["amount_due"])
		self.assertEqual(detail["payment_status"], "Paid")
		with self.assertRaises(frappe.ValidationError):
			orders.mark_paid(name)
		# invoicing moves the payments to the invoice; the order is still paid
		order.reload()
		payment.invoice_paid_order(order)
		self.assertEqual(orders.get_order(name)["payment_status"], "Paid")

	def test_store_cancels_an_unpaid_order_and_tells_the_customer(self):
		name = self.place_order()
		with patch("frappe.sendmail") as sendmail:
			detail = orders.cancel_order(name, note="Out of stock at the supplier")
		self.assertEqual(detail["docstatus"], 2)
		mail = next(c.kwargs for c in sendmail.call_args_list if c.kwargs.get("reference_name") == name)
		self.assertEqual(mail["subject"], f"Your order {name} has been cancelled")
		self.assertIn("Out of stock at the supplier", mail["message"])
		summary = order_summary(frappe.get_doc("Sales Order", name))
		self.assertEqual(summary["heading"], "Your order has been cancelled")
		self.assertIsNone(summary["confirmed"])
		self.assertIsNone(summary["awaiting_shipment"])

	def test_store_cancels_a_paid_order_with_a_credit_note(self):
		name = self.place_order()
		orders.mark_paid(name)
		with patch("frappe.sendmail"):
			orders.cancel_order(name)
		order = frappe.get_doc("Sales Order", name)
		self.assertEqual(order.status, "Closed")
		self.assertEqual(order_summary(order)["display_status"], "Cancelled")
		from shop.storefront import payment

		invoice = payment.order_invoice(name)
		credit_note = frappe.db.get_value("Sales Invoice", {"return_against": invoice, "docstatus": 1})
		self.assertTrue(credit_note)
		self.assertEqual(
			frappe.db.get_value("Sales Invoice", credit_note, "grand_total"),
			-frappe.db.get_value("Sales Invoice", invoice, "grand_total"),
		)

	def test_a_shop_manager_without_desk_roles_runs_an_order_through(self):
		# Shop Manager has no permissions on Payment Entry, Delivery Note or Sales Invoice in Desk
		manager = "orders.manager@example.com"
		if not frappe.db.exists("User", manager):
			frappe.get_doc(
				{"doctype": "User", "email": manager, "first_name": "Orders", "roles": [{"role": "Shop Manager"}]}
			).insert(ignore_permissions=True)
		paid, shipped, cancelled = self.place_order(), self.place_order(), self.place_order()
		frappe.set_user(manager)
		self.addCleanup(frappe.set_user, "Administrator")

		self.assertEqual(orders.mark_paid(paid)["payment_status"], "Paid")
		with self.assertRaises(frappe.ValidationError):
			orders.mark_paid(cancelled, amount=0)
		orders.fulfill(shipped)
		self.assertEqual(frappe.db.get_value("Sales Order", shipped, "per_delivered"), 100)
		with patch("frappe.sendmail"):
			self.assertEqual(orders.cancel_order(cancelled)["docstatus"], 2)

	def test_a_bank_refund_needs_the_bank_account(self):
		with self.assertRaises(frappe.ValidationError):
			orders.refund(self.place_order(), "CN-0001", "bank", bank_account="")
		with self.assertRaises(frappe.ValidationError):
			orders.refund(self.place_order(), "CN-0001", "cheque")

	def test_a_shipped_order_is_returned_not_cancelled(self):
		name = self.place_order()
		orders.fulfill(name)
		with self.assertRaisesRegex(frappe.ValidationError, "Use a return"):
			orders.cancel_order(name)

	def test_fulfillment(self):
		name = self.place_order()
		detail = orders.fulfill(name)
		self.assertEqual(detail["fulfillment_status"], "Fulfilled")

	def test_a_product_is_made_in_the_item_group_chosen(self):
		groups = products.get_item_groups()
		self.assertIn(groups["default"], groups["item_groups"])
		if not frappe.db.exists("Item Group", "_Test Shop Sensors"):
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": "_Test Shop Sensors",
					"parent_item_group": "All Item Groups",
				}
			).insert(ignore_permissions=True)
		created = products.create_product(
			product_name="Test Probe", price=50, item_group="_Test Shop Sensors"
		)
		self.addCleanup(products.delete_product, created["name"])
		self.assertEqual(created["item_group"], "_Test Shop Sensors")
		moved = products.save_product(
			{"name": created["name"], "item_group": groups["default"], "published": True}
		)
		self.assertEqual(frappe.db.get_value("Item", created["item"], "item_group"), groups["default"])
		self.assertEqual(moved["item_group"], groups["default"])

	def test_deleting_a_collection_moves_those_inside_it_up(self):
		products.save_collection({"title": "Outer (test)", "published": 1})
		outer = frappe.db.get_value("Shop Collection", {"title": "Outer (test)"})
		products.save_collection({"title": "Inner (test)", "published": 1, "parent_collection": outer})
		inner = frappe.db.get_value("Shop Collection", {"title": "Inner (test)"})
		self.addCleanup(frappe.delete_doc, "Shop Collection", inner, force=True)
		row = next(c for c in products.get_collections() if c.name == inner)
		self.assertEqual(row.parent_title, "Outer (test)")
		products.delete_collection(outer)
		self.assertIsNone(frappe.db.get_value("Shop Collection", inner, "parent_collection"))

	def test_a_charge_item_is_made_from_settings(self):
		name = settings.create_service_item("Test Card Fee")
		self.addCleanup(frappe.delete_doc, "Item", name, force=True)
		item = frappe.get_doc("Item", name)
		self.assertEqual((item.item_name, item.is_stock_item, item.is_sales_item), ("Test Card Fee", 0, 1))
		self.assertIn(name, [item["value"] for item in settings.get_settings()["service_items"]])

	def test_setup_guide_covers_taxes_shipping_and_email(self):
		from shop.api import admin

		steps = {step["key"]: step for step in admin.get_setup_guide()}
		self.assertTrue({"taxes", "shipping", "email"} <= set(steps))
		self.assertEqual(
			steps["email"]["done"], bool(frappe.db.exists("Email Account", {"enable_outgoing": 1}))
		)

	def test_a_service_product_with_its_weight_and_tax(self):
		created = products.create_product(
			product_name="Test Calibration", price=30, track_stock=False, opening_stock=5
		)
		self.addCleanup(products.delete_product, created["name"])
		self.assertFalse(created["track_stock"])
		self.assertFalse(frappe.db.exists("Stock Ledger Entry", {"item_code": created["item"]}))
		template = frappe.get_all(
			"Item Tax Template",
			filters={"company": frappe.get_cached_doc("Shop Settings").company},
			pluck="name",
			limit=1,
		)
		saved = products.save_product(
			{
				"name": created["name"],
				"weight": 0.25,
				"item_tax_template": template[0] if template else None,
				"published": True,
			}
		)
		self.assertEqual(saved["weight"], 0.25)
		self.assertEqual(saved["item_tax_template"], template[0] if template else None)

	def test_an_order_with_its_parcel_being_prepared_is_open(self):
		name = self.place_order()
		order = frappe.get_doc("Sales Order", name)
		order.status = "To Bill"
		with patch.object(orders, "fulfillment_label", return_value="Preparing"):
			self.assertEqual(orders.display_status(order), "Open")
		with patch.object(orders, "fulfillment_label", return_value="Shipped"):
			self.assertEqual(orders.display_status(order), "Fulfilled")

	def test_the_timeline_follows_the_parcel(self):
		name = self.place_order()
		fulfillment = frappe.get_doc(
			{
				"doctype": "Shop Fulfillment",
				"sales_order": name,
				"provider": "test-carrier",
				"status": "Accepted",
				"requested_on": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
		labels = [event["label"] for event in orders.get_order(name)["timeline"]]
		self.assertIn("Sent to test-carrier", labels)
		self.assertNotIn("Shipped", labels)
		self.assertNotIn("Fulfilled", labels)

		fulfillment.db_set({"status": "Shipped", "shipped_on": frappe.utils.now_datetime()})
		self.assertIn("Shipped", [event["label"] for event in orders.get_order(name)["timeline"]])

		# notes on the order, such as a disputed card payment, are in the timeline too
		frappe.get_doc("Sales Order", name).add_comment("Info", "The customer disputed $ 10.00")
		self.assertEqual(orders.get_order(name)["timeline"][-1]["label"], "The customer disputed $ 10.00")

	def test_an_order_entered_in_desk_doesnt_claim_the_store_emailed_it(self):
		store_order = frappe.get_doc("Sales Order", self.place_order())
		self.assertEqual(order_summary(store_order)["emailed"], "true")

		desk_order = frappe.copy_doc(store_order)
		for field in ("shop_payment_method", "shop_access_token", "shop_payment_due"):
			if desk_order.meta.has_field(field):
				desk_order.set(field, None)
		desk_order.insert(ignore_permissions=True)
		summary = order_summary(desk_order)
		self.assertIsNone(summary["emailed"])
		self.assertEqual(summary["heading"], "Your order")
		self.assertNotIn("emailed", summary["confirmation_note"])

	def test_an_order_in_another_currency_is_shown_in_it_and_counted_in_the_company_currency(self):
		name = self.place_order()
		order = frappe.get_doc("Sales Order", name)
		before = analytics.get_overview(days=1)["revenue"]
		frappe.db.set_value(
			"Sales Order",
			name,
			{"currency": "USD", "grand_total": order.grand_total / 2},
			update_modified=False,
		)

		self.assertTrue(orders.get_order(name)["formatted_grand_total"].endswith(" USD"))
		listed = next(row for row in orders.get_orders(search=name)["orders"] if row["name"] == name)
		self.assertTrue(listed["formatted_total"].endswith(" USD"))
		self.assertEqual(analytics.get_overview(days=1)["revenue"], before)

	def test_markup_typed_by_a_customer_is_never_shown_as_markup(self):
		storefront_cart.add_item("SHOP-DEMO-003")
		typed = '"<img src=x onerror=alert(1)>"'
		name = checkout.place_order(
			customer=dict(BUYER, full_name=f"Ann {typed}"),
			address=dict(ADDRESS, address_line1=f"1 Road {typed}"),
		)["sales_order"]
		order = frappe.get_doc("Sales Order", name)
		self.assertNotIn("<img", frappe.db.get_value("Address", order.shipping_address_name, "address_line1"))
		self.assertNotIn("<img", order.customer_name)

		# an address saved with markup some other way is escaped in the admin
		frappe.db.set_value("Address", order.shipping_address_name, "address_line1", typed)
		self.assertNotIn("<img", orders.get_order(name)["address"])

	def test_erpnext_order_defaults_are_set_from_shop_settings(self):
		group = frappe.db.get_single_value("Selling Settings", "customer_group")
		rounding = frappe.db.get_single_value("Global Defaults", "disable_rounded_total")
		self.addCleanup(
			settings.save_erpnext_settings, {"new_customer_group": group, "round_order_totals": not rounding}
		)
		other = frappe.db.get_value("Customer Group", {"is_group": 0, "name": ["!=", group or ""]})
		result = settings.save_settings({"new_customer_group": other, "round_order_totals": False})
		self.assertEqual(result["new_customer_group"], other)
		self.assertFalse(result["round_order_totals"])
		self.assertEqual(frappe.db.get_single_value("Global Defaults", "disable_rounded_total"), 1)

	def test_an_invoice_priced_differently_from_the_paid_order_is_not_made(self):
		from shop.storefront import payment

		name = self.place_order()
		orders.mark_paid(name)
		order = frappe.get_doc("Sales Order", name)
		with patch.object(payment.totals, "order_total", side_effect=[1.0, 2.0, 1.0, 2.0]):
			self.assertIsNone(payment.invoice_paid_order(order))
		self.assertFalse(payment.order_invoice(name))
		self.assertTrue(
			frappe.db.exists(
				"Comment", {"reference_name": name, "content": ["like", "%could not be invoiced%"]}
			)
		)
		with (
			self.assertRaisesRegex(frappe.ValidationError, "couldn't be invoiced"),
			patch.object(payment, "invoice_paid_order", return_value=None),
		):
			orders.cancel_order(name)
		self.assertNotEqual(frappe.db.get_value("Sales Order", name, "status"), "Closed")

	def test_product_lifecycle(self):
		created = products.create_product(
			product_name="Test Desk Lamp", price=1500, opening_stock=3, published=True
		)
		self.addCleanup(products.delete_product, created["name"])
		self.assertEqual(created["stock"], 3)
		self.assertEqual(created["price"], 1500)
		updated = products.save_product(
			{"name": created["name"], "price": 1200, "compare_at_price": 1800, "published": False}
		)
		self.assertEqual(updated["price"], 1200)
		self.assertFalse(updated["published"])
		listing = products.get_products(search="Test Desk Lamp")
		self.assertEqual(listing["products"][0]["name"], created["name"])

	def test_inventory_and_stock_adjustment(self):
		created = products.create_product(product_name="Test Stock Item", price=500, opening_stock=2)
		self.addCleanup(products.delete_product, created["name"])
		inventory.set_stock(created["item"], 12)
		rows = inventory.get_inventory(search="Test Stock Item")
		self.assertEqual(rows["items"][0]["stock"], 12)
		self.assertFalse(rows["items"][0]["low"])

	def test_customers(self):
		name = self.place_order()
		customer = frappe.db.get_value("Sales Order", name, "customer")
		listing = customers.get_customers(search=customer)
		self.assertTrue(listing["customers"])
		detail = customers.get_customer(customer)
		self.assertIn(name, [order["name"] for order in detail["orders"]])

	def test_reviews_moderation(self):
		listing = reviews.get_reviews(product="ceramic-mug")
		self.assertTrue(listing["reviews"])
		target = listing["reviews"][0]["name"]
		reviews.delete_review(target)
		self.assertFalse(frappe.db.exists("Shop Review", target))

	def test_coupon_management(self):
		discounts.save_coupon(
			{"coupon_code": "ADMINTEST15", "discount_type": "Percentage", "value": 15, "enabled": True}
		)
		coupon = next(c for c in discounts.get_coupons() if c["coupon_code"] == "ADMINTEST15")
		self.assertEqual(coupon["value_label"], "15% off")
		self.assertTrue(coupon["enabled"])
		discounts.set_enabled(coupon["name"], False)
		coupon = next(c for c in discounts.get_coupons() if c["coupon_code"] == "ADMINTEST15")
		self.assertFalse(coupon["enabled"])
		discounts.delete_coupon(coupon["name"])
		self.assertFalse(frappe.db.exists("Coupon Code", {"coupon_code": "ADMINTEST15"}))

	def test_carts_view(self):
		storefront_cart.add_item("SHOP-DEMO-004")
		listing = carts.get_carts()
		self.assertTrue(listing["carts"])
		self.assertTrue(listing["carts"][0]["item_count"])

	def test_settings_round_trip(self):
		original = settings.get_settings()
		settings.save_settings({"low_stock_threshold": 9, "flat_shipping_rate": 49})
		updated = settings.get_settings()
		self.assertEqual(updated["low_stock_threshold"], 9)
		self.assertEqual(updated["flat_shipping_rate"], 49)
		settings.save_settings(
			{
				"low_stock_threshold": original["low_stock_threshold"] or 5,
				"flat_shipping_rate": original["flat_shipping_rate"] or 0,
			}
		)

	def test_bank_accounts_and_fees_round_trip(self):
		from shop.tests.utils import company_bank_account

		original = settings.get_settings()
		company = frappe.db.get_single_value("Shop Settings", "company")
		currency = frappe.get_cached_value("Company", company, "default_currency")
		account = company_bank_account(company, currency)
		self.assertIn(account, [row["name"] for row in original["company_bank_accounts"]])
		row = {
			"bank_account": account,
			"label": "Home",
			"conversion_fee_percent": 0,
			"local_transfer_fee": 0.5,
			"swift_transfer_fee": 6.11,
			"instructions": "",
		}
		try:
			updated = settings.save_settings({"bank_accounts": [row, {"bank_account": ""}]})
			self.assertEqual(len(updated["bank_accounts"]), 1)
			self.assertEqual(updated["bank_accounts"][0]["swift_transfer_fee"], 6.11)
			self.assertEqual(updated["bank_accounts"][0]["local_transfer_fee"], 0.5)
		finally:
			settings.save_settings({"bank_accounts": original["bank_accounts"]})

	def test_fulfillment_settings_persist(self):
		from shop.api import settings as settings_api
		from shop.storefront import stock
		from shop.tests.utils import second_warehouse

		original = settings_api.get_settings()
		self.addCleanup(
			settings_api.save_settings, {"fulfillment_locations": original["fulfillment_locations"]}
		)
		first = stock.primary_warehouse()
		second = second_warehouse(original["company"])
		updated = settings_api.save_settings(
			{
				"fulfillment_locations": [
					{"warehouse": first, "fulfillment_provider": "manual", "auto_send": True},
					{"warehouse": second, "fulfillment_provider": "", "auto_send": False},
					{"warehouse": ""},
				]
			}
		)
		self.assertEqual(
			[
				(row["warehouse"], row["fulfillment_provider"], row["auto_send"])
				for row in updated["fulfillment_locations"]
			],
			[(first, "manual", 1), (second, "manual", 0)],
		)
		with self.assertRaises(frappe.ValidationError):
			settings_api.save_settings(
				{"fulfillment_locations": [{"warehouse": first}, {"warehouse": first}]}
			)
		with self.assertRaises(frappe.ValidationError):
			settings_api.save_settings(
				{"fulfillment_locations": [{"warehouse": first, "fulfillment_provider": "nobody"}]}
			)
		self.assertTrue(updated["fulfillment_providers"])
