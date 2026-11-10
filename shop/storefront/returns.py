import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, get_datetime, now_datetime

from shop.storefront import orders as orders_module

OPEN_STATUSES = ("Requested", "Approved")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def create_request(
	order: str,
	item_code: str,
	request_type: str,
	reason: str,
	qty: float = 1,
	token: str | None = None,
) -> dict:
	if not orders_module.can_view(order, token):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if request_type not in ("Return", "Replacement"):
		frappe.throw(_("Choose return or replacement"))
	reason = frappe.utils.strip_html(reason or "").strip()
	if not reason:
		frappe.throw(_("Please tell us what went wrong"))
	doc = frappe.get_doc("Sales Order", order)
	validate_item(doc, item_code, qty)
	validate_window(doc)
	if frappe.db.exists(
		"Shop Return Request",
		{"sales_order": order, "item_code": item_code, "status": ["in", OPEN_STATUSES]},
	):
		frappe.throw(_("There is already an open request for this item"))
	request = frappe.get_doc(
		{
			"doctype": "Shop Return Request",
			"sales_order": order,
			"item_code": item_code,
			"request_type": request_type,
			"qty": flt(qty),
			"reason": reason.strip(),
		}
	).insert(ignore_permissions=True)
	notify(request, "return_requested", doc.contact_email)
	from shop.storefront.accounts import staff_emails

	notify(request, "return_staff", staff_emails(), reason=request.reason)
	return {"name": request.name, "status": request.status}


def validate_item(order, item_code: str, qty: float):
	from shop.storefront.totals import is_charge_item

	rows = [item for item in order.items if item.item_code == item_code]
	if not rows or is_charge_item(item_code):
		# shipping and fees aren't sent back
		frappe.throw(_("That item is not part of this order"))
	ordered = sum(flt(item.qty) for item in rows)
	if flt(qty) <= 0:
		frappe.throw(_("Choose how many to send back"))
	returned = sum(
		flt(done)
		for done in frappe.get_all(
			"Shop Return Request",
			filters={"sales_order": order.name, "item_code": item_code, "status": "Completed"},
			pluck="qty",
		)
	)
	if flt(qty) > ordered - returned:
		if returned:
			frappe.throw(
				_("You ordered {0} of this item and {1} came back already").format(
					f"{ordered:g}", f"{returned:g}"
				)
			)
		frappe.throw(_("You ordered only {0} of this item").format(f"{ordered:g}"))


def window_days() -> int:
	"""The store's return window (Shop Settings); 0 when customers can't ask online."""
	return cint(frappe.get_cached_doc("Shop Settings").get("return_window_days"))


def returns_note() -> str | None:
	days = window_days()
	return _("{0}-day returns").format(days) if days else None


def validate_window(order):
	days = window_days()
	if not days:
		frappe.throw(_("Please contact us about returns"))
	shipped_on = shipped_date(order.name)
	if not shipped_on:
		frappe.throw(_("Returns open once the order has shipped"))
	if now_datetime() > get_datetime(add_days(shipped_on, days)):
		frappe.throw(_("The {0}-day return window for this order has closed").format(days))


def shipped_date(order_name: str):
	"""When the order left: the courier's pickup for an order sent through a fulfilment provider,
	else its first Delivery Note."""
	if orders_module.is_cancelled(frappe.get_doc("Sales Order", order_name)):
		return None
	if frappe.db.exists("Shop Fulfillment", {"sales_order": order_name}):
		# sent through a fulfilment provider: only a shipment the courier has counts
		shipment = orders_module.shipment_summary(order_name)
		# the window runs from the last parcel to leave
		return get_datetime(shipment["last_shipped_on"]) if shipment and shipment.get("last_shipped_on") else None
	delivered = frappe.db.get_value(
		"Delivery Note Item",
		{"against_sales_order": order_name, "docstatus": 1},
		"creation",
		order_by="creation asc",
	)
	return get_datetime(delivered) if delivered else None


def summary(order_name: str) -> dict:
	"""What the confirmation page needs: open/closed requests and whether new ones are allowed."""
	requests = frappe.get_all(
		"Shop Return Request",
		filters={"sales_order": order_name},
		fields=["name", "item_name", "request_type", "status", "resolution_note"],
		order_by="creation desc",
	)
	for request in requests:
		request.line = f"{_(request.request_type)} · {request.item_name}"
	shipped_on = shipped_date(order_name)
	days = window_days()
	eligible = bool(days and shipped_on and now_datetime() <= get_datetime(add_days(shipped_on, days)))
	return {
		"requests": requests,
		"eligible": "true" if eligible else None,
		"has_requests": "true" if requests else None,
		"show": "true" if requests or eligible else None,
		"window_days": days,
		"window_note": _("Need to return or replace something? You have {0} days from shipping.").format(
			days
		),
	}


