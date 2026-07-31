"""Hands-on walkthroughs for every shopper and merchant persona.

Each persona seeds the exact state its flow needs, then hands back a
step-by-step guide meant to be followed manually in a browser. Also usable
from the shell:

    bench --site shop.localhost execute shop.personas.prepare --kwargs "{'persona': 'deal-hunter'}"
"""

import frappe
from frappe import _

from shop import demo

SHOPPER = {"email": "walkthrough-shopper@example.test", "password": "orbit-mango-42", "name": "Meera"}
BUYER = {"email": "walkthrough-buyer@example.test", "full_name": "Walkthrough Buyer", "phone": "9876543210"}
BUYER_ADDRESS = {
	"address_line1": "12 Walkthrough Lane",
	"city": "Bengaluru",
	"state": "Karnataka",
	"country": "India",
	"pincode": "560001",
}
SEED_ITEM = "SHOP-DEMO-003"


def all_personas() -> list[dict]:
	return [describe(key) for key in PERSONAS]


def describe(key: str) -> dict:
	spec = PERSONAS[key]
	return {
		"key": key,
		"title": spec["title"],
		"tagline": spec["tagline"],
		"kind": spec["kind"],
		"minutes": spec["minutes"],
		"viewport": spec.get("viewport", "Desktop"),
		"start_url": spec["start_url"],
		"steps": spec["steps"](),
		"verify": spec["verify"],
	}


def prepare(persona: str) -> dict:
	if persona not in PERSONAS:
		frappe.throw(_("Unknown persona: {0}").format(persona))
	guide = describe(persona)
	guide["prepared"] = PERSONAS[persona]["prepare"]()
	guide["credentials"] = PERSONAS[persona].get("credentials", lambda: None)()
	return guide


def reset_catalog() -> list[str]:
	settings = frappe.get_cached_doc("Shop Settings")
	demo.reset_stock()
	demo.create_coupon(settings.company)
	return [
		"Sample stock reset to its baseline (25 each, the art print and the olive large hoodie kept out of stock)",
		"Coupon WELCOME10 for 10% off is ready",
	]


def shopper_credentials() -> dict:
	return {
		"label": "Storefront customer",
		"username": SHOPPER["email"],
		"password": SHOPPER["password"],
	}


def ensure_shopper_account() -> list[str]:
	from frappe.utils.password import update_password

	if not frappe.db.exists("User", SHOPPER["email"]):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": SHOPPER["email"],
				"first_name": SHOPPER["name"],
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value("User", SHOPPER["email"], "enabled", 1)
	update_password(SHOPPER["email"], SHOPPER["password"])
	return reset_catalog() + [
		f"Customer account {SHOPPER['email']} is ready, password below",
	]


def seed_open_order() -> list[str]:
	from shop.storefront import checkout

	item_name = frappe.db.get_value("Item", SEED_ITEM, "item_name")
	with checkout.elevated():
		cart = frappe.get_doc(
			{
				"doctype": "Shop Cart",
				"token": frappe.generate_hash(length=32),
				"status": "Active",
				"items": [
					{
						"item_code": SEED_ITEM,
						"shop_product": frappe.db.get_value("Shop Product", {"item": SEED_ITEM}),
						"qty": 2,
					}
				],
			}
		).insert(ignore_permissions=True)
		party = checkout.get_or_create_customer(BUYER)
		address = checkout.create_address(party, BUYER, BUYER_ADDRESS)
		order = checkout.create_sales_order(cart, party, address)
		checkout.convert_cart(cart, order)
	return reset_catalog() + [
		f"Placed a fresh unpaid COD order {order.name} for 2 × {item_name}",
		f"The customer's view of it: /order-confirmation/{order.name}?token={cart.token}",
	]


def guest_steps() -> list[str]:
	return [
		"Open a private window so you start as a fresh guest, then go to /",
		"From the home page open the Apparel collection, then Crew Neck T-Shirt",
		"Pick a size and colour, note how the photo follows the colour, then Add to cart",
		"The drawer slides in with the item and subtotal. Close it by clicking the dark backdrop",
		"Reload the page. The cart badge still reads 1",
		"On /cart bump the quantity with the + stepper",
		"On /checkout fill any details, keep Cash on Delivery, place the order",
		"The confirmation page lists your items, totals, and the order's progress",
		"Tamper with the token in the confirmation URL. The order details must disappear",
	]


def returning_steps() -> list[str]:
	return [
		"Open a private window, add Ceramic Mug to the cart as a guest",
		"Sign in at /login using the credentials below",
		"Visit /product/canvas-tote-bag and add it too",
		"Open /cart. The guest mug and the tote are both there, the guest cart merged into your account",
		f"Check out with Cash on Delivery using {SHOPPER['email']} as the email",
		"You stay signed in. /account/orders lists the order you just placed with its status",
		"On /product/ceramic-mug the review form is open to you. Pick 4 stars, write a line, submit",
		'Your review appears tagged "Verified buyer"',
	]


def deal_hunter_steps() -> list[str]:
	return [
		'On /products click "Under ₹ 500". Only Enamel Pin Set survives',
		'Click "In stock". Botanical Art Print disappears from the grid',
		'Click "Price, high to low". Wool Throw Blanket comes first',
		'Search for "hoodie" and open Zip Hoodie',
		'Pick Large and Olive. Both buttons flip to "Out of stock"',
		'Switch to Charcoal and hit "Buy now". You land straight on checkout',
		"If Pay Online is offered, choose it and submit. You should land on the payment page (abandon it there)",
		"Empty the cart, add Ceramic Mug, and on /checkout apply WELCOME10: subtotal ₹ 599.00, discount ₹ 59.90, total ₹ 539.10",
		"Try a bogus code. An error banner explains it is not valid",
		"Remove the coupon (total back to ₹ 599.00), re-apply it, place a COD order",
		"The discount carries through to the confirmation page",
	]


