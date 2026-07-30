import frappe
from frappe.utils import cint

from shop.api import only_managers


@frappe.whitelist()
def get_reviews(
	product: str | None = None, rating: int | None = None, start: int = 0, limit: int = 20
) -> dict:
	only_managers()
	filters = {}
	if product:
		filters["product"] = product
	if rating:
		filters["rating"] = cint(rating)
	reviews = frappe.get_all(
		"Shop Review",
		filters=filters,
		fields=["name", "product", "reviewer_name", "rating", "title", "review", "verified", "creation"],
		order_by="creation desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 100),
	)
	titles = product_titles({review.product for review in reviews})
	for review in reviews:
		review["product_name"] = titles.get(review.product, review.product)
		review["posted_on"] = str(review.creation)[:10]
		del review["creation"]
	return {
		"reviews": reviews,
		"total": frappe.db.count("Shop Review", filters=filters),
		"average": average_rating(),
	}


def product_titles(products: set) -> dict:
	if not products:
		return {}
	rows = frappe.get_all(
		"Shop Product", filters={"name": ["in", list(products)]}, fields=["name", "product_name"]
	)
	return {row.name: row.product_name for row in rows}


def average_rating() -> float:
	ratings = frappe.get_all("Shop Review", pluck="rating")
	return round(sum(ratings) / len(ratings), 1) if ratings else 0


@frappe.whitelist(methods=["POST"])
def delete_review(name: str) -> None:
	only_managers()
	frappe.delete_doc("Shop Review", name, ignore_permissions=True, force=True)