def notify(request, key: str, recipients, attachments=None, **context) -> None:
	from shop.storefront import emails

	order = frappe.get_doc("Sales Order", request.sales_order)
	emails.send(
		key,
		recipients,
		order,
		attachments=attachments,
		request_type=request.request_type,
		item_name=request.item_name,
		qty=frappe.utils.cint(request.qty) if flt(request.qty) == int(flt(request.qty)) else request.qty,
		note=request.resolution_note,
		**context,
	)


def status_changed(request) -> None:
	"""Tell the customer; a completed return puts the stock back, credits the invoice and refunds."""
	order_email = frappe.db.get_value("Sales Order", request.sales_order, "contact_email")
	if request.status == "Approved":
		notify(request, "return_approved", order_email)
	elif request.status == "Rejected":
		notify(request, "return_rejected", order_email)
	elif request.status == "Completed":
		if request.request_type == "Return":
			# credited first: a paid order not invoiced yet is invoiced while its goods count as delivered
			credit(request)
			return_stock(request)
		amount = (
			frappe.utils.fmt_money(
				abs(flt(frappe.db.get_value("Sales Invoice", request.credit_note, "grand_total"))),
				currency=frappe.db.get_value("Sales Invoice", request.credit_note, "currency"),
			)
			if request.credit_note
			else ""
		)
		from shop.storefront.payment import invoice_attachments, refunds_due

		notify(
			request,
			"return_completed",
			order_email,
			attachments=invoice_attachments(request.credit_note) if request.credit_note else None,
			credit_note=request.credit_note,
			amount=amount,
			refund_due=bool(request.credit_note and refunds_due(request.sales_order)),
		)


def return_lines(doc, request, qty: float | None = None, source_row: str | None = None) -> None:
	"""Keep only the returned item on a return made from a Delivery Note or invoice, for the quantity
	returned, spread over the rows it is on (or only the source row named)."""
	rows = [
		row
		for row in doc.items
		if row.item_code == request.item_code and (not source_row or row.get("dn_detail") == source_row)
	]
	if not rows:
		frappe.throw(_("{0} is not on {1}").format(request.item_name, doc.return_against))
	remaining = flt(qty if qty is not None else request.qty)
	kept = []
	for row in rows:
		take = min(remaining, abs(flt(row.qty)))
		if take <= 0:
			continue
		row.qty = -take
		remaining -= take
		kept.append(row)
	doc.items = kept
	if doc.doctype != "Sales Invoice":
		return
	# ERPNext's return copies the whole order's discount and charges: a returned item takes back
	# only its share of the discount, and shipping and other fixed charges aren't refunded
	original = frappe.get_doc("Sales Invoice", doc.return_against)
	if original.additional_discount_percentage:
		doc.discount_amount = 0
	elif flt(original.discount_amount) and flt(original.total):
		share = sum(abs(flt(row.qty) * flt(row.rate)) for row in kept) / flt(original.total)
		doc.discount_amount = -flt(abs(flt(original.discount_amount)) * share, doc.precision("discount_amount"))
	doc.taxes = [tax for tax in doc.taxes if tax.charge_type != "Actual"]


def return_stock(request) -> None:
	"""ERPNext's return Delivery Note for the item, so the stock is back."""
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

	if request.return_delivery_note:
		return
	# the item may have gone out on more than one Delivery Note: each gives back what it can
	remaining, made = flt(request.qty), []
	for line in frappe.get_all(
		"Delivery Note Item",
		filters={
			"against_sales_order": request.sales_order,
			"item_code": request.item_code,
			"docstatus": 1,
			"qty": [">", 0],
		},
		fields=["name", "parent", "qty", "returned_qty"],
		order_by="creation desc",
	):
		take = min(remaining, flt(line.qty) - flt(line.returned_qty))
		if take <= 0:
			continue
		returned = make_sales_return(line.parent)
		return_lines(returned, request, take, source_row=line.name)
		returned.flags.ignore_permissions = True
		returned.insert(ignore_permissions=True)
		returned.submit()
		made.append(returned.name)
		remaining -= take
		if remaining <= 0:
			break
	if made:
		request.db_set("return_delivery_note", ", ".join(made)[:140])


def credit(request) -> None:
	"""ERPNext's credit note (a return Sales Invoice) for the item."""
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

	from shop.storefront.payment import (
		invoice_paid_order,
		order_invoice,
		payment_status,
		settle_against_invoice,
	)

	if request.credit_note:
		return
	invoice = order_invoice(request.sales_order)
	if not invoice:
		order = frappe.get_doc("Sales Order", request.sales_order)
		# what the customer paid is credited against an invoice, as a cancelled paid order is
		if payment_status(order) != "Paid":
			return
		invoice = invoice_paid_order(order)
		if not invoice:
			return
	note = make_sales_return(invoice)
	return_lines(note, request)
	settle_against_invoice(note, invoice)
	note.flags.ignore_permissions = True
	note.insert(ignore_permissions=True)
	note.submit()
	request.db_set("credit_note", note.name)
