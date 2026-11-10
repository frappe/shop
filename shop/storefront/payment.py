"""How an order is paid: bank transfer instructions, payment status and overdue orders."""

import json
import re

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from shop.storefront import totals


def amount_due(order) -> float:
	"""What is still owed, in the order currency."""
	total = totals.order_total(order)
	paid = flt(order.advance_paid)
	if not paid:
		return total
	if order.get("advance_payment_status") == "Fully Paid":
		return 0.0
	# ERPNext keeps advance_paid in the customer's account currency
	if (order.get("party_account_currency") or order.currency) != order.currency:
		paid = paid / (flt(order.conversion_rate) or 1)
	return max(flt(total - paid, order.precision("grand_total")), 0.0)


def is_paid(order) -> bool:
	if amount_due(order) <= 0:
		return True
	# paid against its invoice instead of the order
	invoice = order_invoice(order.name)
	if invoice and flt(frappe.db.get_value("Sales Invoice", invoice, "outstanding_amount")) <= 0:
		return True
	# paid in full through Payment Requests (a part payment requested in Desk isn't the whole order)
	paid = frappe.get_all(
		"Payment Request",
		filters={
			"reference_doctype": "Sales Order",
			"reference_name": order.name,
			"status": "Paid",
			"docstatus": 1,
			"currency": order.currency,
		},
		pluck="grand_total",
	)
	return bool(paid) and sum(flt(amount) for amount in paid) >= totals.order_total(order) - 0.005


def payment_status(order) -> str:
	"""Paid, Part paid or Unpaid: from what ERPNext records on the order, and for an order paid on
	account, from its invoices. An invoice a credit note settled with nothing received is Credited."""
	if is_paid(order) or invoices_paid(order.name):
		return "Paid" if money_received(order) else "Credited"
	if flt(order.advance_paid) > 0:
		return "Part paid"
	return "Unpaid"


def money_received(order) -> bool:
	"""Whether any payment came in for the order or its invoices."""
	invoices = frappe.get_all(
		"Sales Invoice Item",
		filters={"sales_order": order.name, "docstatus": 1},
		pluck="parent",
		distinct=True,
	)
	names = [order.name, *invoices]
	return bool(
		frappe.db.exists(
			"Payment Entry Reference",
			{"reference_name": ["in", names], "docstatus": 1, "parenttype": "Payment Entry"},
		)
	)


def invoices_paid(order_name: str) -> bool:
	invoices = frappe.get_all(
		"Sales Invoice Item",
		filters={"sales_order": order_name, "docstatus": 1},
		pluck="parent",
		distinct=True,
	)
	if not invoices:
		return False
	return not frappe.get_all(
		"Sales Invoice",
		filters={"name": ["in", invoices], "is_return": 0, "outstanding_amount": [">", 0]},
		limit=1,
	)


def method(order) -> str | None:
	return order.get("shop_payment_method") or None


def bank_instructions(order) -> dict | None:
	"""What to pay, where, and with which reference, for a bank transfer order."""
	if method(order) not in totals.BANK_METHODS:
		return None
	account = totals.bank_account(order.currency, method(order))
	if not account:
		return None
	lines = account.details
	return {
		"currency": order.currency,
		"label": account.label or order.currency,
		"amount": totals.money(amount_due(order), order.currency),
		"reference": order.name,
		"details": lines,
		"due": frappe.utils.formatdate(order.get("shop_payment_due"))
		if order.get("shop_payment_due")
		else "",
		"due_note": due_note(order),
	}


def due_note(order) -> str:
	"""When to pay by, and what happens after, as the store's settings have it."""
	due = order.get("shop_payment_due")
	if not due:
		return ""
	if flt(order.advance_paid) > 0:
		if getdate(due) < getdate(nowdate()):
			return _("Please pay the rest as soon as you can.")
		return _("Please pay the rest by {0}.").format(frappe.utils.formatdate(due))
	note = _("Please pay by {0}.").format(frappe.utils.formatdate(due))
	if frappe.get_cached_doc("Shop Settings").get("cancel_unpaid_orders"):
		note += " " + _("Unpaid orders are cancelled after that date.")
	return note


