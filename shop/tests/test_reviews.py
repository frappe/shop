import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import reviews


class TestReviews(IntegrationTestCase):
	def test_summary_shape(self):
		result = reviews.get_reviews("ceramic-mug")
		self.assertTrue(result["count"])
		self.assertTrue(0 < result["average"] <= 5)
		self.assertEqual(len(result["histogram"]), 5)
		self.assertEqual(sum(row["count"] for row in result["histogram"]), result["count"])
		self.assertTrue(result["reviews"][0]["reviewer_name"])

	def test_add_review(self):
		before = reviews.summary("ceramic-mug")["count"]
		result = reviews.add_review("ceramic-mug", rating=4, title="Solid", review="Good mug.")
		self.assertEqual(result["count"], before + 1)

	def test_guest_cannot_review(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				reviews.add_review("ceramic-mug", rating=5)
		finally:
			frappe.set_user("Administrator")

	def test_invalid_rating_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			reviews.add_review("ceramic-mug", rating=9)

	def test_catalog_carries_rating_and_discount(self):
		from shop.storefront import catalog

		listing = catalog.get_products(search="mug")
		mug = listing["products"][0]
		self.assertTrue(mug.rating_count)
		self.assertEqual(mug.discount_pct, 25)
		self.assertTrue(mug.formatted_compare_at)
