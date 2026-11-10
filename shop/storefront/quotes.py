"""Quotes: a shopper requests one from checkout, staff send the submitted Quotation from the desk,
and the customer accepts it online, which places and pays the order."""

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, getdate, nowdate

from shop.routes import store_url, token_matches
from shop.storefront import cart as cart_module
from shop.storefront import pricing, totals


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 10)
def request_quote(
	customer: dict, address: dict, shipping_option: str | None = None, message: str | None = None
) -> dict:
	from shop.storefront.accounts import staff_emails
	from shop.storefront.checkout import create_address, elevated, get_or_create_customer, plain_text

	customer, address = plain_text(customer), plain_text(address)
	message = frappe.utils.strip_html(message or "")
	if not frappe.get_cached_doc("Shop Settings").get("allow_quote_requests"):
		frappe.throw(_("This store doesn't take quote requests"))
	cart = cart_module.resolve_cart()
	if not cart or not cart.items:
		frappe.throw(_("Your cart is empty"))
	frappe.utils.validate_email_address(customer.get("email"), throw=True)
	if not customer.get("full_name"):
		frappe.throw(_("Name is required"))
	with elevated():
		order_quote = totals.compute(cart, address, shipping_option)
		party = get_or_create_customer(customer)
		shipping_address = create_address(party, customer, order_quote.address or address)
		quotation = quotation_from(
			order_quote.order, party, shipping_address.name, customer["email"].strip().lower()
		)
		quotation.shop_access_token = frappe.generate_hash(length=32)
		quotation.shop_request_message = (message or "").strip()[:2000]
		from shop.storefront import terms

		terms.apply_to(quotation)
		if order_quote.shipping:
			from shop.storefront.checkout import shipping_choice_json

			quotation.shop_shipping_option = shipping_choice_json(order_quote)
		quotation.flags.ignore_permissions = True
		quotation.insert(ignore_permissions=True)
		from shop.storefront import emails

		emails.send("quote_request_received", customer["email"], quotation)
		emails.send(
			"quote_request_staff",
			staff_emails(),
			quotation,
			customer_name=customer["full_name"],
			email=customer["email"],
			message=message or "",
			desk_url=frappe.utils.get_url("/desk/quotation/" + quotation.name),
		)
	return {"quote": quotation.name, "message": _("Thanks. We'll email your quote.")}


ITEM_FIELDS = (
	"item_code",
	"item_name",
	"description",
	"qty",
	"uom",
	"conversion_factor",
	"price_list_rate",
	"discount_percentage",
	"discount_amount",
	"margin_type",
	"margin_rate_or_amount",
	"rate",
	"item_tax_template",
	"pricing_rules",
	"warehouse",
)
TAX_FIELDS = (
	"charge_type",
	"row_id",
	"account_head",
	"description",
	"rate",
	"tax_amount",
	"included_in_print_rate",
	"cost_center",
)


def quotation_from(order, party: str, address: str, email: str):
	"""A draft Quotation with the lines, prices and taxes of the order the shopper was shown."""
	quotation = frappe.new_doc("Quotation")
	quotation.update(
		{
			"quotation_to": "Customer",
			"party_name": party,
			"company": order.company,
			"transaction_date": nowdate(),
			"valid_till": add_days(
				nowdate(), cint(frappe.get_cached_doc("Shop Settings").get("quote_valid_days")) or 30
			),
			"order_type": "Sales",
			"currency": order.currency,
			"conversion_rate": order.conversion_rate,
			"selling_price_list": order.selling_price_list,
			"price_list_currency": order.price_list_currency,
			"plc_conversion_rate": order.plc_conversion_rate,
			"customer_address": address,
			"shipping_address_name": address,
			"contact_email": email,
			"taxes_and_charges": order.taxes_and_charges,
			"apply_discount_on": order.apply_discount_on,
			"discount_amount": order.discount_amount,
			# ERPNext applies the coupon's Pricing Rule again and counts its use once the order is made
			"coupon_code": order.get("coupon_code"),
		}
	)
	source = None
	for item in order.items:
		if source and is_split_row(source, item):
			# a line the order sends from several warehouses is one line on the quote
			quotation.items[-1].qty = flt(quotation.items[-1].qty) + flt(item.qty)
			continue
		quotation.append("items", {field: item.get(field) for field in ITEM_FIELDS})
		source = item
	for tax in order.taxes:
		quotation.append("taxes", {field: tax.get(field) for field in TAX_FIELDS})
	return quotation


