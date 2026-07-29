import frappe

from shop import themes


@frappe.whitelist()
def get_state() -> dict:
	frappe.only_for(("Shop Manager", "System Manager"))
	settings = frappe.get_cached_doc("Shop Settings")
	return {
		"onboarding_complete": settings.onboarding_complete,
		"store_name": settings.store_name,
		"store_logo": settings.store_logo,
		"active_theme": settings.active_theme,
		"themes": themes.list_themes(),
		"has_demo_data": bool(frappe.db.count("Shop Product")),
	}


@frappe.whitelist(methods=["POST"])
def setup_store(store_name: str, store_logo: str | None = None) -> None:
	frappe.only_for(("Shop Manager", "System Manager"))
	settings = frappe.get_doc("Shop Settings")
	settings.store_name = store_name
	if store_logo:
		settings.store_logo = store_logo
	fill_commerce_defaults(settings)
	settings.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def load_demo_data() -> None:
	frappe.only_for(("Shop Manager", "System Manager"))
	frappe.enqueue("shop.demo.setup", queue="long", job_id="shop-demo-setup")


@frappe.whitelist(methods=["POST"])
def complete() -> None:
	frappe.only_for(("Shop Manager", "System Manager"))
	frappe.db.set_single_value("Shop Settings", "onboarding_complete", 1)


def fill_commerce_defaults(settings):
	if not settings.company:
		settings.company = frappe.db.get_value("Company", {}, "name")
	if not settings.price_list:
		settings.price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	if not settings.default_warehouse:
		settings.default_warehouse = frappe.db.get_value(
			"Warehouse", {"company": settings.company, "warehouse_name": "Stores"}, "name"
		)
