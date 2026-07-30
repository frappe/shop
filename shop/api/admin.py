import frappe
from frappe.utils import add_days, nowdate

from shop.api import only_managers
from shop.storefront import pricing


@frappe.whitelist()
def check_app_permission() -> bool:
	if frappe.session.user == "Administrator":
		return True
	return "Shop Manager" in frappe.get_roles()


@frappe.whitelist()
def get_setup_guide() -> list[dict]:
	only_managers()
	settings = frappe.get_cached_doc("Shop Settings")
	return [
		{
			"key": "store",
			"label": "Name your store",
			"done": bool(settings.store_name and settings.onboarding_complete),
			"route": "/settings",
		},
		{
			"key": "product",
			"label": "Add your first product",
			"done": bool(frappe.db.count("Shop Product", {"published": 1})),
			"route": "/products",
		},
		{
			"key": "storefront",
			"label": "Customize your storefront",
			"done": storefront_customized(),
			"href": "/builder",
		},
		{
			"key": "payments",
			"label": "Set up payments",
			"done": bool(settings.enable_cod or settings.payment_gateway_account),
			"route": "/settings",
		},
		{
			"key": "order",
			"label": "Place a test order",
			"done": bool(frappe.db.count("Sales Order", {"docstatus": 1})),
			"href": "/",
		},
	]


def storefront_customized() -> bool:
	from frappe.utils import add_to_date

	settings = frappe.get_cached_doc("Shop Settings")
	for row in settings.theme_pages:
		page = frappe.db.get_value("Builder Page", row.page, ["creation", "modified"], as_dict=True)
		if page and page.modified > add_to_date(page.creation, minutes=5):
			return True
	return False


@frappe.whitelist()
def get_dashboard() -> dict:
	only_managers()
	return {
		"orders_today": frappe.db.count("Sales Order", {"docstatus": 1, "transaction_date": nowdate()}),
		"revenue_week": pricing.format_amount(week_revenue()),
		"active_carts": frappe.db.count("Shop Cart", {"status": "Active"}),
		"published_products": frappe.db.count("Shop Product", {"published": 1}),
		"pending_fulfillment": frappe.db.count(
			"Sales Order", {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]}
		),
		"low_stock": low_stock_count(),
	}


def week_revenue() -> float:
	rows = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1, "transaction_date": [">=", add_days(nowdate(), -7)]},
		fields=["grand_total"],
	)
	return sum(row.grand_total for row in rows)


def low_stock_count() -> int:
	from shop.api.inventory import get_inventory

	return get_inventory(low_only=True, limit=200)["total"]


@frappe.whitelist()
def search_items(query: str = "") -> list[dict]:
	only_managers()
	filters = {"disabled": 0, "variant_of": ["is", "not set"]}
	or_filters = None
	if query:
		term = f"%{query}%"
		or_filters = [["item_code", "like", term], ["item_name", "like", term]]
	return frappe.get_all(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "item_name", "item_group", "has_variants"],
		limit=20,
	)