def is_split_row(row, item) -> bool:
	"""Whether item is more of row's line, sent from another warehouse."""
	return (
		item.item_code == row.item_code
		and not item.get("is_free_item")
		and not row.get("is_free_item")
		and flt(item.rate) == flt(row.rate)
	)


def quote_url(name: str, token: str) -> str:
	return frappe.utils.get_url(store_url(f"quote/{name}?token={token}"))


@frappe.whitelist(methods=["POST"])
def send_quote(name: str) -> str:
	"""Email the customer a link to view and accept a submitted quotation."""
	quotation = frappe.get_doc("Quotation", name)
	quotation.check_permission("email")
	if quotation.docstatus != 1:
		frappe.throw(_("Submit the quotation first"))
	email = quotation.contact_email
	if not email:
		frappe.throw(_("The quotation has no contact email"))
	if not quotation.get("shop_access_token"):
		quotation.db_set("shop_access_token", frappe.generate_hash(length=32))
	from shop.storefront import emails

	link = quote_url(quotation.name, quotation.shop_access_token)
	emails.send(
		"quote_ready",
		email,
		quotation,
		quote_url=link,
		valid_till=frappe.utils.formatdate(quotation.valid_till),
	)
	quotation.add_comment("Info", _("Quote emailed to {0}.").format(email))
	return link


def load_quote(name: str, token: str | None):
	if not name:
		raise frappe.PermissionError
	quotation = frappe.get_doc("Quotation", name)
	from shop.storefront.orders import session_customers

	if token_matches(quotation.get("shop_access_token"), token):
		return quotation
	if quotation.party_name in session_customers():
		return quotation
	raise frappe.PermissionError


def quote_summary(name: str, token: str | None) -> dict:
	from shop.storefront.checkout import elevated

	with elevated():
		quotation = load_quote(name, token)
		order = frappe.db.get_value(
			"Sales Order Item", {"prevdoc_docname": quotation.name, "docstatus": 1}, "parent"
		)
		expired = bool(quotation.valid_till and getdate(quotation.valid_till) < getdate(nowdate()))
		closed = quotation.status in ("Lost", "Cancelled") or quotation.docstatus == 2
		can_accept = (
			quotation.docstatus == 1
			and not closed
			and quotation.status != "Ordered"
			and not expired
			and not order
		)
		# the fee for each way to pay is worked out on the order the quote would make
		methods = quote_payment_methods(quotation) if can_accept else []
	html = lines_html(quotation)
	return {
		"name": quotation.name,
		# only a token that opened the quote is put back into the page
		"token": token if token_matches(quotation.get("shop_access_token"), token) else "",
		"status": quote_status(quotation, order, expired, closed),
		"valid_till": _("Valid until {0}").format(frappe.utils.formatdate(quotation.valid_till))
		if quotation.valid_till
		else "",
		"lines_html": html,
		"can_accept": "true" if can_accept else None,
		"payment_methods": methods,
		"order_url": store_url(
			f"order-confirmation/{order}?token={frappe.db.get_value('Sales Order', order, 'shop_access_token') or ''}"
		)
		if order
		else None,
	}


def quote_status(quotation, order: str | None, expired: bool, closed: bool) -> str:
	if order:
		return _("Ordered")
	if closed:
		return _("Closed")
	if expired:
		return _("Expired")
	if quotation.docstatus == 0:
		return _("Being prepared")
	return _("Ready to accept")


def lines_html(doc) -> str:
	"""A quotation's or order's lines and totals as HTML."""
	esc = frappe.utils.escape_html

	def fmt(amount):
		return frappe.utils.fmt_money(amount, currency=doc.currency)

	lines, notes, factor = totals.shown_lines(doc)
	rows = "".join(
		f'<div class="order-item"><span>{esc(row.item_name)}</span>'
		f'<span class="order-qty">{cart_module.display_qty(row.qty)}</span><span class="order-amount">{esc(fmt(flt(row.amount) * factor(row)))}</span></div>'
		for row in doc.items
		if not totals.is_charge_item(row.item_code)
	)
	rows += "".join(
		f'<div class="order-line"><span>{esc(line["label"])}</span><span>{esc(fmt(line["amount"]))}</span></div>'
		for line in lines[1:]
	)
	rows += (
		f'<div class="order-line total"><span>{esc(_("Total"))}</span>'
		f"<span>{esc(fmt(totals.order_total(doc)))} {esc(doc.currency)}</span></div>"
	)
	return rows + "".join(f'<p class="order-note">{esc(note)}</p>' for note in notes)


