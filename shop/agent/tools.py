"""Shop capabilities exposed to the store assistant.

Every tool is a thin wrapper over the same admin API the panel uses, so the
assistant can only do what a Shop Manager could do by hand.
"""

import frappe
from flow import tool

from shop.api import analytics, carts, customers, discounts, inventory
from shop.api import orders as orders_api
from shop.api import products as products_api
from shop.api import reviews as reviews_api
from shop.api import settings as settings_api
from shop.api import variants as variants_api


@tool
def store_overview() -> dict:
	"""Sales and store health: revenue, orders, average order value, conversion,
	top products, plus counts of unfulfilled orders, low stock items and open carts."""
	return {"performance": analytics.get_overview(days=30), "today": _dashboard()}


def _dashboard() -> dict:
	from shop.api.admin import get_dashboard

	return get_dashboard()


@tool
def list_products(search: str | None = None, status: str | None = None) -> dict:
	"""List storefront products with price, stock and publish state.
	status can be "published" or "draft"."""
	return products_api.get_products(search=search, status=status, limit=50)


@tool
def product_details(product: str) -> dict:
	"""Everything about one product, including images, pricing, highlights and variants.
	Pass the product slug, for example "ceramic-mug"."""
	return products_api.get_product(product)


@tool(requires_confirmation=True)
def add_product(
	product_name: str,
	price: float,
	short_description: str | None = None,
	description: str | None = None,
	compare_at_price: float | None = None,
	opening_stock: float = 0,
	collections: list[str] | None = None,
	published: bool = True,
) -> dict:
	"""Create a new product, including its catalogue item, price and opening stock."""
	return products_api.create_product(
		product_name=product_name,
		price=price,
		short_description=short_description,
		description=description,
		compare_at_price=compare_at_price,
		opening_stock=opening_stock,
		collections=collections,
		published=published,
	)


@tool(requires_confirmation=True)
def update_product(
	product: str,
	product_name: str | None = None,
	price: float | None = None,
	compare_at_price: float | None = None,
	short_description: str | None = None,
	description: str | None = None,
	highlights: str | None = None,
	collections: list[str] | None = None,
	published: bool | None = None,
) -> dict:
	"""Change a product. Only the fields you pass are updated. highlights is one bullet per line."""
	payload = {"name": product}
	current = products_api.get_product(product)
	for field, value in {
		"product_name": product_name,
		"price": price,
		"compare_at_price": compare_at_price,
		"short_description": short_description,
		"description": description,
		"highlights": highlights,
		"collections": collections,
		"published": published,
	}.items():
		payload[field] = current.get(field) if value is None else value
	return products_api.save_product(payload)


@tool(requires_confirmation=True)
def add_product_with_options(
	product_name: str, options: list[dict], price: float, opening_stock: float = 0
) -> dict:
	"""Create a product that varies by options and build every combination.
	options looks like [{"attribute": "Size", "values": ["Small", "Large"]}]."""
	return variants_api.create_variant_product(
		product_name=product_name, options=options, price=price, opening_stock=opening_stock
	)


@tool
def list_variants(product: str) -> dict:
	"""Variants of a product with their price, stock and availability."""
	return variants_api.get_variants(product)


@tool(requires_confirmation=True)
def update_variant(
	item_code: str, price: float | None = None, stock: float | None = None, available: bool | None = None
) -> dict:
	"""Change one variant's price, stock level or whether it can be bought."""
	disabled = None if available is None else not available
	return variants_api.update_variant(item_code, price=price, stock=stock, disabled=disabled)


@tool
def stock_levels(search: str | None = None, low_only: bool = False) -> dict:
	"""Current stock for every sellable item, with low stock flagged."""
	return inventory.get_inventory(search=search, low_only=low_only, limit=100)


@tool(requires_confirmation=True)
def set_stock(item_code: str, qty: float) -> dict:
	"""Set an item's stock to an exact quantity."""
	return inventory.set_stock(item_code, qty)


@tool
def list_orders(status: str | None = None, payment: str | None = None, search: str | None = None) -> dict:
	"""Recent orders with payment and fulfillment state. payment is "Paid" or "Unpaid"."""
	return orders_api.get_orders(status=status, payment=payment, search=search, limit=50)


@tool
def order_details(order: str) -> dict:
	"""One order in full: items, totals, customer, address and activity timeline."""
	return orders_api.get_order(order)


