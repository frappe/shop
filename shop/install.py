import os

import click
import frappe

TRADE_SOURCE = "Store Trade Application"


def after_install():
	from shop.patches.set_order_policy_defaults import execute as set_order_policy_defaults

	setup()
	set_order_policy_defaults()


def after_migrate():
	setup()


def before_uninstall():
	"""Remove the fields Shop added to other apps' documents."""
	for doctype, fields in custom_fields().items():
		for field in fields:
			name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})
			if name:
				frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def setup():
	create_shop_manager_role()
	create_custom_fields()
	create_email_templates()
	sync_templates()
	apply_default_theme()
	apply_route_prefix()
	sync_customer_home_page()
	sync_agent()
	enable_customer_signup()
	list_store_sitemap()
	warn_if_server_scripts_disabled()


def list_store_sitemap():
	"""Point search engines to the store's sitemap (www/store_sitemap.py) from robots.txt, once:
	what the site has there already is kept."""
	robots = frappe.db.get_single_value("Website Settings", "robots_txt") or ""
	if "store_sitemap.xml" in robots:
		return
	line = f"Sitemap: {frappe.utils.get_url('/store_sitemap.xml')}"
	frappe.db.set_single_value("Website Settings", "robots_txt", f"{robots.rstrip()}\n{line}".strip())


def sync_customer_home_page():
	from shop.storefront.accounts import sync_customer_home_page as sync

	sync()


def enable_customer_signup():
	"""Shoppers need accounts to track orders, so the store cannot ship with signup off.

	When the store requires its terms, accounts are made on the store's own sign-up page,
	which asks for them, so the site's generic sign-up stays off."""
	if frappe.db.get_single_value("Shop Settings", "require_terms"):
		frappe.db.set_single_value("Website Settings", "disable_signup", 1)
	elif frappe.db.get_single_value("Website Settings", "disable_signup"):
		frappe.db.set_single_value("Website Settings", "disable_signup", 0)


def create_email_templates():
	from shop.storefront.emails import ensure_templates

	ensure_templates()


def sync_agent():
	from shop.agent.setup import sync

	sync()


