import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from shop.routes import FRAPPE_SEGMENTS, STOREFRONT_SEGMENTS, get_prefix, normalize_prefix


class ShopSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from shop.shop.doctype.shop_bank_account.shop_bank_account import ShopBankAccount
		from shop.shop.doctype.shop_fulfillment_location.shop_fulfillment_location import (
			ShopFulfillmentLocation,
		)
		from shop.shop.doctype.shop_import_duty.shop_import_duty import ShopImportDuty
		from shop.shop.doctype.shop_payment_gateway.shop_payment_gateway import ShopPaymentGateway
		from shop.shop.doctype.shop_theme_page.shop_theme_page import ShopThemePage

		active_theme: DF.Data | None
		allow_out_of_stock: DF.Check
		allow_quote_requests: DF.Check
		allow_trade_applications: DF.Check
		applied_route_prefix: DF.Data | None
		bank_accounts: DF.Table[ShopBankAccount]
		bank_charges_account: DF.Link | None
		bank_transfer_days: DF.Int
		business_buyer_label: DF.SmallText | None
		cancel_unpaid_orders: DF.Check
		cart_reminder_hours: DF.Int
		card_fee_item: DF.Link | None
		company: DF.Link | None
		conversion_fee_item: DF.Link | None
		currency: DF.Link | None
		customers_land_in_store: DF.Check
		delivery_days: DF.Int
		duties_item: DF.Link | None
		email_statements: DF.Check
		enable_bank_transfer: DF.Check
		enable_cod: DF.Check
		export_tax_template: DF.Link | None
		flat_shipping_rate: DF.Currency
		fulfillment_locations: DF.Table[ShopFulfillmentLocation]
		free_shipping_above: DF.Currency
		import_duties: DF.Table[ShopImportDuty]
		invoice_paid_orders: DF.Check
		low_stock_threshold: DF.Int
		onboarding_complete: DF.Check
		online_payment_days: DF.Int
		order_naming_series: DF.Data | None
		other_currencies_with_tax: DF.Check
		payment_gateways: DF.Table[ShopPaymentGateway]
		payment_reminder_hours: DF.Int
		price_list: DF.Link | None
		prices_include_tax: DF.Check
		quote_valid_days: DF.Int
		require_terms: DF.Check
		return_window_days: DF.Int
		route_prefix: DF.Data | None
		send_shipping_emails: DF.Check
		shipping_account: DF.Link | None
		shipping_item: DF.Link | None
		show_prices_with_tax: DF.Check
		staff_notification_emails: DF.SmallText | None
		store_logo: DF.AttachImage | None
		store_name: DF.Data | None
		tax_template: DF.Link | None
		terms_and_conditions: DF.Link | None
		terms_checkbox_note: DF.SmallText | None
		terms_url: DF.Data | None
		theme_pages: DF.Table[ShopThemePage]
		trade_customer_group: DF.Link | None
		transfer_fee_item: DF.Link | None
		weight_uom: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_order_naming_series()
		self.validate_fulfillment_locations()
		self.validate_import_duties()
		self.validate_price_list_currency()
		self.validate_staff_emails()
		self.route_prefix = normalize_prefix(self.route_prefix)
		first_segment = self.route_prefix.split("/")[0] if self.route_prefix else ""
		if first_segment in STOREFRONT_SEGMENTS:
			frappe.throw(
				_("Route Prefix can't start with {0}, the storefront already uses that path.").format(
					frappe.bold(first_segment)
				)
			)
		if first_segment in FRAPPE_SEGMENTS:
			frappe.throw(
				_("Route Prefix can't start with {0}, the site already uses that path.").format(
					frappe.bold(first_segment)
				)
			)

	def validate_staff_emails(self):
		from frappe.utils import validate_email_address

		for email in (self.staff_notification_emails or "").replace(",", "\n").splitlines():
			if email.strip():
				validate_email_address(email.strip(), throw=True)
		if self.delivery_days is not None and cint(self.delivery_days) < 0:
			frappe.throw(_("Delivery Days can't be negative"))

	def validate_price_list_currency(self):
		"""The store prices in its company's currency; other currencies are converted from it."""
		if not (self.price_list and self.company):
			return
		listed = frappe.db.get_value("Price List", self.price_list, "currency")
		company = frappe.get_cached_value("Company", self.company, "default_currency")
		if listed and company and listed != company:
			frappe.throw(
				_("Price List {0} is in {1}. Pick a Price List in {2}, the currency of {3}.").format(
					frappe.bold(self.price_list), listed, company, self.company
				)
			)

	def validate_fulfillment_locations(self):
		from shop.fulfillment.provider import get_provider, registry

		seen = set()
		providers = registry()
		for row in self.fulfillment_locations:
			if row.warehouse in seen:
				frappe.throw(_("Warehouse {0} is listed twice").format(frappe.bold(row.warehouse)))
			seen.add(row.warehouse)
			found = frappe.db.get_value("Warehouse", row.warehouse, ["company", "is_group"])
			if not found:
				frappe.throw(_("Warehouse {0} doesn't exist").format(frappe.bold(row.warehouse)))
			company, is_group = found
			if is_group:
				frappe.throw(
					_("{0} is a group warehouse: pick the warehouse stock is kept in").format(row.warehouse)
				)
			if self.company and company != self.company:
				frappe.throw(_("Warehouse {0} belongs to another company").format(frappe.bold(row.warehouse)))
			row.fulfillment_provider = row.fulfillment_provider or "manual"
			if row.fulfillment_provider not in providers:
				frappe.throw(
					_("Fulfillment provider {0} is not installed").format(
						frappe.bold(row.fulfillment_provider)
					)
				)
			if not get_provider(row.fulfillment_provider).for_locations:
				frappe.throw(
					_(
						"{0} is chosen by the customer for an order; turn on collection for the location instead"
					).format(get_provider(row.fulfillment_provider).label)
				)
			self.check_ship_from(row)

	def validate_import_duties(self):
		seen = set()
		for row in self.import_duties:
			if row.country in seen:
				frappe.throw(_("{0} is listed twice in Import Duties").format(frappe.bold(row.country)))
			seen.add(row.country)
		if self.import_duties and not self.duties_item:
			frappe.throw(_("Set the Duties Item that charges import duties on orders"))

	def check_ship_from(self, row) -> None:
		warning = self.ship_from_warning(row)
		if warning:
			frappe.msgprint(warning, indicator="orange", alert=True)

	def ship_from_warning(self, row) -> str | None:
		"""Why a location's provider can't send from it: it has no address, or one that isn't the
		company's (ERPNext's Shipment sends only from the company's addresses)."""
		from shop.fulfillment.provider import get_provider, registry
		from shop.storefront.stock import warehouse_address

		if (row.fulfillment_provider or "manual") not in registry():
			return None
		provider = get_provider(row.fulfillment_provider or "manual")
		if not getattr(provider, "needs_ship_from", False):
			return None
		address = row.ship_from_address or warehouse_address(row.warehouse) or provider.default_ship_from()
		if not address:
			return _(
				"{0} has no address to send parcels from. Add one to the warehouse, or pick a Ship From Address."
			).format(row.warehouse)
		if self.company and not frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": "Address",
				"parent": address,
				"link_doctype": "Company",
				"link_name": self.company,
			},
		):
			return _(
				"Address {0} isn't linked to {1}: ERPNext ships only from the company's addresses. Link it in Desk."
			).format(address, self.company)
		return None

	def validate_order_naming_series(self):
		if not self.order_naming_series:
			return
		options = (frappe.get_meta("Sales Order").get_field("naming_series").options or "").split("\n")
		if self.order_naming_series not in options:
			frappe.throw(
				_("Add {0} to Sales Order in Document Naming Settings first.").format(
					frappe.bold(self.order_naming_series)
				)
			)

	def on_update(self):
		# the storefront reads the cached settings, which Frappe refreshes only after on_update
		self.clear_cache()
		if self.has_value_changed("require_terms"):
			from shop.install import enable_customer_signup

			enable_customer_signup()
		if self.active_theme and get_prefix() != normalize_prefix(self.applied_route_prefix):
			from shop.themes import apply_route_prefix

			apply_route_prefix()
		from shop.storefront.accounts import sync_customer_home_page

		sync_customer_home_page()