def quote_payment_methods(quotation) -> list[dict]:
	"""How the quote's customer can pay for it: online, by bank transfer to an account in the
	quote's currency, or on account when the signed-in shopper is that customer and may."""
	from shop.storefront.orders import session_customers

	methods = []
	for method in totals.payment_methods(is_export(quotation), swift=True):
		if method["method"] in totals.BANK_METHODS and not totals.bank_account(
			quotation.currency, method["method"]
		):
			continue
		gateway = totals.gateway_row(method["method"]) if totals.is_gateway(method["method"]) else None
		if gateway:
			account = totals.gateway_account(gateway.payment_gateway, quotation.currency)
			if not account or account.currency != quotation.currency:
				# online payments are taken, and recorded, in the gateway account's currency
				continue
		if gateway or method["method"] in totals.BANK_METHODS:
			fee = payment_fee(quotation, method["method"])
			amount = totals.money(fee, quotation.currency)
			note = (
				_("{0} {1} added").format(totals.fee_label(gateway), amount)
				if gateway
				else _("Bank fees {0} added").format(amount)
			)
			methods.append(dict(method, fee_note=note if fee else ""))
	if quotation.party_name in session_customers():
		terms = totals.on_account_terms(quotation.party_name)
		if terms:
			methods.insert(
				0, {"method": totals.ACCOUNT, "label": _("Pay on account (invoice)"), "fee_note": terms}
			)
	return methods


def payment_fee(quotation, method: str) -> float:
	"""What paying the quote this way adds to it: the card fee, or the bank's fees."""
	order = make_order(quotation)
	add_payment_fee(order, quotation, method)
	totals.calculate(order)
	return flt(flt(order.grand_total) - flt(quotation.grand_total), quotation.precision("grand_total"))


def add_payment_fee(order, quotation, method: str) -> None:
	"""The fees checkout adds for the payment method: the gateway's, or the bank account's
	conversion and transfer fees."""
	if totals.is_gateway(method):
		totals.add_card_fee(order, is_export(quotation), totals.gateway_row(method))
	elif method in totals.BANK_METHODS:
		account = totals.bank_account(quotation.currency, method)
		if quotation.currency != order.company_currency:
			totals.add_conversion_fee(order, account)
		totals.add_transfer_fee(order, account, method)


def is_export(quotation) -> bool:
	country = (
		frappe.db.get_value("Address", quotation.shipping_address_name, "country")
		if quotation.shipping_address_name
		else None
	)
	return bool(country and country != totals.company_country())


def tell_staff_prices_changed(quotation: str, order_total: float) -> None:
	"""A customer couldn't accept a quote because its order would now cost something else: staff
	are told once, on the quotation and by email, to send a new quote."""
	from shop.storefront import emails
	from shop.storefront.accounts import staff_emails

	doc = frappe.get_doc("Quotation", quotation)
	note = _(
		"The customer tried to accept this quote, but its order would now cost {0} instead of {1}: prices or pricing rules changed after it was sent. Send them a new quote."
	).format(
		frappe.utils.fmt_money(order_total, currency=doc.currency),
		frappe.utils.fmt_money(totals.order_total(doc), currency=doc.currency),
	)
	from shop.storefront.payment import has_note

	if has_note(doc, note):
		return
	doc.add_comment("Info", note)
	emails.send(
		"quote_changed_staff",
		staff_emails(),
		doc,
		note=note,
		desk_url=frappe.utils.get_url("/desk/quotation/" + quotation),
	)


def quoted_shipping(quotation):
	"""The shipping the quote was made with: one service, or one per parcel."""
	chosen = json.loads(quotation.shop_shipping_option)
	return [frappe._dict(row) for row in chosen] if isinstance(chosen, list) else frappe._dict(chosen)


