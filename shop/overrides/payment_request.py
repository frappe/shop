import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest

AUTHORIZED_STATUSES = ("Authorized", "Verified", "Completed")


class ShopPaymentRequest(PaymentRequest):
	def on_payment_authorized(self, status: str | None = None) -> str | None:
		"""Called by payments gateway controllers after a successful payment."""
		if status not in AUTHORIZED_STATUSES:
			return None
		self.flags.ignore_permissions = True
		if self.status != "Paid":
			self.set_as_paid()
		if self.reference_doctype == "Sales Order":
			from shop.fulfillment.service import auto_send

			auto_send(self.reference_name)
		return self.confirmation_url()

	def confirmation_url(self) -> str | None:
		if self.reference_doctype != "Sales Order":
			return None
		token = frappe.db.get_value("Shop Cart", {"sales_order": self.reference_name}, "token")
		if token:
			return f"/order-confirmation/{self.reference_name}?token={token}"
		return "/account/orders"
