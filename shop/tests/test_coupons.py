import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from shop.storefront import cart, checkout
from shop.tests.utils import fresh_request

BUYER = {"email": "coupon-buyer@example.com", "full_name": "Coupon Buyer"}
ADDRESS = {"address_line1": "3 Offer Lane", "city": "Bengaluru", "country": "India"}


class TestCoupons(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()

	def test_apply_and_checkout_discount(self):
		cart.add_item("SHOP-DEMO-011")
		payload = cart.apply_coupon("WELCOME10")
		self.assertEqual(payload["coupon"]["code"], "WELCOME10")
		self.assertAlmostEqual(payload["discount"], payload["subtotal"] * 0.1, places=2)
		used_before = frappe.db.get_value("Coupon Code", {"coupon_code": "WELCOME10"}, "used")
		result = checkout.place_order(customer=BUYER, address=ADDRESS)
		order = frappe.get_doc("Sales Order", result["sales_order"])
		self.assertAlmostEqual(order.discount_amount, order.total * 0.1, places=2)
		self.assertAlmostEqual(order.grand_total, order.total * 0.9, places=2)
		self.assertEqual(
			frappe.db.get_value("Coupon Code", {"coupon_code": "WELCOME10"}, "used"),
			used_before + 1,
		)

	def test_invalid_code_rejected(self):
		cart.add_item("SHOP-DEMO-003")
		with self.assertRaises(frappe.ValidationError):
			cart.apply_coupon("NOPE123")

	def test_expired_coupon_rejected(self):
		expired = make_coupon("EXPIRED10", valid_upto=add_days(nowdate(), -1))
		cart.add_item("SHOP-DEMO-003")
		with self.assertRaises(frappe.ValidationError):
			cart.apply_coupon(expired)

	def test_fully_redeemed_coupon_rejected(self):
		code = make_coupon("MAXED10", maximum_use=1, used=1)
		cart.add_item("SHOP-DEMO-003")
		with self.assertRaises(frappe.ValidationError):
			cart.apply_coupon(code)

	def test_coupon_for_a_customer_group_is_only_for_that_group(self):
		group = "_Test Coupon Group"
		if not frappe.db.exists("Customer Group", group):
			frappe.get_doc(
				{
					"doctype": "Customer Group",
					"customer_group_name": group,
					"parent_customer_group": "All Customer Groups",
				}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("Coupon Code", {"coupon_code": "GROUPONLY"}):
			company = frappe.db.get_single_value("Shop Settings", "company")
			rule = frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": "Group only offer",
					"apply_on": "Transaction",
					"selling": 1,
					"coupon_code_based": 1,
					"applicable_for": "Customer Group",
					"customer_group": group,
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": 15,
					"company": company,
					"currency": frappe.get_cached_value("Company", company, "default_currency"),
				}
			).insert(ignore_permissions=True)
			frappe.get_doc(
				{
					"doctype": "Coupon Code",
					"coupon_name": "GROUPONLY",
					"coupon_code": "GROUPONLY",
					"coupon_type": "Promotional",
					"pricing_rule": rule.name,
				}
			).insert(ignore_permissions=True)
		cart.add_item("SHOP-DEMO-003")
		with self.assertRaisesRegex(frappe.ValidationError, "doesn't apply"):
			cart.apply_coupon("GROUPONLY")

	def test_coupon_with_a_minimum_applies_above_it(self):
		rule = frappe.db.get_value("Coupon Code", {"coupon_code": "WELCOME10"}, "pricing_rule")
		original = frappe.db.get_value("Pricing Rule", rule, "min_amt")
		frappe.db.set_value("Pricing Rule", rule, "min_amt", 1)
		self.addCleanup(frappe.db.set_value, "Pricing Rule", rule, "min_amt", original)
		cart.add_item("SHOP-DEMO-011")
		payload = cart.apply_coupon("WELCOME10")
		self.assertEqual(payload["coupon"]["code"], "WELCOME10")
		self.assertGreater(payload["discount"], 0)

	def test_remove_coupon(self):
		cart.add_item("SHOP-DEMO-003")
		cart.apply_coupon("WELCOME10")
		payload = cart.remove_coupon()
		self.assertIsNone(payload["coupon"])
		self.assertEqual(payload["total"], payload["subtotal"])


def make_coupon(code, valid_upto=None, maximum_use=0, used=0):
	if frappe.db.exists("Coupon Code", {"coupon_code": code}):
		frappe.db.set_value("Coupon Code", {"coupon_code": code}, {"used": used})
		return code
	frappe.get_doc(
		{
			"doctype": "Coupon Code",
			"coupon_name": code,
			"coupon_type": "Promotional",
			"coupon_code": code,
			"pricing_rule": frappe.db.get_value("Pricing Rule", {"title": "Shop welcome offer"}),
			"valid_upto": valid_upto,
			"maximum_use": maximum_use,
			"used": used,
		}
	).insert(ignore_permissions=True)
	return code


class TestCouponLifecycle(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Shop Cart")
		fresh_request()

	def test_coupon_held_in_a_cart_can_still_be_deleted(self):
		from shop.api import discounts

		discounts.save_coupon(
			{"coupon_code": "HELDINCART", "discount_type": "Percentage", "value": 10, "enabled": True}
		)
		coupon = next(c for c in discounts.get_coupons() if c["coupon_code"] == "HELDINCART")
		cart.add_item("SHOP-DEMO-003")
		cart.apply_coupon("HELDINCART")
		discounts.delete_coupon(coupon["name"])
		self.assertFalse(frappe.db.exists("Coupon Code", coupon["name"]))
		self.assertIsNone(cart.get_cart()["coupon"])

	def test_disabled_coupon_is_dropped_from_the_cart(self):
		from shop.api import discounts

		discounts.save_coupon(
			{"coupon_code": "GOESAWAY", "discount_type": "Percentage", "value": 10, "enabled": True}
		)
		coupon = next(c for c in discounts.get_coupons() if c["coupon_code"] == "GOESAWAY")
		cart.add_item("SHOP-DEMO-003")
		cart.apply_coupon("GOESAWAY")
		discounts.set_enabled(coupon["name"], False)
		payload = cart.get_cart()
		self.assertIsNone(payload["coupon"])
		self.assertEqual(payload["total"], payload["subtotal"])
		name = frappe.db.get_value("Shop Cart", {"status": "Active"})
		self.assertIsNone(frappe.db.get_value("Shop Cart", name, "coupon_code"))
		discounts.delete_coupon(coupon["name"])