def custom_fields() -> dict:
	"""The fields Shop adds to ERPNext's documents: the store details of orders, quotations,
	customers, trade applications (Leads), the terms a user accepted and where products are sent."""
	return {
		"Sales Order": [
			{
				"fieldname": "shop_section",
				"fieldtype": "Section Break",
				"label": "Online Store",
				"insert_after": "terms",
				"collapsible": 1,
			},
			{
				"fieldname": "shop_payment_method",
				"no_copy": 1,
				"fieldtype": "Data",
				"label": "Payment Method",
				"read_only": 1,
				"insert_after": "shop_section",
				"allow_on_submit": 1,
			},
			{
				"fieldname": "shop_payment_gateway",
				"no_copy": 1,
				"fieldtype": "Link",
				"options": "Payment Gateway",
				"label": "Payment Gateway",
				"read_only": 1,
				"depends_on": "shop_payment_gateway",
				"insert_after": "shop_payment_method",
			},
			{
				"fieldname": "shop_payment_due",
				"no_copy": 1,
				"fieldtype": "Date",
				"label": "Payment Due",
				"insert_after": "shop_payment_gateway",
				"allow_on_submit": 1,
				"description": "Unpaid store orders are cancelled after this date",
			},
			{
				"fieldname": "shop_shipping_option",
				"no_copy": 1,
				"fieldtype": "Small Text",
				"label": "Shipping Chosen",
				"read_only": 1,
				"insert_after": "shop_payment_due",
			},
			{
				"fieldname": "shop_order_note",
				"no_copy": 1,
				"fieldtype": "Small Text",
				"label": "Customer's Note",
				"read_only": 1,
				"insert_after": "shop_shipping_option",
			},
			{"fieldname": "shop_column", "fieldtype": "Column Break", "insert_after": "shop_order_note"},
			{
				"fieldname": "shop_terms_version",
				"no_copy": 1,
				"fieldtype": "Data",
				"label": "Terms Accepted",
				"read_only": 1,
				"insert_after": "shop_column",
			},
			{
				"fieldname": "shop_terms_accepted_on",
				"no_copy": 1,
				"fieldtype": "Datetime",
				"label": "Terms Accepted On",
				"read_only": 1,
				"insert_after": "shop_terms_version",
			},
			{
				"fieldname": "shop_business_buyer",
				"no_copy": 1,
				"fieldtype": "Check",
				"label": "Business Buyer",
				"read_only": 1,
				"insert_after": "shop_terms_accepted_on",
				"description": "Confirmed at checkout that they are buying for business purposes",
			},
			{
				"fieldname": "shop_access_token",
				"fieldtype": "Data",
				"label": "Access Token",
				"hidden": 1,
				"read_only": 1,
				"no_copy": 1,
				"insert_after": "shop_business_buyer",
			},
		],
		"Quotation": [
			{
				"fieldname": "shop_section",
				"fieldtype": "Section Break",
				"label": "Online Store",
				"insert_after": "terms",
				"collapsible": 1,
			},
			{
				"fieldname": "shop_request_message",
				"fieldtype": "Small Text",
				"label": "Customer's Request",
				"read_only": 1,
				"insert_after": "shop_section",
			},
			{
				"fieldname": "shop_shipping_option",
				"no_copy": 1,
				"fieldtype": "Small Text",
				"label": "Shipping Chosen",
				"read_only": 1,
				"insert_after": "shop_request_message",
			},
			{
				"fieldname": "shop_access_token",
				"fieldtype": "Data",
				"label": "Access Token",
				"hidden": 1,
				"read_only": 1,
				"no_copy": 1,
				"insert_after": "shop_shipping_option",
			},
		],
		"Customer": [
			{
				"fieldname": "shop_allow_on_account",
				"fieldtype": "Check",
				"label": "Pay on Account at the Store",
				"insert_after": "payment_terms",
				"description": "Can order online and pay by invoice under their payment terms and credit limit",
			},
		],
		# trade account applications from the store are ERPNext Leads (UTM Source: TRADE_SOURCE)
		"Lead": [
			{
				"fieldname": "shop_trade_section",
				"fieldtype": "Section Break",
				"label": "Trade Account Application",
				"insert_after": "utm_campaign",
				"collapsible": 1,
				"depends_on": f"eval:doc.utm_source == '{TRADE_SOURCE}'",
			},
			{
				"fieldname": "shop_tax_id",
				"fieldtype": "Data",
				"label": "Tax ID",
				"insert_after": "shop_trade_section",
				"description": "The tax number the business gave. Copied to the Customer when approved.",
			},
			{
				"fieldname": "shop_company_number",
				"fieldtype": "Data",
				"label": "Company Number",
				"insert_after": "shop_tax_id",
			},
			{
				"fieldname": "shop_user",
				"fieldtype": "Link",
				"options": "User",
				"label": "Applied As",
				"read_only": 1,
				"insert_after": "shop_company_number",
				"description": "The store login that applied, if they were signed in",
			},
			{"fieldname": "shop_trade_column", "fieldtype": "Column Break", "insert_after": "shop_user"},
			{
				"fieldname": "shop_terms_version",
				"no_copy": 1,
				"fieldtype": "Data",
				"label": "Terms Accepted",
				"read_only": 1,
				"insert_after": "shop_trade_column",
			},
			{
				"fieldname": "shop_terms_accepted_on",
				"no_copy": 1,
				"fieldtype": "Datetime",
				"label": "Terms Accepted On",
				"read_only": 1,
				"insert_after": "shop_terms_version",
			},
		],
		"Item": [
			{
				"fieldname": "shop_shipping_restriction",
				"fieldtype": "Link",
				"options": "Shop Shipping Restriction",
				"label": "Shipping Restriction",
				"insert_after": "customs_tariff_number",
				"description": "Where the store can send it. Empty follows its Item Group",
			},
		],
		"Item Group": [
			{
				"fieldname": "shop_shipping_restriction",
				"fieldtype": "Link",
				"options": "Shop Shipping Restriction",
				"label": "Shipping Restriction",
				"insert_after": "is_group",
				"description": "Where the store can send its items. Empty follows its parent group",
			},
		],
		"User": [
			{
				"fieldname": "shop_terms_version",
				"no_copy": 1,
				"fieldtype": "Data",
				"label": "Store Terms Accepted",
				"read_only": 1,
				"insert_after": "user_type",
			},
			{
				"fieldname": "shop_terms_accepted_on",
				"no_copy": 1,
				"fieldtype": "Datetime",
				"label": "Store Terms Accepted On",
				"read_only": 1,
				"insert_after": "shop_terms_version",
			},
		],
	}


def create_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as create

	create(custom_fields(), ignore_validate=True)
	if frappe.db.table_exists("UTM Source") and not frappe.db.exists("UTM Source", TRADE_SOURCE):
		frappe.get_doc(
			{
				"doctype": "UTM Source",
				"__newname": TRADE_SOURCE,
				"description": "Trade account applications made in the store",
			}
		).insert(ignore_permissions=True)


def create_shop_manager_role():
	if frappe.db.exists("Role", "Shop Manager"):
		return
	frappe.get_doc({"doctype": "Role", "role_name": "Shop Manager", "desk_access": 1}).insert(
		ignore_permissions=True
	)


def sync_templates():
	if not os.path.exists(frappe.get_app_path("shop", "builder_templates")):
		return
	from builder.template_sync import sync_builder_templates

	from shop.themes import organize_template_folders

	sync_builder_templates(app="shop", publish=False)
	organize_template_folders()


def apply_default_theme():
	from shop.themes import ensure_default_theme

	ensure_default_theme()


def apply_route_prefix():
	"""Keep the live storefront on the configured route prefix.

	Migrate re-imports theme components with root links, so this runs every time.
	"""
	if not frappe.db.get_single_value("Shop Settings", "active_theme"):
		return
	from shop.themes import apply_route_prefix as apply

	apply()


def warn_if_server_scripts_disabled():
	from frappe.utils.safe_exec import is_safe_exec_enabled

	if not is_safe_exec_enabled():
		click.secho(
			"Shop storefront pages require server scripts. "
			"Run: bench set-config --global server_script_enabled 1",
			fg="yellow",
		)


def before_tests():
	frappe.clear_cache()
	from shop.demo import setup as setup_demo_data

	setup_demo_data()
