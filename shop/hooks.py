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

web_include_js = ["/assets/shop/js/login_signup.js"]
update_website_context = "shop.storefront.accounts.account_page_redirect"

doctype_js = {"Quotation": "public/js/quotation.js", "Lead": "public/js/lead.js"}

doc_events = {
	# a bank transfer recorded in the desk pays the order like a card payment does
	"Payment Entry": {"on_submit": "shop.storefront.payment.on_payment_entry"},
	# a bank transfer arriving in a company bank account pays the order it names
	"Bank Transaction": {"on_submit": "shop.storefront.payment.on_bank_transaction"},
	# statement runs follow the Customer Group
	"Customer": {
		"on_update": ["shop.storefront.statements.sync_customer", "shop.storefront.pricing.forget_rates"],
	},
	"Sales Order": {"before_insert": "shop.storefront.payment.forget_checkout_on_amend"},
	# prices worked out earlier in the request are worked out again
	"Item Price": {
		"on_update": "shop.storefront.pricing.forget_rates",
		"on_trash": "shop.storefront.pricing.forget_rates",
	},
	"Pricing Rule": {
		"on_update": "shop.storefront.pricing.forget_rates",
		"on_trash": "shop.storefront.pricing.forget_rates",
	},
	# and what the prices and their tax are worked out from
	**{
		doctype: {
			"on_update": "shop.storefront.pricing.forget_rates",
			"on_trash": "shop.storefront.pricing.forget_rates",
		}
		for doctype in (
			"Item",
			"Item Group",
			"Item Tax Template",
			"Price List",
			"Sales Taxes and Charges Template",
			"Shop Settings",
		)
	},
}

override_doctype_class = {
	"Payment Request": "shop.overrides.payment_request.ShopPaymentRequest",
}

after_install = "shop.install.after_install"
after_migrate = "shop.install.after_migrate"
before_uninstall = "shop.install.before_uninstall"

on_session_creation = "shop.storefront.cart.merge_guest_cart"
on_logout = "shop.storefront.cart.forget_cart"

shop_fulfillment_providers = {
	"manual": "shop.fulfillment.providers.manual.ManualProvider",
	"amazon_mcf": "shop.fulfillment.providers.amazon.AmazonProvider",
	"pickup": "shop.fulfillment.providers.pickup.PickupProvider",
}

shop_carrier_tracking_urls = {
	"Delhivery": "https://www.delhivery.com/track/package/{tracking_number}",
	"Bluedart": "https://www.bluedart.com/tracking/{tracking_number}",
	"DTDC": "https://www.dtdc.in/tracking/{tracking_number}",
}

scheduler_events = {
	"daily": [
		"shop.storefront.cart.cleanup_carts",
		"shop.storefront.payment.cancel_overdue_orders",
	],
	"hourly": [
		"shop.fulfillment.service.sync_open_shipments",
		"shop.storefront.payment.remind_unpaid_online_orders",
		"shop.storefront.cart.remind_left_carts",
		"shop.storefront.product.send_stock_alerts",
	],
}

before_tests = "shop.install.before_tests"

# Apps add live shipping rates at checkout here; see shop.storefront.shipping
shop_shipping_rate_providers = []

# Apps with their own storefront theme list its Builder Component ids here, so storefront links
# in them follow the route prefix. Other components (a site's own header) are left alone.
shop_theme_components = []

export_python_type_annotations = True
require_type_annotated_api_methods = True