def bank_instructions_html(order) -> str:
	info = bank_instructions(order)
	if not info:
		return ""
	esc = frappe.utils.escape_html
	details = "".join(f"<div>{esc(line)}</div>" for line in info["details"])
	due = f"<p>{esc(info['due_note'])}</p>" if info["due_note"] else ""
	return f"""
	<div style="border:1px solid #ddd;border-radius:6px;padding:14px;margin:16px 0">
		<p style="margin:0 0 8px;font-weight:bold">{esc(_("Pay by bank transfer"))}</p>
		<p style="margin:0 0 8px">{esc(_("Amount"))}: <b>{esc(info["amount"])}</b> ({esc(info["currency"])})<br>
		{esc(_("Reference"))}: <b>{esc(info["reference"])}</b></p>
		{details}
		{due}
		<p style="margin:8px 0 0">{esc(_("We'll send your order as soon as the payment arrives."))}</p>
	</div>
	"""


def on_payment_entry(doc, method=None) -> None:
	"""When a payment pays off a store order: invoice it, tell the customer once, hand it on."""
	for row in doc.references or []:
		if row.reference_doctype != "Sales Order" or not frappe.db.get_value(
			"Sales Order", row.reference_name, "shop_payment_method"
		):
			continue
		order = frappe.get_doc("Sales Order", row.reference_name)
		if order.docstatus != 1 or amount_due(order) > 0:
			continue
		if was_paid_before(order, row):
			continue
		order_paid(order)
		if order.shop_payment_method in totals.BANK_METHODS:
			order.add_comment("Info", _("Bank transfer received ({0}).").format(doc.name))
			notify_paid(order)
		elif doc.reference_no not in frappe.get_all(
			"Payment Request",
			{"reference_doctype": "Sales Order", "reference_name": order.name},
			pluck="name",
		):
			# an online order paid another way (recorded by staff), not through its Payment Request
			# (whose own confirmation goes out): the customer still hears
			notify_paid(order)


def on_bank_transaction(doc, method=None) -> None:
	"""A deposit into one of the company's bank accounts may pay a bank transfer order; it is matched
	once the Bank Transaction is saved."""
	if flt(doc.deposit) > 0:
		frappe.enqueue(
			"shop.storefront.payment.match_bank_transaction",
			bank_transaction=doc.name,
			enqueue_after_commit=True,
		)


def match_bank_transaction(bank_transaction: str) -> None:
	try:
		pay_from_bank_transaction(bank_transaction)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(
			title=_("Bank deposit not matched to an order"),
			reference_doctype="Bank Transaction",
			reference_name=bank_transaction,
		)


def pay_from_bank_transaction(bank_transaction: str) -> str | None:
	"""Pay the bank transfer order a deposit names in its reference: a Payment Entry for what the
	customer sent, with the bank's fee as a charge, reconciled with the Bank Transaction. A payment
	short of what is owed leaves the order waiting and tells the customer the balance."""
	from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import reconcile_vouchers

	from shop.storefront import emails
	from shop.storefront.checkout import elevated

	transaction = frappe.get_doc("Bank Transaction", bank_transaction)
	if transaction.docstatus != 1 or flt(transaction.unallocated_amount) <= 0:
		return None
	order = order_paid_by(transaction)
	if not order:
		note_deposit_for_closed_order(transaction)
		return None
	with elevated():
		payment_entry = make_payment_entry(order, transaction)
		reconcile_vouchers(
			transaction.name,
			json.dumps(
				[
					{
						"payment_doctype": "Payment Entry",
						"payment_name": payment_entry.name,
						"amount": flt(transaction.unallocated_amount),
					}
				]
			),
		)
		order.reload()
		owed = amount_due(order)
		if flt(payment_entry.unallocated_amount) > 0:
			order.add_comment(
				"Info",
				_("{0} more than owed arrived ({1}); it is unallocated on {2}.").format(
					money_text(
						flt(payment_entry.unallocated_amount), order.party_account_currency or order.currency
					),
					transaction.name,
					payment_entry.name,
				),
			)
		if owed > 0:
			received = money_text(flt(payment_entry.received_amount), order.currency)
			order.add_comment(
				"Info",
				_("Bank transfer of {0} received ({1}); {2} is still owed.").format(
					received, payment_entry.name, money_text(owed, order.currency)
				),
			)
			emails.send(
				"payment_short",
				order.contact_email,
				order,
				received=received,
				owed=money_text(owed, order.currency),
				payment_html=bank_instructions_html(order),
			)
	return payment_entry.name


