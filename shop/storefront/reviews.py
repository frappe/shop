import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, format_date


@frappe.whitelist(allow_guest=True)
def get_reviews(product: str, start: int = 0, limit: int = 10) -> dict:
	rows = frappe.get_all(
		"Shop Review",
		filters={"product": product},
		fields=["reviewer_name", "rating", "title", "review", "verified", "creation"],
		order_by="creation desc",
		start=cint(start),
		limit=min(cint(limit) or 10, 50),
	)
	for row in rows:
		row.posted_on = format_date(row.creation, "MMM yyyy")
		row.stars = "★" * row.rating + "☆" * (5 - row.rating)
		del row["creation"]
	return {"reviews": rows, **summary(product)}


def summary(product: str) -> dict:
	ratings = frappe.get_all("Shop Review", filters={"product": product}, pluck="rating")
	count = len(ratings)
	average = round(sum(ratings) / count, 1) if count else 0
	histogram = []
	for stars in range(5, 0, -1):
		star_count = ratings.count(stars)
		histogram.append(
			{
				"stars": stars,
				"count": star_count,
				"percent": round(star_count * 100 / count) if count else 0,
			}
		)
	return {"average": average, "count": count, "histogram": histogram}


def summaries(products: list[str]) -> dict:
	if not products:
		return {}
	rows = frappe.get_all(
		"Shop Review",
		filters={"product": ["in", products]},
		fields=["product", "rating"],
	)
	grouped = {}
	for row in rows:
		grouped.setdefault(row.product, []).append(row.rating)
	return {
		product: {"average": round(sum(ratings) / len(ratings), 1), "count": len(ratings)}
		for product, ratings in grouped.items()
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def add_review(product: str, rating: int, title: str | None = None, review: str | None = None) -> dict:
	if frappe.session.user in ("Guest", None):
		frappe.throw(_("Please sign in to review"), frappe.PermissionError)
	if not frappe.db.exists("Shop Product", {"name": product, "published": 1}):
		frappe.throw(_("Product not found"), frappe.DoesNotExistError)
	frappe.get_doc(
		{
			"doctype": "Shop Review",
			"product": product,
			"rating": cint(rating),
			"title": title,
			"review": review,
			"reviewer_name": frappe.utils.get_fullname(frappe.session.user),
			"user": frappe.session.user,
			"verified": 1 if has_purchased(product) else 0,
		}
	).insert(ignore_permissions=True)
	return get_reviews(product)


def has_purchased(product: str) -> bool:
	from shop.storefront.orders import session_customers

	customers = session_customers()
	if not customers:
		return False
	item = frappe.db.get_value("Shop Product", product, "item")
	items = [item, *frappe.get_all("Item", filters={"variant_of": item}, pluck="name")]
	return bool(
		frappe.db.sql(
			"""select 1 from `tabSales Order Item` soi
			join `tabSales Order` so on so.name = soi.parent
			where so.docstatus = 1 and so.customer in %(customers)s
			and soi.item_code in %(items)s limit 1""",
			{"customers": customers, "items": items},
		)
	)