def indecisive_steps() -> list[str]:
	return [
		"In a private window add Ceramic Mug, Canvas Tote Bag and Leather Journal to the cart",
		"In the drawer: bump the mug to 3, remove the journal with ×, step the tote down to zero. No page reloads",
		"On /cart remove what is left. The empty state appears and the badge reads 0",
		"Add the mug again and step the drawer quantity up to 26 (stock is 25)",
		'On /checkout fill your details and submit. The order is blocked with "Only 25 left in stock"',
		"Open the drawer from the checkout page itself, fix the quantity to 2, submit again. The order goes through",
	]


def mobile_steps() -> list[str]:
	return [
		"Open devtools, toggle the device toolbar, pick a 390 × 844 phone",
		"On / there must be no horizontal scroll",
		"/products shows a usable two column grid",
		"On /product/ceramic-mug a buy bar stays pinned to the bottom of the screen",
		'Tap "Buy now" in the sticky bar, the checkout form fits the width',
		"Complete a Cash on Delivery order",
		"Back on /, open the cart drawer. It fits the viewport",
	]


def merchant_steps() -> list[str]:
	return [
		"Open /shop signed in as a Shop Manager (Administrator on a dev bench)",
		"The dashboard shows revenue, orders and anything that needs attention",
		'On /shop/products create a product: name, price, opening stock, a photo, then "Create"',
		"Open the storefront in another tab and search for it. It is live",
		"In /shop/settings rename the store and save. The storefront header updates on reload",
		"Turn Cash on Delivery off in the payments section. /checkout now offers only online payment",
		"Turn it back on before you leave",
	]


def operations_steps() -> list[str]:
	return [
		"Open /shop/orders. The freshly seeded order sits on top, unpaid",
		'Open it and hit "Mark paid". A payment entry is recorded',
		'In the Fulfillment card send it to "Ship it yourself" (unless auto-send already did)',
		"Mark it shipped with carrier Delhivery and any tracking number",
		"The order flips to Fulfilled and a delivery note is filed automatically",
		"/shop/fulfillments lists the shipment with its tracking link",
		"Open the customer link from the preparation notes: the confirmation page now shows the shipment progress and tracking",
	]


PERSONAS = {
	"casual-guest": {
		"title": "Casual guest",
		"tagline": "First time visitor who browses in, buys one thing with cash on delivery, never signs up",
		"kind": "shopper",
		"minutes": 5,
		"start_url": "/",
		"steps": guest_steps,
		"prepare": reset_catalog,
		"verify": [
			"Cart survives a reload",
			"A tampered confirmation token leaks nothing",
		],
	},
	"returning-customer": {
		"title": "Returning customer",
		"tagline": "Signs in mid-shop, expects the guest cart to follow, checks order history, reviews a purchase",
		"kind": "shopper",
		"minutes": 7,
		"start_url": "/product/ceramic-mug",
		"steps": returning_steps,
		"prepare": ensure_shopper_account,
		"credentials": shopper_credentials,
		"verify": [
			"Guest cart merges on login",
			"Checkout does not log the customer out",
			'The review is tagged "Verified buyer"',
		],
	},
	"deal-hunter": {
		"title": "Deal hunter",
		"tagline": "Filters hard, compares prices, pays online, never checks out without trying a coupon",
		"kind": "shopper",
		"minutes": 8,
		"start_url": "/products",
		"steps": deal_hunter_steps,
		"prepare": reset_catalog,
		"verify": [
			"Filters, sort and search all narrow the grid correctly",
			"Out of stock variants disable both buy buttons",
			"WELCOME10 takes 10% off and survives to the confirmation",
		],
	},
	"indecisive": {
		"title": "Indecisive shopper",
		"tagline": "Fills the cart, edits it, empties it, overshoots the stock, finally buys",
		"kind": "shopper",
		"minutes": 6,
		"start_url": "/product/ceramic-mug",
		"steps": indecisive_steps,
		"prepare": reset_catalog,
		"verify": [
			"Drawer edits never reload the page",
			"Checkout reports exactly how much stock is left",
		],
	},
	"mobile-shopper": {
		"title": "Mobile shopper",
		"tagline": "Shops entirely on a phone, taps the sticky buy bar, expects nothing to overflow",
		"kind": "shopper",
		"minutes": 5,
		"viewport": "Phone, 390 × 844",
		"start_url": "/",
		"steps": mobile_steps,
		"prepare": reset_catalog,
		"verify": [
			"No horizontal scroll anywhere",
			"Sticky buy bar and drawer fit the viewport",
		],
	},
	"merchant": {
		"title": "Store owner",
		"tagline": "Sets up the store, publishes a product, watches the storefront react to every change",
		"kind": "merchant",
		"minutes": 8,
		"start_url": "/shop",
		"steps": merchant_steps,
		"prepare": reset_catalog,
		"verify": [
			"A new product is buyable minutes after creation",
			"Settings changes show up on the storefront immediately",
		],
	},
	"merchant-operations": {
		"title": "Operations manager",
		"tagline": "Takes a paid order from the queue to the customer's doorstep with tracking",
		"kind": "merchant",
		"minutes": 6,
		"start_url": "/shop/orders",
		"steps": operations_steps,
		"prepare": seed_open_order,
		"verify": [
			"Marking shipped files the delivery note and flips the order to Fulfilled",
			"The customer sees the shipment progress on their confirmation page",
		],
	},
}