def note_deposit_for_closed_order(transaction) -> None:
	"""A deposit naming a store order it can't pay (cancelled, closed, on hold, already paid, or in
	another currency) is left for staff, and said on the order, where the admin shows it, once."""
	text = compact(f"{transaction.reference_number or ''} {transaction.description or ''}")
	for name in frappe.get_all(
		"Sales Order",
		filters={
			"company": transaction.company,
			"shop_payment_method": ["in", list(totals.BANK_METHODS)],
			"docstatus": ["in", [1, 2]],
		},
		pluck="name",
	):
		if not mentions(name, text):
			continue
		order = frappe.get_doc("Sales Order", name)
		if order.docstatus == 2:
			state = _("cancelled")
		elif order.status in ("Closed", "On Hold"):
			state = _(order.status).lower()
		elif is_paid(order):
			state = _("already paid")
		elif order.currency != transaction.currency:
			state = _("in {0}").format(order.currency)
		else:
			continue
		note = _(
			"Bank deposit {0} of {1} names this order, which is {2}. Match, refund or record it."
		).format(
			transaction.name, money_text(flt(transaction.unallocated_amount), transaction.currency), state
		)
		note_once(order, note)
		return


def order_paid_by(transaction):
	"""The one unpaid bank transfer order, in the deposit's currency, whose number is in the
	deposit's reference or description."""
	# bank references drop or change spaces, dashes and case ("so 00058" pays SO-00058)
	text = compact(f"{transaction.reference_number or ''} {transaction.description or ''}")
	names = frappe.get_all(
		"Sales Order",
		filters={
			"docstatus": 1,
			"company": transaction.company,
			"currency": transaction.currency,
			"shop_payment_method": ["in", list(totals.BANK_METHODS)],
			"advance_payment_status": ["!=", "Fully Paid"],
			"status": ["not in", ["Closed", "Completed", "On Hold"]],
		},
		pluck="name",
	)
	matched = [name for name in names if mentions(name, text)]
	return frappe.get_doc("Sales Order", matched[0]) if len(matched) == 1 else None


def compact(text: str) -> str:
	return re.sub(r"[^A-Z0-9]", "", text.upper())


def mentions(name: str, text: str) -> bool:
	"""Whether compacted text quotes the order: its number isn't part of a longer one."""
	number = compact(name)
	before = r"(?<!\d)" if number[:1].isdigit() else ""
	return bool(re.search(rf"{before}{number}(?!\d)", text))


def make_payment_entry(order, transaction):
	"""ERPNext's Payment Entry for the order, for what the customer sent: the deposit plus the fee the
	bank took, which is booked to the store's Bank Charges Account."""
	account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
	charges_account = frappe.get_cached_doc("Shop Settings").get("bank_charges_account")
	fee = flt(transaction.included_fee) if charges_account else 0
	payment_entry, rate = payment_entry_for(order, account, flt(transaction.unallocated_amount) + fee)
	if fee:
		payment_entry.append(
			"taxes",
			{
				"charge_type": "Actual",
				"add_deduct_tax": "Deduct",
				"account_head": charges_account,
				"description": _("Bank fee"),
				"tax_amount": flt(fee * rate, payment_entry.precision("paid_amount")),
				"cost_center": frappe.get_cached_value("Company", order.company, "cost_center"),
			},
		)
	payment_entry.bank_account = transaction.bank_account
	payment_entry.reference_no = transaction.transaction_id or transaction.name
	# a transaction entered by hand may have no date
	payment_entry.reference_date = transaction.date or getdate(transaction.creation)
	payment_entry.insert()
	payment_entry.submit()
	return payment_entry


