import frappe
from frappe.utils import fmt_money


def get_prices(item_codes: list[str]) -> dict:
	if not item_codes:
		return {}
	settings = frappe.get_cached_doc("Shop Settings")
	rates = frappe.get_all(
		"Item Price",
		filters={"item_code": ["in", item_codes], "price_list": settings.price_list},
		fields=["item_code", "price_list_rate"],
	)
	return {
		row.item_code: {
			"rate": row.price_list_rate,
			"formatted": format_amount(row.price_list_rate),
		}
		for row in rates
	}


def get_price(item_code: str) -> dict | None:
	return get_prices([item_code]).get(item_code)


def format_amount(amount: float) -> str:
	settings = frappe.get_cached_doc("Shop Settings")
	return fmt_money(amount, currency=settings.currency)
