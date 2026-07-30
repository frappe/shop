"""Amazon Multi-Channel Fulfillment.

Amazon picks, packs and ships orders you took on your own store, from the stock
you already hold in their warehouses. This adapter speaks the Selling Partner
API's Fulfillment Outbound section:

    POST   /fulfillment/outbound/2020-07-01/fulfillmentOrders
    GET    /fulfillment/outbound/2020-07-01/fulfillmentOrders/{id}
    PUT    /fulfillment/outbound/2020-07-01/fulfillmentOrders/{id}/cancel

Access tokens come from Login with Amazon using the seller's refresh token.
"""

import json

import frappe
from frappe.utils import get_datetime, now_datetime

from shop.fulfillment.provider import FulfillmentProvider

HOSTS = {
	"na": "https://sellingpartnerapi-na.amazon.com",
	"eu": "https://sellingpartnerapi-eu.amazon.com",
	"fe": "https://sellingpartnerapi-fe.amazon.com",
}
SANDBOX_HOSTS = {
	"na": "https://sandbox.sellingpartnerapi-na.amazon.com",
	"eu": "https://sandbox.sellingpartnerapi-eu.amazon.com",
	"fe": "https://sandbox.sellingpartnerapi-fe.amazon.com",
}
TOKEN_URL = "https://api.amazon.com/auth/o2/token"
BASE_PATH = "/fulfillment/outbound/2020-07-01/fulfillmentOrders"

# Amazon's fulfillment order statuses mapped onto ours
STATUS_MAP = {
	"NEW": "Accepted",
	"RECEIVED": "Accepted",
	"PLANNING": "Accepted",
	"PROCESSING": "Accepted",
	"CANCELLED": "Cancelled",
	"COMPLETE": "Delivered",
	"COMPLETE_PARTIALLED": "Shipped",
	"UNFULFILLABLE": "Failed",
	"INVALID": "Failed",
}


class AmazonProvider(FulfillmentProvider):
	key = "amazon_mcf"
	label = "Amazon Multi-Channel Fulfillment"

	def __init__(self):
		self.settings = frappe.get_cached_doc("Shop Amazon Fulfillment Settings")

	def is_configured(self) -> bool:
		return bool(
			self.settings.enabled
			and self.settings.seller_id
			and self.settings.marketplace_id
			and self.settings.lwa_client_id
			and self.settings.get_password("refresh_token", raise_exception=False)
		)

	def setup_hint(self) -> str:
		return (
			"Add your seller ID, marketplace ID and Login with Amazon credentials in "
			"Amazon Fulfillment Settings, then enable it."
		)

	def create_shipment(self, order, items: list[dict]) -> dict:
		address = shipping_address(order)
		payload = {
			"sellerFulfillmentOrderId": order.name,
			"displayableOrderId": order.name,
			"displayableOrderDate": f"{order.transaction_date}T00:00:00Z",
			"displayableOrderComment": self.settings.displayable_org_name or "Thank you for your order",
			"shippingSpeedCategory": self.settings.shipping_speed or "Standard",
			"destinationAddress": address,
			"items": [
				{
					"sellerSku": item["item_code"],
					"sellerFulfillmentOrderItemId": item["item_code"][:50],
					"quantity": int(item["qty"]),
				}
				for item in items
			],
			"marketplaceId": self.settings.marketplace_id,
		}
		response = self.request("POST", BASE_PATH, payload)
		return {
			"status": "Accepted",
			"external_id": order.name,
			"raw": response,
		}

	def fetch_status(self, fulfillment) -> dict:
		response = self.request("GET", f"{BASE_PATH}/{fulfillment.external_id}")
		payload = (response or {}).get("payload", response) or {}
		order = payload.get("fulfillmentOrder", {})
		shipments = payload.get("fulfillmentShipments", []) or []
		status = STATUS_MAP.get(order.get("fulfillmentOrderStatus", ""), "Accepted")
		result = {"status": status, "raw": response}
		package = first_package(shipments)
		if package:
			result.update(
				{
					"carrier": package.get("carrierCode"),
					"tracking_number": package.get("trackingNumber"),
					"tracking_url": tracking_url(package),
					"status": "Delivered" if status == "Delivered" else "Shipped",
				}
			)
		return result

	def cancel(self, fulfillment) -> dict:
		response = self.request("PUT", f"{BASE_PATH}/{fulfillment.external_id}/cancel")
		return {"status": "Cancelled", "raw": response}

	def request(self, method: str, path: str, payload: dict | None = None) -> dict:
		import requests

		host = (SANDBOX_HOSTS if self.settings.use_sandbox else HOSTS)[self.settings.region or "eu"]
		response = requests.request(
			method,
			f"{host}{path}",
			headers={
				"x-amz-access-token": self.access_token(),
				"content-type": "application/json",
			},
			data=json.dumps(payload) if payload else None,
			timeout=30,
		)
		if response.status_code >= 400:
			frappe.throw(
				frappe._("Amazon rejected the request: {0}").format(response.text[:500]),
				title=frappe._("Fulfillment failed"),
			)
		return response.json() if response.content else {}

	def access_token(self) -> str:
		"""Exchange the seller's refresh token for a short lived access token."""
		import requests

		cached = frappe.cache.get_value("shop:amazon_mcf_token")
		if cached and get_datetime(cached["expires_at"]) > now_datetime():
			return cached["token"]
		response = requests.post(
			TOKEN_URL,
			data={
				"grant_type": "refresh_token",
				"refresh_token": self.settings.get_password("refresh_token"),
				"client_id": self.settings.lwa_client_id,
				"client_secret": self.settings.get_password("lwa_client_secret"),
			},
			timeout=30,
		)
		if response.status_code >= 400:
			frappe.throw(frappe._("Could not sign in to Amazon: {0}").format(response.text[:300]))
		body = response.json()
		token = body["access_token"]
		frappe.cache.set_value(
			"shop:amazon_mcf_token",
			{
				"token": token,
				"expires_at": str(frappe.utils.add_to_date(now_datetime(), seconds=body.get("expires_in", 3600) - 60)),
			},
		)
		return token


def shipping_address(order) -> dict:
	address = frappe.get_doc("Address", order.shipping_address_name) if order.shipping_address_name else None
	if not address:
		frappe.throw(frappe._("This order has no shipping address"))
	return {
		"name": order.customer_name,
		"addressLine1": address.address_line1,
		"addressLine2": address.address_line2 or "",
		"city": address.city,
		"stateOrRegion": address.state or address.city,
		"postalCode": address.pincode or "",
		"countryCode": country_code(address.country),
		"phone": address.phone or "",
	}


def country_code(country: str | None) -> str:
	if not country:
		return ""
	return frappe.db.get_value("Country", country, "code") or ""


def first_package(shipments: list) -> dict | None:
	for shipment in shipments:
		for package in shipment.get("fulfillmentShipmentPackage", []) or []:
			if package.get("trackingNumber"):
				return package
	return None


def tracking_url(package: dict) -> str | None:
	number = package.get("trackingNumber")
	if not number:
		return None
	return f"https://track.amazon.com/tracking/{number}"