def payment_entry_for(order, account: str | None, received: float | None = None):
	"""ERPNext's Payment Entry for the order, for what was received into the bank account (all that
	is owed when not given), and the rate from the bank's currency to the customer's account. More
	than is owed stays unallocated, the customer's advance."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	payment_entry = get_payment_entry("Sales Order", order.name, bank_account=account, bank_amount=received)
	rate = flt(payment_entry.target_exchange_rate) / flt(payment_entry.source_exchange_rate)
	if received and flt(received, 2) != flt(amount_due(order), 2):
		owed = {row.reference_name: flt(row.outstanding_amount) for row in payment_entry.references}
		party_rate = rate
		if payment_entry.paid_to_account_currency == order.currency:
			# paid in the order's currency: it pays that much of the order, at the order's rate;
			# ERPNext books the change in rate since as exchange gain or loss
			party_rate = (
				1
				if payment_entry.paid_from_account_currency == order.currency
				else flt(order.conversion_rate)
			)
		payment_entry = get_payment_entry(
			"Sales Order",
			order.name,
			bank_account=account,
			bank_amount=received,
			party_amount=flt(received * party_rate, payment_entry.precision("paid_amount")),
		)
		for reference in payment_entry.references:
			reference.outstanding_amount = owed[reference.reference_name]
			reference.allocated_amount = min(flt(reference.allocated_amount), reference.outstanding_amount)
	return payment_entry, rate


def money_text(amount: float, currency: str) -> str:
	return f"{totals.money(amount, currency)} {currency}"


def was_paid_before(order, reference) -> bool:
	"""Whether the order was already paid in full before this payment."""
	paid, allocated = flt(order.advance_paid), flt(reference.allocated_amount)
	if (order.get("party_account_currency") or order.currency) != order.currency:
		paid, allocated = (
			paid / (flt(order.conversion_rate) or 1),
			allocated / (flt(order.conversion_rate) or 1),
		)
	return totals.order_total(order) - (paid - allocated) <= 0


def order_paid(order) -> None:
	"""A store order is paid: invoice it when the store invoices paid orders, and send it on."""
	from shop.fulfillment.service import auto_send

	if frappe.get_cached_doc("Shop Settings").get("invoice_paid_orders"):
		invoice_paid_order(order)
	auto_send(order.name)


def notify_paid(order) -> None:
	from shop.storefront import emails

	invoice = order_invoice(order.name)
	emails.send(
		"payment_received",
		order.contact_email,
		order,
		attachments=invoice_attachments(invoice),
		invoice=invoice,
		shipping_emails=frappe.get_cached_doc("Shop Settings").get("send_shipping_emails"),
	)


def order_invoice(order_name: str) -> str | None:
	"""The submitted Sales Invoice made from this order, if there is one (not a credit note)."""
	invoices = frappe.get_all(
		"Sales Invoice Item",
		filters={"sales_order": order_name, "docstatus": 1},
		pluck="parent",
		distinct=True,
	)
	if not invoices:
		return None
	return frappe.db.get_value("Sales Invoice", {"name": ["in", invoices], "is_return": 0}, "name")


def invoice_paid_order(order) -> str | None:
	"""Invoice a store order once it is paid in full, with the payment set against the invoice.

	ERPNext's own Sales Invoice is made from the Sales Order, and its Allocate Advances
	Automatically option takes the payment already recorded against the order. Orders paid on
	account are invoiced when they are placed. A failure is logged and never blocks the payment."""
	if order.get("shop_payment_method") not in (totals.GATEWAY, *totals.BANK_METHODS, totals.COD):
		return None
	existing = order_invoice(order.name)
	if existing or flt(order.per_billed) >= 100:
		return existing
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

	frappe.db.savepoint("shop_invoice")
	try:
		invoice = make_sales_invoice(order.name)
		# as in the desk: ERPNext allocates the order's payment itself, after working out the totals
		invoice.allocate_advances_automatically = 1
		invoice.only_include_allocated_payments = 1
		invoice.flags.ignore_permissions = True
		invoice.insert(ignore_permissions=True)
		if flt(totals.order_total(invoice), 2) != flt(totals.order_total(order), 2):
			# ERPNext priced the invoice differently (e.g. the customer's pricing changed since)
			frappe.throw(
				_("The invoice would be {0}, the order is {1}").format(
					totals.order_total(invoice), totals.order_total(order)
				)
			)
		invoice.submit()
	except Exception as error:
		frappe.db.rollback(save_point="shop_invoice")
		frappe.log_error(title=f"Could not invoice paid order {order.name}")
		frappe.clear_messages()
		order.add_comment(
			"Info",
			_(
				"The order is paid but could not be invoiced automatically ({0}). Make the invoice from the order."
			).format(frappe.utils.strip_html(str(error))),
		)
		return None
	order.add_comment("Info", _("Paid and invoiced: {0}.").format(invoice.name))
	return invoice.name


def invoice_pay_url(invoice: str | None) -> str | None:
	"""The link an app gives an unpaid invoice to pay it online (the payments app's invoice
	payment links), if any."""
	if not invoice or flt(frappe.db.get_value("Sales Invoice", invoice, "outstanding_amount")) <= 0:
		return None
	return getattr(frappe.get_doc("Sales Invoice", invoice), "payment_link", None)


def invoice_attachments(invoice: str | None) -> list:
	if not invoice:
		return []
	from shop.storefront.checkout import elevated

	try:
		# the invoice goes to its own customer, also from a payment confirmed while signed out
		with elevated():
			return [frappe.attach_print("Sales Invoice", invoice, file_name=invoice)]
	except Exception:
		# the email still goes out; the invoice is on the customer's account and order page
		frappe.log_error(title=f"Could not attach invoice {invoice}")
		return []


def cancel_overdue_orders() -> None:
	"""Daily: cancel store orders that were never paid by their due date, and tell the customer."""
	if not frappe.get_cached_doc("Shop Settings").get("cancel_unpaid_orders"):
		return
	if not frappe.get_meta("Sales Order").has_field("shop_payment_method"):
		return
	for name in frappe.get_all(
		"Sales Order",
		filters={
			"docstatus": 1,
			"shop_payment_method": ["in", [*totals.BANK_METHODS, totals.GATEWAY]],
			# an order without a pay-by date (Frappe would read it as long past) is never cancelled
			"shop_payment_due": ["is", "set"],
			"status": ["not in", ["Closed", "Completed", "On Hold"]],
		},
		pluck="name",
	):
		if getdate(frappe.db.get_value("Sales Order", name, "shop_payment_due")) >= getdate(nowdate()):
			continue
		try:
			cancel_if_unpaid(name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Could not cancel unpaid order {name}")


def cancel_if_unpaid(name: str) -> bool:
	order = frappe.get_doc("Sales Order", name)
	if order.docstatus != 1 or order.status in ("On Hold", "Closed", "Completed") or is_paid(order):
		return False
	if not order.get("shop_payment_due") or getdate(order.shop_payment_due) >= getdate(nowdate()):
		return False
	if flt(order.advance_paid) > 0:
		chase_part_paid(order)
		return False
	if flt(order.per_delivered) > 0 or flt(order.per_billed) > 0:
		return False
	if frappe.db.exists(
		"Shop Fulfillment", {"sales_order": order.name, "status": ["in", ("Pending", "Accepted", "Shipped")]}
	):
		# staff sent it before it was paid: they decide
		note_once(order, _("Not cancelled: it has been sent for fulfilment, though it isn't paid."))
		return False
	unmatched = unmatched_payments(order) + unmatched_deposits(order)
	if unmatched:
		# the customer may have paid without the payment being matched to the order; said once
		note = _(
			"Not cancelled: {0} has payments not matched to an order yet ({1}). Match them in ERPNext's Payment Reconciliation."
		).format(order.customer, ", ".join(unmatched))
		note_once(order, note)
		return False
	for request in frappe.get_all(
		"Payment Request",
		filters={
			"reference_doctype": "Sales Order",
			"reference_name": name,
			"docstatus": 1,
			"status": ["!=", "Paid"],
		},
		pluck="name",
	):
		frappe.get_doc("Payment Request", request).cancel()
	# cancelling a Payment Request updates the order
	order.reload()
	order.flags.ignore_permissions = True
	order.cancel()
	order.add_comment("Info", _("Cancelled automatically: not paid by {0}.").format(order.shop_payment_due))
	notify_cancelled(order)
	return True


def settle_against_invoice(credit_note, invoice: str) -> None:
	"""A credit note for an invoice still owed (an order on account) takes it off what is owed,
	instead of becoming money to pay back."""
	if flt(frappe.db.get_value("Sales Invoice", invoice, "outstanding_amount")) > 0:
		credit_note.update_outstanding_for_self = 0


def refunds_due(order_name: str) -> list[dict]:
	"""The order's credit notes still owed to the customer, and whether the card can be refunded."""
	invoice = order_invoice(order_name)
	if not invoice:
		return []
	notes = frappe.get_all(
		"Sales Invoice",
		filters={"return_against": invoice, "docstatus": 1, "outstanding_amount": ["<", 0]},
		fields=["name", "outstanding_amount", "currency"],
		order_by="creation asc",
	)
	# credited beyond what was still owed on it: the invoice itself has money to pay back
	if flt(frappe.db.get_value("Sales Invoice", invoice, "outstanding_amount")) < 0:
		currency = frappe.db.get_value("Sales Invoice", invoice, "currency")
		notes.insert(0, frappe._dict(name=invoice, currency=currency))
	found = online_refund_controller(order_name)
	gateway = paid_through(found[0]) if found else None
	return [
		{
			"credit_note": note.name,
			"amount": owed(note.name),
			"formatted_amount": money_text(owed(note.name), note.currency),
			"online": bool(found),
			"gateway": gateway,
		}
		for note in notes
	]


