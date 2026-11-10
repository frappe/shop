import frappe

from shop import themes
from shop.api.settings import GATEWAY_FIELDS


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
		"has_sample_products": has_sample_products(),
		"enable_cod": settings.enable_cod,
		"payment_gateways": [row.payment_gateway for row in settings.payment_gateways],
		"gateway_accounts": gateway_accounts(),
	}


def gateway_accounts() -> list[dict]:
	return frappe.get_all(
		"Payment Gateway Account",
		fields=["name", "payment_gateway", "currency", "is_default"],
	)


@frappe.whitelist(methods=["POST"])
def update_payments(enable_cod: bool = True, payment_gateways: list | None = None) -> None:
	"""Turn the store's online gateways on and off; one kept on keeps its label and fees."""
	frappe.only_for(("Shop Manager", "System Manager"))
	wanted = list(dict.fromkeys(frappe.parse_json(payment_gateways) or []))
	settings = frappe.get_doc("Shop Settings")
	settings.enable_cod = 1 if enable_cod else 0
	kept = {row.payment_gateway: row for row in settings.payment_gateways}
	settings.set("payment_gateways", [])
	for gateway in wanted:
		row = kept.get(gateway)
		settings.append(
			"payment_gateways",
			{field: row.get(field) for field in GATEWAY_FIELDS} if row else {"payment_gateway": gateway},
		)
	settings.save(ignore_permissions=True)


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


def has_sample_products() -> bool:
	from shop.demo import DEMO_PREFIX

	return bool(frappe.db.exists("Shop Product", {"item": ["like", f"{DEMO_PREFIX}%"]}))


@frappe.whitelist(methods=["POST"])
def remove_demo_data() -> None:
	"""Take the sample products, their collections, prices and stock out of the store."""
	from shop.demo import teardown

	frappe.only_for(("Shop Manager", "System Manager"))
	teardown()


@frappe.whitelist(methods=["POST"])
def complete() -> None:
	frappe.only_for(("Shop Manager", "System Manager"))
	frappe.db.set_single_value("Shop Settings", "onboarding_complete", 1)


def fill_commerce_defaults(settings):
	if not settings.company:
		settings.company = frappe.db.get_value("Company", {}, "name")
	if not settings.price_list:
		settings.price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	add_first_location(settings)


def add_first_location(settings, warehouse: str | None = None) -> None:
	"""A store without a fulfillment location sells from ERPNext's default warehouse (Stock
	Settings) when it is the company's, else from the company's first warehouse."""
	if settings.get("fulfillment_locations"):
		return
	default = frappe.db.get_single_value("Stock Settings", "default_warehouse")
	warehouse = (
		warehouse
		or (default if default and frappe.db.get_value("Warehouse", default, "company") == settings.company else None)
		or frappe.db.get_value(
			"Warehouse", {"company": settings.company, "is_group": 0, "disabled": 0}, "name", order_by="lft"
		)
	)
	if warehouse:
		settings.append("fulfillment_locations", {"warehouse": warehouse, "fulfillment_provider": "manual"})
