def execute():
	from shop.patches.set_order_policy_defaults import execute as set_defaults
	from shop.storefront.accounts import sync_customer_home_page

	set_defaults()
	sync_customer_home_page()