def paid_through(payment_request) -> str:
	"""What the store calls the gateway an order was paid through, e.g. "Card" or "PayPal"."""
	row = totals.gateway_row(payment_request.payment_gateway)
	return totals.gateway_label(row) if row else payment_request.payment_gateway


def online_refund_controller(order_name: str):
	"""The paid Payment Request of an order paid online, and its gateway's settings when they can refund."""
	request_name = frappe.db.get_value(
		"Payment Request",
		{"reference_doctype": "Sales Order", "reference_name": order_name, "status": "Paid", "docstatus": 1},
		"name",
	)
	if not request_name:
		return None
	payment_request = frappe.get_doc("Payment Request", request_name)
	controller = gateway_controller(payment_request.payment_gateway)
	return (payment_request, controller) if controller and hasattr(controller, "refund") else None


def gateway_controller(name: str):
	"""A Payment Gateway's settings: one of several records (Stripe), or a single settings
	DocType named after the gateway (PayPal)."""
	gateway = frappe.get_doc("Payment Gateway", name)
	if gateway.gateway_settings and gateway.gateway_controller:
		return frappe.get_doc(gateway.gateway_settings, gateway.gateway_controller)
	settings = gateway.gateway_settings or f"{name} Settings"
	return frappe.get_single(settings) if frappe.db.exists("DocType", settings) else None


