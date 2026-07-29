app_name = "shop"
app_title = "Shop"
app_publisher = "Frappe"
app_description = "B2C e-commerce storefront powered by Frappe Builder and ERPNext"
app_email = "suraj@frappe.io"
app_license = "mit"

use_json_request_body = True

required_apps = ["frappe", "erpnext", "payments", "builder"]

add_to_apps_screen = [
	{
		"name": "shop",
		"logo": "/assets/shop/frontend/shop-logo.svg",
		"title": "Shop",
		"route": "/shop",
		"has_permission": "shop.api.admin.check_app_permission",
	}
]

website_route_rules = [
	{"from_route": "/shop/<path:app_path>", "to_route": "shop"},
]

after_install = "shop.install.after_install"
after_migrate = "shop.install.after_migrate"

on_session_creation = "shop.storefront.cart.merge_guest_cart"

scheduler_events = {
	"daily": [
		"shop.storefront.cart.cleanup_carts",
	],
}

before_tests = "shop.install.before_tests"

export_python_type_annotations = True
require_type_annotated_api_methods = True
