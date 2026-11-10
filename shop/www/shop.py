import frappe

from shop.routes import store_url

no_cache = 1


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	# Storefront base path for links from the admin to live pages ("" or "/store")
	base = store_url()
	context.boot = {"shop_route_prefix": "" if base == "/" else base}