def refund(order_name: str, credit_note: str, bank_account: str | None = None) -> str:
	"""Pay a credit note back, as staff approved: to the card through the gateway, or from a bank
	account. Records ERPNext's Payment Entry and tells the customer."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from shop.storefront import emails

	# a second request for the same refund waits here, then finds nothing left to refund
	frappe.db.get_value("Sales Invoice", credit_note, "name", for_update=True)
	due = next((row for row in refunds_due(order_name) if row["credit_note"] == credit_note), None)
	if not due:
		frappe.throw(_("Credit note {0} has nothing left to refund for this order").format(credit_note))
	gateway = due["gateway"]
	amount = money_text(owed(credit_note), frappe.db.get_value("Sales Invoice", credit_note, "currency"))
	if bank_account:
		entry = get_payment_entry(
			"Sales Invoice",
			credit_note,
			bank_account=frappe.db.get_value("Bank Account", bank_account, "account"),
		)
		pay_back_exactly(entry, credit_note)
		entry.bank_account = bank_account
		entry.reference_no, entry.reference_date = credit_note, nowdate()
		entry.flags.ignore_permissions = True
		entry.insert(ignore_permissions=True)
		entry.submit()
		name = entry.name
	else:
		name = refund_online(order_name, credit_note)
		if not name:
			frappe.throw(
				_("This order wasn't paid through a gateway that can refund. Refund it from a bank account.")
			)
	frappe.db.set_value("Shop Return Request", {"credit_note": credit_note}, "refund", name)
	order = frappe.get_doc("Sales Order", order_name)
	emails.send(
		"refund_sent",
		order.contact_email,
		order,
		amount=amount,
		to_card=not bank_account,
		gateway=None if bank_account else gateway,
	)
	return name


def pay_back_exactly(entry, credit_note: str) -> None:
	"""A refund from an account in the credit note's currency pays back exactly what it owes there;
	ERPNext books the change in rate since the payment as exchange gain or loss."""
	if entry.paid_from_account_currency == frappe.db.get_value("Sales Invoice", credit_note, "currency"):
		entry.paid_amount = owed(credit_note)
		entry.set_amounts()


def refund_online(order_name: str, credit_note: str) -> str | None:
	"""Refund a credit note's amount through the gateway that took the order's online payment, when
	the gateway can, and record it as ERPNext's Payment Entry against the credit note."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	found = online_refund_controller(order_name)
	if not found:
		return None
	payment_request, controller = found
	amount = owed(credit_note)
	entry = get_payment_entry("Sales Invoice", credit_note, bank_account=payment_request.payment_account)
	pay_back_exactly(entry, credit_note)
	entry.reference_no, entry.reference_date = credit_note, nowdate()
	entry.flags.ignore_permissions = True
	entry.insert(ignore_permissions=True)
	entry.submit()
	# the gateway is asked last, so nothing can undo the recorded refund once the money has gone back
	reference = controller.refund("Payment Request", payment_request.name, amount, credit_note)
	entry.db_set("reference_no", reference)
	return entry.name


