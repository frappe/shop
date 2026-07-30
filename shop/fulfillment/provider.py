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

	def is_configured(self) -> bool:
		"""Whether credentials are present, so the panel can explain what is missing."""
		return True

	def setup_hint(self) -> str:
		return ""

	def create_shipment(self, order, items: list[dict]) -> dict:
		"""Ask the provider to ship these items.

		Returns at least {"status": one of STATUSES}, plus any of external_id,
		carrier, tracking_number, tracking_url, raw.
		"""
		raise NotImplementedError

	def fetch_status(self, fulfillment) -> dict:
		"""Current state of a shipment, in the same shape as create_shipment."""
		raise NotImplementedError

	def cancel(self, fulfillment) -> dict:
		raise NotImplementedError


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


def available() -> list[dict]:
	entries = []
	for key in sorted(registry()):
		provider = get_provider(key)
		entries.append(
			{
				"key": provider.key or key,
				"label": provider.label or key.title(),
				"configured": provider.is_configured(),
				"hint": provider.setup_hint(),
			}
		)
	return entries
