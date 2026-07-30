import frappe
from frappe.utils import now_datetime

from shop.fulfillment.provider import FulfillmentProvider


class ManualProvider(FulfillmentProvider):
	"""You pick and pack yourself. Shipments are tracked here so the rest of the
	store behaves the same as it does with an outside service."""

	key = "manual"
	label = "Ship it yourself"

	def create_shipment(self, order, items: list[dict]) -> dict:
		return {
			"status": "Accepted",
			"external_id": f"MANUAL-{order.name}",
			"raw": {"accepted_on": str(now_datetime())},
		}

	def fetch_status(self, fulfillment) -> dict:
		"""Nothing to poll: a manual shipment only moves when the merchant says so."""
		return {"status": fulfillment.status}

	def cancel(self, fulfillment) -> dict:
		return {"status": "Cancelled"}

	def mark_shipped(self, fulfillment, carrier: str | None, tracking_number: str | None) -> dict:
		return {
			"status": "Shipped",
			"carrier": carrier,
			"tracking_number": tracking_number,
			"tracking_url": tracking_url(carrier, tracking_number),
		}


def tracking_url(carrier: str | None, tracking_number: str | None) -> str | None:
	if not tracking_number:
		return None
	if not carrier:
		return None
	for name, templates in (frappe.get_hooks("shop_carrier_tracking_urls") or {}).items():
		if name.lower() != carrier.lower():
			continue
		template = templates[-1] if isinstance(templates, list) else templates
		return template.format(tracking_number=tracking_number)
	return None