def owed(credit_note: str) -> float:
	"""What a credit note still owes the customer, in its own currency (the currency they paid in):
	ERPNext keeps the outstanding amount in the customer's account currency."""
	note = frappe.db.get_value(
		"Sales Invoice",
		credit_note,
		["outstanding_amount", "currency", "party_account_currency", "conversion_rate"],
		as_dict=True,
	)
	amount = abs(flt(note.outstanding_amount))
	if (note.party_account_currency or note.currency) != note.currency:
		amount = amount / (flt(note.conversion_rate) or 1)
	return flt(amount, 2)


CANCELLED_BY_STORE = "Cancelled by the store."


def cancel_by_store(name: str, note: str | None = None) -> dict:
	"""Cancel an order that hasn't shipped. An unpaid order is cancelled; an invoiced or paid one is
	credited in full and closed, and staff refund it from its refunds due. The customer is told."""
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
	from erpnext.selling.doctype.sales_order.sales_order import update_status

	from shop.fulfillment import service
	from shop.storefront import emails
	from shop.storefront.orders import shipment_summary

	order = frappe.get_doc("Sales Order", name)
	if order.docstatus != 1 or order.status == "Closed":
		frappe.throw(_("This order can't be cancelled"))
	shipment = shipment_summary(name)
	if (shipment and (shipment.partly_shipped or shipment.status in ("Shipped", "Delivered"))) or (
		not shipment and flt(order.per_delivered)
	):
		frappe.throw(_("This order has shipped. Use a return instead."))
	# everything that can stop the cancel is checked before the carrier is told
	invoice = order_invoice(name)
	if not invoice and payment_status(order) == "Paid":
		invoice = invoice_paid_order(order)
		if not invoice and not order.get("shop_payment_method"):
			# entered in Desk: the store doesn't invoice it
			frappe.throw(_("This order is paid. Make its invoice in Desk, then cancel it here."))
		if not invoice:
			frappe.throw(
				_(
					"This order is paid but couldn't be invoiced automatically (see the note on the order). Make its invoice in Desk, then cancel it."
				)
			)
	if not invoice and flt(order.advance_paid):
		frappe.throw(_("This order is part paid. Refund the payment in ERPNext before cancelling it."))
	for fulfillment in frappe.get_all(
		"Shop Fulfillment",
		filters={"sales_order": name, "status": ["in", ("Pending", "Accepted")]},
		pluck="name",
	):
		service.cancel(fulfillment)
	order.reload()
	result = {"credit_note": None}
	if not invoice:
		for request in frappe.get_all(
			"Payment Request",
			filters={
				"reference_doctype": "Sales Order",
				"reference_name": name,
				"docstatus": 1,
				"status": ["!=", "Paid"],
			},
			pluck="name",
		):
			frappe.get_doc("Payment Request", request).cancel()
		order.reload()
		order.flags.ignore_permissions = True
		order.cancel()
	else:
		credit_note = make_sales_return(invoice)
		settle_against_invoice(credit_note, invoice)
		credit_note.flags.ignore_permissions = True
		credit_note.insert(ignore_permissions=True)
		credit_note.submit()
		result["credit_note"] = credit_note.name
		update_status("Closed", name)
	order.add_comment("Info", CANCELLED_BY_STORE + (f" {note}" if note else ""))
	amount = (
		frappe.utils.fmt_money(
			abs(flt(frappe.db.get_value("Sales Invoice", result["credit_note"], "grand_total"))),
			currency=order.currency,
		)
		if result["credit_note"]
		else ""
	)
	emails.send(
		"order_cancelled_by_store",
		order.contact_email,
		order,
		attachments=invoice_attachments(result["credit_note"]) if result["credit_note"] else None,
		note=note,
		credit_note=result["credit_note"],
		amount=amount,
		refund_due=bool(refunds_due(name)),
	)
	return result


def chase_part_paid(order) -> None:
	"""A part-paid order past its date isn't cancelled, as money came in: staff are told on the order
	and the customer is reminded of the rest, once."""
	from shop.storefront import emails

	owed = money_text(amount_due(order), order.currency)
	note = _(
		"Past its pay-by date with {0} still owed. Ask for the rest, or cancel the order and refund what was paid."
	).format(owed)
	if not note_once(order, note):
		return
	emails.send(
		"payment_short",
		order.contact_email,
		order,
		received=money_text(totals.order_total(order) - amount_due(order), order.currency),
		owed=owed,
		payment_html=bank_instructions_html(order),
	)


