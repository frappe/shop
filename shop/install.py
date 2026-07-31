import os

import click

import frappe


def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	create_shop_manager_role()
	sync_templates()
	sync_agent()
	enable_customer_signup()
	warn_if_server_scripts_disabled()


def enable_customer_signup():
	"""Shoppers need accounts to track orders, so the store cannot ship with signup off."""
	if frappe.db.get_single_value("Website Settings", "disable_signup"):
		frappe.db.set_single_value("Website Settings", "disable_signup", 0)


def sync_agent():
	from shop.agent.setup import sync

	sync()


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


def warn_if_server_scripts_disabled():
	if not frappe.conf.server_script_enabled:
		click.secho(
			"Shop storefront pages require server scripts. "
			"Set server_script_enabled: 1 in site config.",
			fg="yellow",
		)


def before_tests():
	frappe.clear_cache()
	from shop.demo import setup as setup_demo_data

	setup_demo_data()
