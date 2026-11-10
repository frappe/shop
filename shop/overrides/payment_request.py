import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest

from shop.routes import store_url

AUTHORIZED_STATUSES = ("Authorized", "Verified", "Completed")


class ShopPaymentRequest(PaymentRequest):
	def on_payment_authorized(self, status: str | None = None) -> str | None:
		"""Called by payments gateway controllers after a successful payment."""
		if status not in AUTHORIZED_STATUSES:
			return None
		self.flags.ignore_permissions = True
		# a gateway can report one payment twice at once (the shopper's return and its webhook)
		newly_paid = frappe.db.get_value(self.doctype, self.name, "status", for_update=True) != "Paid"
		if newly_paid and self.cancelled_meanwhile():
			self.tell_staff_of_stray_payment(status)
			return None
		if newly_paid:
			self.reload()
			self.flags.ignore_permissions = True
			self.set_as_paid()
		if not self.for_store_order():
			# a request staff made in Desk for their own order is left to ERPNext
			return None
		if newly_paid:
			from shop.storefront.checkout import send_confirmation

			# the order is handed on by its Payment Entry (payment.on_payment_entry), once
			send_confirmation(self.reference_name)
		return self.confirmation_url()

	def cancelled_meanwhile(self) -> bool:
		"""Paid through an old link after the request, or its order, was cancelled (unpaid orders are
		cancelled after their due date): the money came, but there is nothing to book it on."""
		if frappe.db.get_value(self.doctype, self.name, "docstatus") == 2:
			return True
		return self.reference_doctype == "Sales Order" and (
			frappe.db.get_value("Sales Order", self.reference_name, "docstatus") == 2
		)

	def tell_staff_of_stray_payment(self, status: str | None) -> None:
		from shop.storefront.accounts import staff_emails

		subject = frappe._("Payment received for cancelled {0} {1}").format(
			frappe._(self.reference_doctype), self.reference_name
		)
		message = frappe._(
			"Payment Request {0} was paid ({1} {2}, {3}) after it or its order was cancelled. "
			"Nothing was recorded in ERPNext: refund the customer or record the payment yourself."
		).format(self.name, self.grand_total, self.currency, status)
		frappe.log_error(
			title=subject, message=message, reference_doctype=self.doctype, reference_name=self.name
		)
		recipients = staff_emails()
		if recipients:
			frappe.sendmail(recipients=recipients, subject=subject, message=message, now=True)

	def for_store_order(self) -> bool:
		if self.reference_doctype != "Sales Order":
			return False
		from shop.storefront.orders import placed_in_store

		return placed_in_store(frappe.get_doc("Sales Order", self.reference_name))

	def confirmation_url(self) -> str | None:
		from shop.storefront.orders import access_token, order_url

		if access_token(self.reference_name):
			return order_url(self.reference_name)
		return store_url("account/orders")
