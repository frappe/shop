import frappe
from frappe import _
from frappe.utils import cint, flt

from shop.api import only_managers
from shop.storefront import address_lookup

EDITABLE = (
	"store_name",
	"store_logo",
	"enable_cod",
	"allow_out_of_stock",
	"prices_include_tax",
	"tax_template",
	"flat_shipping_rate",
	"free_shipping_above",
	"shipping_account",
	"low_stock_threshold",
	"price_list",
	"show_prices_with_tax",
	"other_currencies_with_tax",
	"export_tax_template",
	"shipping_item",
	"card_fee_item",
	"enable_bank_transfer",
	"bank_transfer_days",
	"conversion_fee_item",
	"transfer_fee_item",
	"duties_item",
	"bank_charges_account",
	"invoice_paid_orders",
	"cancel_unpaid_orders",
	"online_payment_days",
	"order_naming_series",
	"payment_reminder_hours",
	"cart_reminder_hours",
	"return_window_days",
	"quote_valid_days",
	"send_shipping_emails",
	"require_terms",
	"terms_and_conditions",
	"terms_url",
	"trade_customer_group",
	"email_statements",
	"allow_quote_requests",
	"allow_trade_applications",
	"staff_notification_emails",
	"delivery_days",
	"weight_uom",
	"route_prefix",
	"customers_land_in_store",
	"menu_label",
	"business_buyer_label",
	"terms_checkbox_note",
)
CHECKS = {
	"enable_cod",
	"allow_out_of_stock",
	"prices_include_tax",
	"show_prices_with_tax",
	"other_currencies_with_tax",
	"enable_bank_transfer",
	"invoice_paid_orders",
	"cancel_unpaid_orders",
	"send_shipping_emails",
	"require_terms",
	"email_statements",
	"allow_quote_requests",
	"allow_trade_applications",
	"customers_land_in_store",
}
AMOUNTS = {
	"flat_shipping_rate",
	"free_shipping_above",
}
COUNTS = {
	"cart_reminder_hours",
	"low_stock_threshold",
	"bank_transfer_days",
	"online_payment_days",
	"payment_reminder_hours",
	"return_window_days",
	"quote_valid_days",
	"delivery_days",
}
LOCATION_FIELDS = (
	"warehouse",
	"display_name",
	"fulfillment_provider",
	"ship_from_address",
	"auto_send",
	"show_stock",
	"allow_pickup",
	"pickup_instructions",
)
GATEWAY_FIELDS = (
	"payment_gateway",
	"label",
	"fee_label",
	"fee_percent",
	"fee_fixed",
	"fee_percent_international",
	"fee_fixed_international",
)
SURCHARGE_FIELDS = (
	"label",
	"enabled",
	"destination",
	"postcodes",
	"address_contains",
	"services",
	"weight_from",
	"weight_to",
	"value_from",
	"value_to",
	"charge_type",
	"amount",
	"amount_includes_tax",
)
DUTY_FIELDS = ("country", "duty_rate", "fee_on_duty", "fee_per_parcel", "duty_free_up_to")
BANK_ACCOUNT_FIELDS = (
	"bank_account",
	"label",
	"branch_code_label",
	"conversion_fee_percent",
	"local_transfer_fee",
	"swift_transfer_fee",
	"instructions",
)


def shipping_restrictions() -> dict:
	"""The store's shipping restrictions, and the Item Groups that use one."""
	return {
		"shipping_restrictions": [
			{
				"name": doc.name,
				"ships_to": doc.ships_to,
				"countries": [row.country for row in doc.countries],
				"customer_note": doc.customer_note or "",
			}
			for doc in (
				frappe.get_doc("Shop Shipping Restriction", name)
				for name in frappe.get_all("Shop Shipping Restriction", order_by="name", pluck="name")
			)
		],
		"item_group_restrictions": frappe.get_all(
			"Item Group",
			filters={"shop_shipping_restriction": ["is", "set"]},
			fields=["name as item_group", "shop_shipping_restriction as restriction"],
			order_by="lft",
		),
	}


