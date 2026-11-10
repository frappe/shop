"""Records the store tests share: tax templates, service items, bank accounts, terms."""

import frappe


def service(name: str, company: str) -> str:
	if not frappe.db.exists("Item", name):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": name,
				"item_name": name,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
			}
		).insert(ignore_permissions=True)
	return name


def template(company: str, title: str, rate: float, included: int) -> str:
	name = frappe.db.exists("Sales Taxes and Charges Template", {"title": title, "company": company})
	if name:
		return name
	account = frappe.db.get_value("Account", {"company": company, "account_type": "Tax", "is_group": 0})
	doc = frappe.get_doc(
		{
			"doctype": "Sales Taxes and Charges Template",
			"title": title,
			"company": company,
			"taxes": [
				{
					"charge_type": "On Net Total",
					"account_head": account,
					"rate": rate,
					"description": f"VAT {rate:g}%",
					"included_in_print_rate": included,
				}
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def company_bank_account(company: str, currency: str) -> str:
	"""An ERPNext company Bank Account in a currency, with test details, as a store would set up."""
	name = f"_Test Shop {currency}"
	if frappe.db.exists("Bank Account", {"account_name": name, "company": company}):
		return frappe.db.get_value("Bank Account", {"account_name": name, "company": company})
	if not frappe.db.exists("Bank", "_Test Shop Bank"):
		frappe.get_doc(
			{"doctype": "Bank", "bank_name": "_Test Shop Bank", "swift_number": "TESTXX22"}
		).insert(ignore_permissions=True)
	parent = frappe.db.get_value(
		"Account", {"company": company, "account_type": "Bank", "is_group": 1}
	) or frappe.db.get_value("Account", {"company": company, "root_type": "Asset", "is_group": 1})
	account = frappe.db.get_value("Account", {"company": company, "account_name": name})
	if not account:
		account = (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": name,
					"company": company,
					"parent_account": parent,
					"account_type": "Bank",
					"account_currency": currency,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	return (
		frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": name,
				"bank": "_Test Shop Bank",
				"is_company_account": 1,
				"company": company,
				"account": account,
				"branch_code": "2",
				"bank_account_no": "3",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def gateway(company: str, name: str = "_Test Shop Gateway", currencies: tuple = ()) -> str:
	"""A Payment Gateway with a Payment Gateway Account in each currency (the company's by default),
	as a gateway app sets up."""
	if not frappe.db.exists("Payment Gateway", name):
		frappe.get_doc({"doctype": "Payment Gateway", "gateway": name}).insert(ignore_permissions=True)
	for currency in currencies or (frappe.get_cached_value("Company", company, "default_currency"),):
		if frappe.db.exists("Payment Gateway Account", {"payment_gateway": name, "currency": currency}):
			continue
		account = frappe.db.get_value("Bank Account", company_bank_account(company, currency), "account")
		frappe.get_doc(
			{
				"doctype": "Payment Gateway Account",
				"payment_gateway": name,
				"payment_account": account,
				"currency": currency,
			}
		).insert(ignore_permissions=True)
	return name


def terms_record() -> str:
	"""An ERPNext Terms and Conditions record for the store, using Jinja as ERPNext allows."""
	if not frappe.db.exists("Terms and Conditions", "_Test Store Terms"):
		frappe.get_doc(
			{
				"doctype": "Terms and Conditions",
				"title": "_Test Store Terms",
				"selling": 1,
				"terms": "<p>Terms for {{ customer_name }}</p>",
			}
		).insert(ignore_permissions=True)
	return "_Test Store Terms"


def sellable(item_code: str, qty: float, warehouse: str | None = None) -> None:
	"""At least this many of the item to sell (in this warehouse, else the store's first), whatever
	earlier tests' orders are waiting for."""
	from shop.storefront import stock

	warehouse = warehouse or stock.primary_warehouse()
	short = qty - max(stock.warehouse_stock([item_code], sellable=True)[item_code].get(warehouse, 0), 0)
	if short <= 0:
		return
	settings = frappe.get_cached_doc("Shop Settings")
	entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": settings.company,
			"items": [
				{
					"item_code": item_code,
					"qty": short,
					"t_warehouse": warehouse,
					"basic_rate": 1,
				}
			],
		}
	)
	entry.insert(ignore_permissions=True)
	entry.submit()


def second_warehouse(company: str) -> str:
	"""A second stock warehouse of the company, as a store with two locations has."""
	abbr = frappe.get_cached_value("Company", company, "abbr")
	name = f"_Test Shop Second - {abbr}"
	if not frappe.db.exists("Warehouse", name):
		parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name", order_by="lft")
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "_Test Shop Second",
				"company": company,
				"parent_warehouse": parent,
			}
		).insert(ignore_permissions=True)
	return name


def use_locations(test, *rows: dict) -> None:
	"""The store's fulfillment locations for one test, put back afterwards."""
	from shop.api.settings import LOCATION_FIELDS

	settings = frappe.get_doc("Shop Settings")
	original = [{f: row.get(f) for f in LOCATION_FIELDS} for row in settings.fulfillment_locations]

	def put(locations):
		doc = frappe.get_doc("Shop Settings")
		doc.fulfillment_locations = []
		for row in locations:
			doc.append("fulfillment_locations", row)
		doc.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Shop Settings")

	test.addCleanup(put, original)
	put(rows)


REQUEST_CACHES = (
	"shop_session_customer",
	"shop_customer_rates",
	"shop_item_tax_rates",
	"shop_display_rates",
	"shop_domestic_taxes",
	"shop_shopper",
	"shop_display_currencies",
	"shop_cart_token",
)


def fresh_request() -> None:
	"""A test starts as a new request: no request object, and none of what the store keeps for one."""
	if hasattr(frappe.local, "request"):
		del frappe.local.request
	for name in REQUEST_CACHES:
		if hasattr(frappe.local, name):
			delattr(frappe.local, name)
	# nor prices kept from earlier tests, which change prices without saving documents
	from shop.storefront.pricing import forget_rates

	forget_rates()