@tool(requires_confirmation=True)
def mark_order_paid(order: str) -> dict:
	"""Record payment against an order."""
	return orders_api.mark_paid(order)


@tool(requires_confirmation=True)
def fulfill_order(order: str) -> dict:
	"""Ship an order, which files the delivery and reduces stock."""
	return orders_api.fulfill(order)


@tool(requires_confirmation=True)
def cancel_order(order: str) -> dict:
	"""Cancel an order."""
	return orders_api.cancel_order(order)


@tool
def list_customers(search: str | None = None) -> dict:
	"""Customers with how many orders they placed and what they spent."""
	return customers.get_customers(search=search, limit=50)


@tool
def customer_details(customer: str) -> dict:
	"""One customer with their orders, addresses and reviews."""
	return customers.get_customer(customer)


@tool
def open_carts() -> dict:
	"""Carts shoppers left behind, with their contents and value."""
	return carts.get_carts(status="Active", limit=50)


@tool
def list_reviews(product: str | None = None, rating: int | None = None) -> dict:
	"""Customer reviews, newest first."""
	return reviews_api.get_reviews(product=product, rating=rating, limit=50)


@tool(requires_confirmation=True)
def delete_review(review: str) -> str:
	"""Remove a review. Use the review id from list_reviews."""
	reviews_api.delete_review(review)
	return f"Deleted review {review}"


@tool
def list_discounts() -> list:
	"""Coupon codes with their value, usage and validity."""
	return discounts.get_coupons()


@tool(requires_confirmation=True)
def create_discount(
	coupon_code: str,
	discount_type: str,
	value: float,
	min_amt: float = 0,
	maximum_use: int = 0,
	valid_upto: str | None = None,
) -> str:
	"""Create a coupon code shoppers can enter at checkout.
	discount_type is "Percentage" or "Amount". valid_upto is YYYY-MM-DD."""
	discounts.save_coupon(
		{
			"coupon_code": coupon_code,
			"discount_type": discount_type,
			"value": value,
			"min_amt": min_amt,
			"maximum_use": maximum_use,
			"valid_upto": valid_upto,
			"enabled": True,
		}
	)
	return f"Created coupon {coupon_code.upper()}"


@tool(requires_confirmation=True)
def set_discount_enabled(coupon: str, enabled: bool) -> str:
	"""Turn a coupon on or off. Use the coupon id from list_discounts."""
	discounts.set_enabled(coupon, enabled)
	return f"{'Enabled' if enabled else 'Disabled'} {coupon}"


@tool
def store_settings() -> dict:
	"""Current store configuration: payments, shipping, catalogue defaults and storefront theme."""
	return settings_api.get_settings()


@tool(requires_confirmation=True)
def update_store_settings(
	store_name: str | None = None,
	enable_cod: bool | None = None,
	flat_shipping_rate: float | None = None,
	free_shipping_above: float | None = None,
	low_stock_threshold: int | None = None,
	allow_out_of_stock: bool | None = None,
) -> dict:
	"""Change store settings. Only the values you pass are updated."""
	payload = {
		field: value
		for field, value in {
			"store_name": store_name,
			"enable_cod": enable_cod,
			"flat_shipping_rate": flat_shipping_rate,
			"free_shipping_above": free_shipping_above,
			"low_stock_threshold": low_stock_threshold,
			"allow_out_of_stock": allow_out_of_stock,
		}.items()
		if value is not None
	}
	return settings_api.save_settings(payload)


@tool
def setup_progress() -> list:
	"""What is still left to do before the store is ready to sell."""
	from shop.api.admin import get_setup_guide

	return get_setup_guide()


@tool(requires_confirmation=True)
def load_sample_catalog() -> str:
	"""Fill an empty store with sample products, collections and reviews to try things out."""
	frappe.enqueue("shop.demo.setup", queue="long", job_id="shop-demo-setup")
	return "Sample catalog is being created. It appears in a few seconds."


@tool
def storefront_pages() -> list:
	"""The live storefront pages and their addresses, so they can be opened or edited in Builder."""
	settings = frappe.get_cached_doc("Shop Settings")
	return [
		{"route": f"/{row.route}", "page": row.page, "edit_in_builder": f"/builder/page/{row.page}"}
		for row in settings.theme_pages
	]