@frappe.whitelist(methods=["POST"])
def save_shipping_restrictions(restrictions: list, item_groups: list) -> dict:
	"""Save the restrictions as listed, remove the ones taken off the list, and set which Item
	Groups use which."""
	only_managers()
	keep = []
	for row in restrictions or []:
		name = (row.get("name") or "").strip()
		if not name:
			continue
		doc = (
			frappe.get_doc("Shop Shipping Restriction", name)
			if frappe.db.exists("Shop Shipping Restriction", name)
			else frappe.new_doc("Shop Shipping Restriction")
		)
		doc.restriction_name = name
		doc.ships_to = row.get("ships_to") or "Only to these countries"
		doc.customer_note = row.get("customer_note") or None
		doc.set("countries", [{"country": country} for country in row.get("countries") or []])
		doc.save(ignore_permissions=True)
		keep.append(doc.name)
	wanted = {
		row.get("item_group"): row.get("restriction") for row in item_groups or [] if row.get("item_group")
	}
	for group in frappe.get_all(
		"Item Group", filters={"shop_shipping_restriction": ["is", "set"]}, pluck="name"
	):
		wanted.setdefault(group, None)
	for group, restriction in wanted.items():
		if not frappe.db.exists("Item Group", group):
			frappe.throw(_("Item Group {0} doesn't exist").format(frappe.bold(group)))
		if restriction and restriction not in keep:
			frappe.throw(_("Shipping restriction {0} isn't in the list").format(frappe.bold(restriction)))
		frappe.db.set_value("Item Group", group, "shop_shipping_restriction", restriction or None)
		frappe.clear_document_cache("Item Group", group)
	for name in frappe.get_all(
		"Shop Shipping Restriction", filters={"name": ["not in", keep or [""]]}, pluck="name"
	):
		frappe.delete_doc("Shop Shipping Restriction", name, ignore_permissions=True)
	return shipping_restrictions()


def shipping_surcharges() -> list[dict]:
	return [
		{
			"name": doc.name,
			**{field: doc.get(field) for field in SURCHARGE_FIELDS},
			"countries": [row.country for row in doc.countries],
		}
		for doc in (
			frappe.get_doc("Shop Shipping Surcharge", name)
			for name in frappe.get_all("Shop Shipping Surcharge", order_by="surcharge_name", pluck="name")
		)
	]


@frappe.whitelist(methods=["POST"])
def save_shipping_surcharges(surcharges: list) -> list[dict]:
	"""Save the surcharges as listed and remove the ones taken off the list."""
	only_managers()
	keep = []
	for row in surcharges or []:
		name = (row.get("name") or "").strip()
		if not name:
			continue
		doc = (
			frappe.get_doc("Shop Shipping Surcharge", name)
			if frappe.db.exists("Shop Shipping Surcharge", name)
			else frappe.new_doc("Shop Shipping Surcharge")
		)
		doc.surcharge_name = name
		doc.update({field: row.get(field) for field in SURCHARGE_FIELDS if field in row})
		doc.set("countries", [{"country": country} for country in row.get("countries") or []])
		doc.save(ignore_permissions=True)
		keep.append(doc.name)
	for name in frappe.get_all(
		"Shop Shipping Surcharge", filters={"name": ["not in", keep or [""]]}, pluck="name"
	):
		frappe.delete_doc("Shop Shipping Surcharge", name, ignore_permissions=True)
	return shipping_surcharges()