def reassign_short_lines(order) -> None:
	"""A line whose quoted warehouse no longer has it is sent from the first of the store's
	warehouses that does."""
	from shop.storefront.stock import is_stock_item, warehouse_stock, warehouses

	codes = [row.item_code for row in order.items if is_stock_item(row.item_code)]
	stock = warehouse_stock(codes, sellable=True)
	for row in order.items:
		if row.item_code not in stock or stock[row.item_code].get(row.warehouse, 0) >= flt(row.qty):
			continue
		better = next((name for name in warehouses() if stock[row.item_code].get(name, 0) >= flt(row.qty)), None)
		if better:
			row.warehouse = better


def make_order(quotation):
	from erpnext.selling.doctype.quotation.quotation import make_sales_order

	order = make_sales_order(quotation.name)
	order.shop_shipping_option = quotation.get("shop_shipping_option")
	order.delivery_date = add_days(nowdate(), cint(frappe.get_cached_doc("Shop Settings").delivery_days))
	for item in order.items:
		item.delivery_date = order.delivery_date
	return order


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60)
def accept_quote(
	name: str,
	token: str | None = None,
	payment_method: str | None = None,
	accept_terms: int = 0,
	business_buyer: int = 0,
) -> dict:
	"""The customer accepts the quote: the order is placed at the quoted prices, then paid."""
	from shop.storefront import terms
	from shop.storefront.checkout import (
		check_credit_limit,
		create_payment_request,
		elevated,
		send_confirmation_for,
		set_shop_details,
	)

	load_quote(name, token)
	if not payment_method:
		frappe.throw(_("Choose how to pay"))
	if terms.required() and not cint(accept_terms):
		frappe.throw(_("Please accept the terms and conditions"))
	payment_method = totals.resolve_method(payment_method)
	with elevated():
		frappe.db.get_value("Quotation", name, "name", for_update=True)
		quotation = load_quote(name, token)
		summary = quote_summary(name, token)
		if not summary["can_accept"]:
			frappe.throw(_("This quote can no longer be accepted. Please contact us."))
		if payment_method not in [m["method"] for m in summary["payment_methods"]]:
			frappe.throw(_("This payment method is not available"))
		# what was in stock when the quote was sent may have sold since; a quote may hold items the
		# store doesn't list online
		from shop.storefront.checkout import lock_stock, validate_quantities

		goods = [row for row in quotation.items if not totals.is_charge_item(row.item_code)]
		lock_stock([row.item_code for row in goods])
		validate_quantities([(row.item_code, flt(row.stock_qty) or flt(row.qty)) for row in goods])
		order = make_order(quotation)
		precision = quotation.precision("grand_total")
		if flt(totals.order_total(order), precision) != flt(totals.order_total(quotation), precision):
			# ERPNext prices the order as prices are today; it is never placed for other than quoted
			frappe.enqueue(
				"shop.storefront.quotes.tell_staff_prices_changed",
				quotation=quotation.name,
				order_total=totals.order_total(order),
				job_id=f"shop-quote-changed-{quotation.name}",
				deduplicate=True,
			)
			frappe.throw(
				_(
					"Our prices have changed since this quote was sent, so it can't be accepted as it is. "
					"We've let our team know and they'll send you an updated quote."
				)
			)
		order.contact_email = quotation.contact_email
		order.shop_access_token = frappe.generate_hash(length=32)
		quoted = quoted_shipping(quotation) if quotation.get("shop_shipping_option") else None
		order_quote = frappe._dict(
			payment_method=payment_method,
			shipping=quoted[0] if isinstance(quoted, list) else quoted,
			shippings=quoted if isinstance(quoted, list) else None,
		)
		reassign_short_lines(order)
		set_shop_details(order, order_quote, cint(accept_terms), cint(business_buyer))
		add_payment_fee(order, quotation, payment_method)
		order.flags.ignore_permissions = True
		order.insert(ignore_permissions=True)
		check_credit_limit(order)
		order.submit()
		response = {"sales_order": order.name}
		confirmation = store_url(f"order-confirmation/{order.name}?token={order.shop_access_token}")
		if totals.is_gateway(payment_method) and totals.order_total(order) > 0:
			response["redirect"] = create_payment_request(order, {"email": order.contact_email})
		else:
			response["redirect"] = confirmation
			send_confirmation_for(order, confirmation)
	return response