def forget_checkout_on_amend(doc, method=None) -> None:
	"""Sales Order before_insert: an amended store order doesn't keep the cancelled one's pay-by
	date (ERPNext's amend copies it), so it isn't cancelled again for it."""
	if doc.get("amended_from") and doc.meta.has_field("shop_payment_due"):
		doc.shop_payment_due = None


def has_note(doc, note: str) -> bool:
	"""Whether the document has this comment already; Frappe stores comments escaped."""
	return bool(
		frappe.db.exists(
			"Comment",
			{
				"reference_doctype": doc.doctype,
				"reference_name": doc.name,
				"content": ["in", [note, frappe.utils.escape_html(note)]],
			},
		)
	)


def note_once(order, note: str) -> bool:
	"""Add an Info comment to the order unless it is there already; whether it was added."""
	if has_note(order, note):
		return False
	order.add_comment("Info", note)
	return True


def unmatched_deposits(order) -> list[str]:
	"""Bank Transactions not reconciled yet that name the order: its payment may be one of them."""
	deposits = frappe.get_all(
		"Bank Transaction",
		filters={
			"docstatus": 1,
			"company": order.company,
			"deposit": [">", 0],
			"unallocated_amount": [">", 0],
			"date": [">=", order.transaction_date],
		},
		fields=["name", "reference_number", "description"],
	)
	return [
		row.name
		for row in deposits
		if mentions(order.name, compact(f"{row.reference_number or ''} {row.description or ''}"))
	]


def unmatched_payments(order) -> list[str]:
	"""The customer's Payment Entries since the order with money not allocated to anything."""
	return frappe.get_all(
		"Payment Entry",
		filters={
			"party_type": "Customer",
			"party": order.customer,
			"docstatus": 1,
			"payment_type": "Receive",
			"unallocated_amount": [">", 0],
			"posting_date": [">=", order.transaction_date],
		},
		pluck="name",
	)


REMINDER = "Payment reminder sent."


def remind_unpaid_online_orders() -> None:
	"""Remind once a customer who left the payment page, the store's set number of hours after an
	online order was placed (Shop Settings)."""
	from frappe.utils import add_to_date, cint, now_datetime

	hours = cint(frappe.get_cached_doc("Shop Settings").get("payment_reminder_hours"))
	if not hours:
		return
	for name in frappe.get_all(
		"Sales Order",
		filters={
			"docstatus": 1,
			"shop_payment_method": totals.GATEWAY,
			"status": ["not in", ["Closed", "Completed", "On Hold"]],
			"advance_payment_status": ["!=", "Fully Paid"],
			"creation": ["<", add_to_date(now_datetime(), hours=-hours)],
		},
		# an order with no due date (unpaid orders aren't cancelled) is reminded too
		or_filters=[["shop_payment_due", ">=", nowdate()], ["shop_payment_due", "is", "not set"]],
		pluck="name",
	):
		if frappe.db.exists(
			"Comment", {"reference_doctype": "Sales Order", "reference_name": name, "content": REMINDER}
		):
			continue
		order = frappe.get_doc("Sales Order", name)
		if not is_paid(order):
			remind(order)


def remind(order) -> None:
	from shop.storefront import emails
	from shop.storefront.checkout import order_email_parts
	from shop.storefront.orders import order_url, pay_url

	url = pay_url(order)
	if not url:
		return
	parts = order_email_parts(order, order_url(order.name))
	emails.send(
		"payment_reminder",
		order.contact_email,
		order,
		pay_url=url,
		# said only when the store does cancel unpaid orders
		due_date=frappe.utils.formatdate(order.shop_payment_due)
		if order.get("shop_payment_due")
		and frappe.get_cached_doc("Shop Settings").get("cancel_unpaid_orders")
		else "",
		**{key: parts[key] for key in ("lines_html", "order_url") if key in parts},
	)
	order.add_comment("Info", REMINDER)


def notify_cancelled(order) -> None:
	from shop.storefront import emails

	emails.send(
		"order_cancelled",
		order.contact_email,
		order,
		due_date=frappe.utils.formatdate(order.shop_payment_due),
	)