@frappe.whitelist()
def get_settings() -> dict:
	only_managers()
	settings = frappe.get_doc("Shop Settings")
	payload = {field: settings.get(field) for field in EDITABLE}
	payload.update(
		{
			# ERPNext's own settings, shown here because every web order uses them
			"new_customer_group": frappe.db.get_single_value("Selling Settings", "customer_group"),
			"round_order_totals": not cint(
				frappe.db.get_single_value("Global Defaults", "disable_rounded_total")
			),
			"company": settings.company,
			"currency": settings.currency,
			# what ERPNext's company is set up with: its accounts' currency and its country
			"company_currency": frappe.get_cached_value("Company", settings.company, "default_currency")
			if settings.company
			else None,
			"company_country": frappe.get_cached_value("Company", settings.company, "country")
			if settings.company
			else None,
			"active_theme": settings.active_theme,
			"gateway_accounts": frappe.get_all(
				"Payment Gateway Account", fields=["name", "payment_gateway", "currency"]
			),
			"fulfillment_locations": [
				{
					**{field: row.get(field) for field in LOCATION_FIELDS},
					"warning": settings.ship_from_warning(row),
				}
				for row in settings.fulfillment_locations
			],
			"addresses": company_addresses(settings.company),
			"payment_gateways": [
				{field: row.get(field) for field in GATEWAY_FIELDS} for row in settings.payment_gateways
			],
			"shipping_surcharges": shipping_surcharges(),
			"import_duties": [
				{field: row.get(field) for field in DUTY_FIELDS} for row in settings.import_duties
			],
			"countries": frappe.get_all("Country", pluck="name", order_by="name"),
			"item_groups": frappe.get_all("Item Group", pluck="name", order_by="lft"),
			**shipping_restrictions(),
			"tax_templates": frappe.get_all("Sales Taxes and Charges Template", pluck="name"),
			"income_accounts": frappe.get_all(
				"Account",
				filters={"company": settings.company, "is_group": 0, "root_type": "Income"},
				pluck="name",
			),
			"price_lists": frappe.get_all("Price List", filters={"selling": 1}, pluck="name"),
			"uoms": frappe.get_all("UOM", filters={"enabled": 1}, pluck="name", order_by="name"),
			"service_items": [
				{"label": item.item_name or item.name, "value": item.name, "description": item.name}
				for item in frappe.get_all(
					"Item",
					filters={"is_stock_item": 0, "is_sales_item": 1, "disabled": 0, "has_variants": 0},
					fields=["name", "item_name"],
					order_by="item_name",
				)
			],
			"terms_records": frappe.get_all(
				"Terms and Conditions", filters={"selling": 1, "disabled": 0}, pluck="name"
			),
			"customer_groups": frappe.get_all("Customer Group", filters={"is_group": 0}, pluck="name"),
			"bank_accounts": [
				{field: row.get(field) for field in BANK_ACCOUNT_FIELDS} for row in settings.bank_accounts
			],
			"company_bank_accounts": company_bank_accounts(settings.company),
			"expense_accounts": frappe.get_all(
				"Account",
				filters={"company": settings.company, "is_group": 0, "root_type": "Expense"},
				pluck="name",
			),
			"fulfillment_providers": fulfillment_providers(),
			"delivery_services": delivery_names(("label", "carrier", "service")),
			"order_series": [
				series
				for series in (frappe.get_meta("Sales Order").get_field("naming_series").options or "").split(
					"\n"
				)
				if series
			],
			"site_pages": site_pages(),
			"address_lookup": address_lookup.status(),
			"warehouses": [
				{"value": row.name, "label": row.warehouse_name or row.name}
				for row in frappe.get_all(
					"Warehouse",
					filters={"company": settings.company, "is_group": 0},
					fields=["name", "warehouse_name"],
				)
			],
		}
	)
	return payload


def company_addresses(company: str | None) -> list[dict]:
	"""Addresses parcels can be sent from: the company's and its warehouses'."""
	if not company:
		return []
	from shop.storefront.stock import warehouse_address

	names = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
		pluck="parent",
	)
	for warehouse in frappe.get_all("Warehouse", filters={"company": company, "is_group": 0}, pluck="name"):
		address = warehouse_address(warehouse)
		if address:
			names.append(address)
	return [
		{"value": row.name, "label": f"{row.address_title or row.name}, {row.city or ''}".strip(", ")}
		for row in frappe.get_all(
			"Address",
			filters={"name": ["in", list(dict.fromkeys(names)) or [""]], "disabled": 0},
			fields=["name", "address_title", "city"],
		)
	]


def company_bank_accounts(company: str) -> list[dict]:
	"""The company's ERPNext Bank Accounts, with the currency customers would pay in and whether
	their Bank has a SWIFT code for international transfers."""
	accounts = []
	for row in frappe.get_all(
		"Bank Account",
		filters={"company": company, "is_company_account": 1, "disabled": 0},
		fields=["name", "account", "bank"],
	):
		accounts.append(
			{
				"name": row.name,
				"currency": frappe.get_cached_value("Account", row.account, "account_currency")
				if row.account
				else None,
				"swift": bool(row.bank and frappe.get_cached_value("Bank", row.bank, "swift_number")),
			}
		)
	return accounts


