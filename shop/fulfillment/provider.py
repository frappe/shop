"""Contract every fulfillment provider implements.

A provider turns an order into a shipment somebody else picks, packs and ships:
a marketplace fulfillment service, a courier aggregator, or a warehouse. Apps
register their own by adding to the `shop_fulfillment_providers` hook.
"""

import frappe

STATUSES = ("Pending", "Accepted", "Shipped", "Delivered", "Cancelled", "Failed")


class FulfillmentProvider:
	key = ""
	label = ""
	# sends parcels from the location's address (a courier app does; a fulfilment service ships
	# from its own warehouses)
	needs_ship_from = False
	# a location can send all its parcels this way (collection is chosen per order instead)
	for_locations = True

	def default_ship_from(self) -> str | None:
		"""The Address it sends from when a location has none of its own."""
		return None

	def is_configured(self) -> bool:
		"""Whether credentials are present, so the panel can explain what is missing."""
		return True

	def setup_hint(self) -> str:
		return ""

	def create_shipment(self, order, items: list[dict], fulfillment=None) -> dict:
		"""Ask the provider to ship these items. fulfillment is the Shop Fulfillment being sent (its
		warehouse, ship-from address and the customer's shipping choice).

		Returns at least {"status": one of STATUSES}, plus any of external_id,
		carrier, tracking_number, tracking_url, raw.
		"""
		raise NotImplementedError

	def fetch_status(self, fulfillment) -> dict:
		"""Current state of a shipment, in the same shape as create_shipment."""
		raise NotImplementedError

	def cancel(self, fulfillment) -> dict:
		raise NotImplementedError

	# A provider that books a courier and prints its label for a parcel overrides courier() and has
	# courier_services(fulfillment) -> [{"id", "provider", "carrier", "service", "amount",
	# "currency", "preferred"}], book_courier(fulfillment, service_id) -> a result as
	# create_shipment returns, print_label(fulfillment) -> the same with "files" (the label files'
	# URLs, bought the first time) and labels(fulfillment) -> the label files' URLs printed so far.

	def courier(self, fulfillment) -> dict | None:
		"""Where the parcel's courier booking and label stand: {"booked", "provider", "service",
		"amount", "currency", "labels", "can_book", "can_print_label"}, or None."""
		return None


def registry() -> dict:
	"""Every provider available on this site, keyed by its slug.

	Frappe merges dict hooks into {key: [path, ...]}, later apps last."""
	hooks = frappe.get_hooks("shop_fulfillment_providers") or {}
	return {key: paths[-1] if isinstance(paths, list) else paths for key, paths in hooks.items()}


def get_provider(key: str) -> FulfillmentProvider:
	paths = registry()
	if key not in paths:
		frappe.throw(frappe._("Fulfillment provider {0} is not available").format(key))
	return frappe.get_attr(paths[key])()


def available(for_locations: bool = False) -> list[dict]:
	"""The providers staff can send with; for_locations leaves out those a location can't use."""
	entries = []
	for key in sorted(registry()):
		provider = get_provider(key)
		if for_locations and not provider.for_locations:
			continue
		entries.append(
			{
				"key": provider.key or key,
				"label": provider.label or key.title(),
				"configured": provider.is_configured(),
				"hint": provider.setup_hint(),
			}
		)
	return entries
