from frappe import _

from shop.fulfillment.provider import FulfillmentProvider


class PickupProvider(FulfillmentProvider):
	"""The customer collects the parcel from the location. Staff say when it is ready to collect
	(the customer is told, with the location's pickup instructions) and when it was collected."""

	key = "pickup"
	for_locations = False

	@property
	def label(self) -> str:
		return _("Collected by the customer")

	def create_shipment(self, order, items: list[dict], fulfillment=None) -> dict:
		warehouse = fulfillment.get("warehouse") if fulfillment else None
		return {"status": "Accepted", "external_id": f"PICKUP-{order.name}" + (f"-{warehouse}" if warehouse else "")}

	def fetch_status(self, fulfillment) -> dict:
		"""Nothing to poll: a pickup only moves when staff say so."""
		return {"status": fulfillment.status}

	def cancel(self, fulfillment) -> dict:
		return {"status": "Cancelled"}

	def mark_shipped(self, fulfillment, carrier: str | None = None, tracking_number: str | None = None) -> dict:
		"""Ready to collect."""
		return {"status": "Shipped"}

	def mark_delivered(self, fulfillment) -> dict:
		"""Collected."""
		return {"status": "Delivered"}