def delivery_names(keys: tuple[str, ...]) -> list[str]:
	"""Names of the deliveries the store has offered and sent (a shipping option's label, carrier
	and service), from recent orders and shipments."""
	names = []
	for value in frappe.get_all(
		"Sales Order",
		filters={"shop_shipping_option": ["like", "{%"]},
		pluck="shop_shipping_option",
		order_by="creation desc",
		limit=500,
	):
		option = frappe.parse_json(value) or {}
		names += [option.get(key) for key in keys]
	if "carrier" in keys:
		names += frappe.get_all(
			"Shop Fulfillment", filters={"carrier": ["is", "set"]}, pluck="carrier", limit=500
		)
		names += frappe.get_all("Shipment", filters={"carrier": ["is", "set"]}, pluck="carrier", limit=500)
	if "service" in keys:
		names += frappe.get_all(
			"Shipment", filters={"carrier_service": ["is", "set"]}, pluck="carrier_service", limit=500
		)
	return sorted({str(name).strip() for name in names if name and str(name).strip()}, key=str.lower)


def site_pages() -> list[dict]:
	"""The site's published pages, to link to."""
	pages = frappe.get_all(
		"Builder Page",
		filters={"published": 1, "is_template": 0, "dynamic_route": 0},
		fields=["name", "page_title as title", "route"],
	)
	store_pages = {row.page for row in frappe.get_cached_doc("Shop Settings").theme_pages}
	pages = [page for page in pages if page.name not in store_pages]
	pages += frappe.get_all("Web Page", filters={"published": 1}, fields=["title", "route"])
	return sorted(
		(
			{
				"label": page.title or page.route,
				"value": "/" + page.route.strip("/"),
				"description": "/" + page.route.strip("/"),
			}
			for page in pages
			if page.route
		),
		key=lambda page: page["label"].lower(),
	)


def fulfillment_providers() -> list[dict]:
	from shop.fulfillment.provider import available

	return available(for_locations=True)


@frappe.whitelist(methods=["POST"])
def save_settings(payload: dict) -> dict:
	only_managers()
	settings = frappe.get_doc("Shop Settings")
	for field in EDITABLE:
		if field not in payload:
			continue
		value = payload[field]
		if field in CHECKS:
			value = 1 if value else 0
		elif field in AMOUNTS:
			value = flt(value)
		elif field in COUNTS:
			value = cint(value)
		settings.set(field, value)
	if "fulfillment_locations" in payload:
		settings.set(
			"fulfillment_locations",
			[
				{field: row.get(field) for field in LOCATION_FIELDS}
				for row in payload["fulfillment_locations"] or []
				if row.get("warehouse")
			],
		)
	if "payment_gateways" in payload:
		settings.set(
			"payment_gateways",
			[
				{field: row.get(field) for field in GATEWAY_FIELDS}
				for row in payload["payment_gateways"] or []
				if row.get("payment_gateway")
			],
		)
	if "import_duties" in payload:
		settings.set(
			"import_duties",
			[
				{field: row.get(field) for field in DUTY_FIELDS}
				for row in payload["import_duties"] or []
				if row.get("country")
			],
		)
	if "bank_accounts" in payload:
		settings.set(
			"bank_accounts",
			[
				{field: row.get(field) for field in BANK_ACCOUNT_FIELDS}
				for row in payload["bank_accounts"] or []
				if row.get("bank_account")
			],
		)
	settings.save(ignore_permissions=True)
	save_erpnext_settings(payload)
	return get_settings()


def save_erpnext_settings(payload: dict) -> None:
	"""ERPNext's own settings the store shows. They apply to every company and document, so only a
	System Manager can change them here."""
	changes = []
	if "new_customer_group" in payload:
		selling = frappe.get_single("Selling Settings")
		if selling.customer_group != payload["new_customer_group"]:
			selling.customer_group = payload["new_customer_group"]
			changes.append(selling)
	if "round_order_totals" in payload:
		defaults = frappe.get_single("Global Defaults")
		disabled = 0 if payload["round_order_totals"] else 1
		if cint(defaults.disable_rounded_total) != disabled:
			defaults.disable_rounded_total = disabled
			changes.append(defaults)
	if changes and "System Manager" not in frappe.get_roles():
		frappe.throw(
			_("Only a System Manager can change ERPNext's {0}").format(
				", ".join(_(doc.doctype) for doc in changes)
			),
			frappe.PermissionError,
		)
	for doc in changes:
		doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def create_service_item(item_name: str) -> str:
	"""A service Item (not stocked) for a charge the store adds to orders, such as a fee or shipping."""
	from shop.api.products import unique_item_code
	from shop.setup_store import service_item_group

	only_managers()
	group = service_item_group()
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": unique_item_code(item_name),
			"item_name": item_name,
			"item_group": group,
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"description": item_name,
		}
	).insert(ignore_permissions=True)
	return item.name
