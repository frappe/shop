import math
import re
from itertools import pairwise

import frappe
from frappe import _
from frappe.utils import cint, escape_html, flt
from frappe.utils.caching import redis_cache

from shop.routes import signin_url, store_url
from shop.storefront import cart, catalog, checkout, orders, pricing, product


@frappe.whitelist(allow_guest=True)
def home() -> dict:
	return {
		"store": store_details(),
		"collections": catalog.get_collections(),
		"featured_products": catalog.get_products(limit=8)["products"],
	}


PER_PAGE = (24, 48, 96)
LIST_PARAMS = ("search", "sort", "price", "stock", "per_page", "view", "collection")


@frappe.whitelist(allow_guest=True)
def listing() -> dict:
	"""Every published product, narrowed by what the shopper picked."""
	return {**browse(title=_("All Products")), **page_meta(_("All Products"))}


@frappe.whitelist(allow_guest=True)
def collection_page() -> dict:
	"""A collection's products (with those of the collections inside it), its sub-collections as
	tiles and where it sits."""
	tree = catalog.published_collections()
	row = next((row for row in tree.values() if row.slug == frappe.form_dict.slug), None)
	if not row:
		frappe.throw(_("Collection not found"), frappe.DoesNotExistError)
	trail = catalog.ancestors(tree, row.name)
	return {
		"collection": {key: row.get(key) for key in ("title", "slug", "description", "image")},
		"breadcrumbs": [{"title": r.title, "route": store_url(f"collection/{r.slug}")} for r in trail]
		or None,
		"sub_collections": catalog.get_collections(parent=row.name) or None,
		**browse(title=row.title, description=row.description, collection=row),
		**page_meta(row.title, row.description, row.image),
	}


def owing_summary(rows) -> str:
	"""What the customer owes across their invoices (in each currency), the next due date and how
	many are overdue."""
	esc = frappe.utils.escape_html
	unpaid = [row for row in rows if flt(row.outstanding_amount) > 0]
	if not unpaid:
		return f"<p class='account-owing'>{esc(_('Nothing owing. Thank you.'))}</p>"
	by_currency: dict[str, float] = {}
	for row in unpaid:
		by_currency[row.currency] = by_currency.get(row.currency, 0) + flt(row.outstanding_amount)
	owed = ", ".join(
		frappe.utils.fmt_money(amount, currency=currency) for currency, amount in by_currency.items()
	)
	text = (
		_("You owe {0} on {1} invoices.").format(owed, len(unpaid))
		if len(unpaid) != 1
		else _("You owe {0} on 1 invoice.").format(owed)
	)
	overdue = sum(1 for row in unpaid if row.overdue)
	upcoming = [row.due_date for row in unpaid if row.due_date and not row.overdue]
	if overdue:
		note = f" <strong class='account-overdue'>{esc(_('{0} overdue.').format(overdue))}</strong>"
	elif upcoming:
		note = " " + esc(_("Next due {0}.").format(frappe.utils.formatdate(min(upcoming))))
	else:
		note = ""
	return f"<p class='account-owing'>{esc(text)}{note}</p>"


def search_label(search: str | None, searched_as: str | None) -> str | None:
	if not search:
		return None
	if searched_as:
		# nothing matched what was typed, so the nearest words were searched for
		return escape_html(_('Results for "{0}" (no results for "{1}")').format(searched_as, search))
	return escape_html(_('Results for "{0}"').format(search))


def narrowing_params() -> dict[str, str]:
	"""The URL parameter for each way products can be narrowed: brand, spec_<name>, option_<name>."""
	params = {"brand": catalog.BRAND}
	for name in frappe.get_all("Shop Specification", filters={"use_as_filter": 1}, pluck="name"):
		params[f"spec_{frappe.scrub(name)}"] = f"spec:{name}"
	for name in frappe.get_all("Item Attribute", pluck="name"):
		params[f"option_{frappe.scrub(name)}"] = f"option:{name}"
	return params


def picked(form, param: str) -> list[str]:
	return [value for value in (form.get(param) or "").split("|") if value]


def browse(title: str, description: str | None = None, collection=None) -> dict:
	"""A page of products with the filters beside them, the toolbar above and the filters applied."""
	form = frappe.form_dict
	params = narrowing_params()
	keys = {key: param for param, key in params.items()}
	chosen = {key: picked(form, param) for param, key in params.items() if form.get(param)}
	per_page = cint(form.get("per_page")) if cint(form.get("per_page")) in PER_PAGE else PER_PAGE[0]
	page = max(cint(form.get("page")) or 1, 1)
	price_min, price_max = parse_price_bucket(form.get("price"))
	result = catalog.get_products(
		collection=collection.slug if collection else form.get("collection"),
		search=form.get("search"),
		sort=form.get("sort") or "ranking",
		start=(page - 1) * per_page,
		limit=per_page,
		price_min=price_min,
		price_max=price_max,
		in_stock=form.get("stock") == "in",
		chosen=chosen,
	)
	total = result["total"]
	last = max((total + per_page - 1) // per_page, 1)
	view = "list" if form.get("view") == "list" else "grid"

	def url(changes: dict, keep_page: bool = False) -> str:
		return listing_url(form, params, changes, keep_page)

	def option(label, param, value, count=None):
		active = (form.get(param) or "") == (value or "")
		return {
			"label": label,
			"url": url({param: value}),
			"active": "true" if active else "false",
			"count": count,
		}

	groups = []
	inside = catalog.get_collections(parent=collection.name) if collection else catalog.get_collections()
	if inside:
		groups.append(
			{
				"label": _("Category"),
				"options": [
					{
						"label": row.title,
						"url": row.route,
						"active": "false",
						"count": row.product_count,
					}
					for row in inside
					if row.product_count
				],
			}
		)
	groups.append(
		{
			"label": _("Availability"),
			"single": "true",
			"options": [option(_("All"), "stock", None), option(_("In stock"), "stock", "in")],
		}
	)
	buckets = {key: price_label(label, low, high) for key, label, (low, high) in useful_price_buckets(form)}
	if buckets:
		groups.append(
			{
				"label": _("Price"),
				"single": "true",
				"options": [
					option(_("Any price"), "price", None),
					*[option(label, "price", key) for key, label in buckets.items()],
				],
			}
		)
	applied = []
	for narrowing in result["narrowings"]:
		param = keys[narrowing["key"]]
		current = picked(form, param)
		options = []
		for value in narrowing["values"]:
			others = [v for v in current if v != value["value"]]
			toggled = others if value["chosen"] else [*current, value["value"]]
			options.append(
				{
					"label": value["label"],
					"url": url({param: "|".join(toggled)}),
					"active": "true" if value["chosen"] else "false",
					"count": value["count"],
				}
			)
			if value["chosen"]:
				applied.append(
					{
						"label": f"{narrowing['label']}: {value['label']}",
						"url": url({param: "|".join(others)}),
					}
				)
		groups.append({"label": narrowing["label"], "options": options, "multiple": "true"})
	if form.get("stock") == "in":
		applied.insert(0, {"label": _("In stock"), "url": url({"stock": None})})
	if form.get("price") in buckets:
		label = buckets[form.get("price")]
		applied.insert(0, {"label": _("Price: {0}").format(label), "url": url({"price": None})})
	return {
		"store": store_details(),
		"title": escape_html(title),
		"description": description,
		# page data is put into the page as HTML, so what the shopper typed is escaped
		"search": escape_html(form.get("search") or ""),
		"search_label": search_label(form.get("search"), result.get("searched_as")),
		"filter_groups": groups,
		"applied": applied or None,
		"clear_url": url({key: None for key in (*params, "price", "stock")}) if applied else None,
		"filter_count": str(len(applied)) if applied else None,
		"total_label": _("{0} products").format(total) if total != 1 else _("1 product"),
		"page_label": _("Page {0} of {1}").format(min(page, last), last),
		"sort_options": [
			option(_(label), "sort", None if key == "ranking" else key) for key, label in SORT_OPTIONS
		],
		"per_page_options": [
			option(str(n), "per_page", None if n == PER_PAGE[0] else str(n)) for n in PER_PAGE
		],
		"view": view,
		"grid_url": url({"view": None}, keep_page=True),
		"list_url": url({"view": "list"}, keep_page=True),
		"grid_active": "true" if view == "grid" else "false",
		"list_active": "true" if view == "list" else "false",
		"no_results": None if result["products"] else "true",
		"page": page,
		"pager": {
			"prev_url": url({"page": str(page - 1) if page > 2 else None}, keep_page=True)
			if page > 1
			else None,
			"next_url": url({"page": str(page + 1)}, keep_page=True) if page < last else None,
		}
		if last > 1
		else None,
		"products": result["products"],
		"total": total,
	}


def price_label(label: str, low: float | None, high: float | None) -> str:
	from frappe.utils import fmt_money

	currency = frappe.get_cached_doc("Shop Settings").currency
	return _(label).format(
		fmt_money(low or high, currency=currency, precision=0),
		fmt_money(high or low, currency=currency, precision=0),
	)


def listing_url(form, params: dict, changes: dict, keep_page: bool = False) -> str:
	"""This page's URL with the shopper's filters, changed as given; a new filter starts at page 1."""
	from urllib.parse import urlencode

	request_path = (
		frappe.local.request.path if getattr(frappe.local, "request", None) else store_url("products")
	)
	query = {key: form.get(key) for key in (*LIST_PARAMS, *params) if form.get(key)}
	if keep_page and form.get("page"):
		query["page"] = form.get("page")
	for key, value in changes.items():
		if value:
			query[key] = value
		else:
			query.pop(key, None)
	return request_path + (f"?{urlencode(query)}" if query else "")


SORT_OPTIONS = [
	("ranking", "Featured"),
	("newest", "Newest"),
	("name", "Name"),
	("price_asc", "Price, low to high"),
	("price_desc", "Price, high to low"),
]


def parse_price_bucket(bucket: str | None):
	"""A price range from the listing's URL, "low-high" with either end left open."""
	low, _sep, high = (bucket or "").partition("-")
	try:
		return (float(low) if low else None), (float(high) if high else None)
	except ValueError:
		return None, None


def tidy_amount(amount: float) -> float:
	"""An amount rounded up to 1, 2, 2.5 or 5 of its order of magnitude, for a price range's edge."""
	if amount <= 0:
		return 0
	scale = 10 ** math.floor(math.log10(amount))
	return next(step * scale for step in (1, 2, 2.5, 5, 10) if amount <= step * scale)


def price_buckets(rates: list[float]) -> list[tuple]:
	"""Price ranges for the store's own prices: about a quarter of the products in each, with edges
	at tidy amounts in the store's currency."""
	rates = sorted(rate for rate in rates if rate > 0)
	if len(rates) < 2:
		return []
	edges = sorted({tidy_amount(rates[int(len(rates) * share)]) for share in (0.25, 0.5, 0.75)})
	edges = [edge for edge in edges if rates[0] < edge <= rates[-1]]
	ends = [None, *edges, None]
	return [
		(
			f"{low or 0:g}-{'' if high is None else f'{high:g}'}",
			"Under {0}" if low is None else ("Over {0}" if high is None else "{0} to {1}"),
			(low, high),
		)
		for low, high in pairwise(ends)
	]


def useful_price_buckets(form) -> list:
	"""The price ranges that have products in them. With fewer than two, a price filter can't
	narrow anything down and is left out (unless the shopper already chose a range)."""
	rates = listed_prices(frappe.get_cached_doc("Shop Settings").price_list)
	buckets = [
		bucket
		for bucket in price_buckets(rates)
		if any(
			(bucket[2][0] or 0) <= rate and (bucket[2][1] is None or rate < bucket[2][1]) for rate in rates
		)
	]
	if len(buckets) < 2 and not form.get("price"):
		return []
	return buckets


@redis_cache(ttl=300)
def listed_prices(price_list: str) -> list[float]:
	"""The store price each published product is listed at (its lowest variant's, for variants)."""
	products = frappe.get_all("Shop Product", filters={"published": 1}, fields=["item", "has_variants"])
	prices = catalog.display_prices(products, customer=None)
	return [flt(prices[p.item]["rate"]) for p in products if p.item in prices]


@frappe.whitelist(allow_guest=True)
def product_page() -> dict:
	detail = product.get_product(frappe.form_dict.slug)
	detail["image"] = detail["images"][0]["image"] if detail["images"] else None
	detail["buy_item_code"] = detail.get("default_item_code") or detail["item"]
	detail["description_text"] = frappe.utils.strip_html(detail.get("description") or "")
	# the description as safe HTML, so lists, headings and spec tables keep their layout
	from frappe.utils.html_utils import sanitize_html

	detail["description_html"] = sanitize_html(detail.get("description") or "")
	detail["attribute_options"] = [
		{
			"attribute": option["attribute"],
			"values": [{"attribute": option["attribute"], "value": value} for value in option["values"]],
		}
		for option in detail.get("attributes", [])
	]
	detail["show_fabric_band"] = (
		"true" if any(c.get("slug") == "apparel" for c in detail.get("collections") or []) else None
	)
	from shop.storefront import reviews

	detail["structured_data"] = structured_data(detail)
	return {
		"store": store_details(),
		"product": detail,
		"related_products": related_products(detail),
		"reviews": reviews.get_reviews(detail["name"], limit=6),
		# Builder writes the page's <title> from this, as it is
		"title": escape_html(detail["product_name"]),
		**page_meta(
			detail["product_name"],
			detail.get("short_description") or detail["description_text"],
			detail["image"],
			kind="product",
		),
	}


def page_meta(
	title: str, description: str | None = None, image: str | None = None, kind: str = "website"
) -> dict:
	"""The page's title, and what search results and shared links show of it."""
	from frappe.utils import get_url

	store = frappe.get_cached_doc("Shop Settings").store_name
	full_title = f"{title} | {store}" if store else title
	description = " ".join(frappe.utils.strip_html(description or "").split())
	if len(description) > 160:
		description = description[:157].rsplit(" ", 1)[0] + "..."
	return {
		"metatags": {
			"title": full_title,
			"description": description or full_title,
			"image": get_url(image) if image else None,
			"og:type": kind,
		},
	}


def structured_data(detail: dict) -> str:
	"""The product for search engines (schema.org), so results can show its price, stock and rating."""
	import json

	from frappe.utils import get_url

	currency = pricing.store_currency()
	if detail.get("has_variants"):
		sold = [v for v in detail.get("variants") or [] if v.get("price") is not None]
		offers = {
			"@type": "AggregateOffer",
			"priceCurrency": currency,
			"lowPrice": min((shown_price(v["price"], v["item_code"]) for v in sold), default=None),
			"highPrice": max((shown_price(v["price"], v["item_code"]) for v in sold), default=None),
			"offerCount": len(sold),
			"availability": in_stock(any(v.get("purchasable") for v in sold)),
		}
	else:
		offers = {
			"@type": "Offer",
			"priceCurrency": currency,
			"price": shown_price(detail.get("price"), detail["item"]),
			"availability": in_stock(detail.get("purchasable")),
		}
	offers["url"] = get_url(store_url(f"product/{detail['slug']}"))
	data = {
		"@context": "https://schema.org",
		"@type": "Product",
		"name": detail["product_name"],
		"sku": detail.get("default_item_code") or detail["item"],
		"description": " ".join(
			frappe.utils.strip_html(
				detail.get("short_description") or detail["description_text"] or ""
			).split()
		),
		"image": [get_url(row["image"]) for row in detail.get("images") or [] if row.get("image")],
		"offers": {key: value for key, value in offers.items() if value is not None},
	}
	brand = frappe.db.get_value("Item", detail["item"], "brand")
	if brand:
		data["brand"] = {"@type": "Brand", "name": brand}
	rating = detail.get("rating") or {}
	if rating.get("count"):
		data["aggregateRating"] = {
			"@type": "AggregateRating",
			"ratingValue": rating["average"],
			"reviewCount": rating["count"],
		}
	# inside a <script>, "</" could end it early
	return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def shown_price(rate: float | None, item_code: str) -> float | None:
	if rate is None:
		return None
	return flt(pricing.shown_amount(rate, pricing.item_tax_rate(item_code)), 2)


def in_stock(available) -> str:
	return "https://schema.org/InStock" if available else "https://schema.org/OutOfStock"


def related_products(detail: dict) -> list:
	collections = detail.get("collections") or []
	if collections:
		result = catalog.get_products(collection=collections[0]["slug"], limit=5)["products"]
	else:
		result = catalog.get_products(limit=5)["products"]
	return [product for product in result if product.slug != detail["slug"]][:4]


@frappe.whitelist(allow_guest=True)
def basic() -> dict:
	return {"store": store_details()}


@frappe.whitelist(allow_guest=True)
def cart_page() -> dict:
	if frappe.form_dict.get("restore"):
		cart.restore_cart(frappe.form_dict.restore)
	return {"store": store_details(), "cart": cart.get_cart()}


@frappe.whitelist(allow_guest=True)
def checkout_page() -> dict:
	return {"store": store_details(), **checkout.get_checkout_summary()}


@frappe.whitelist(allow_guest=True)
def order_confirmation() -> dict:
	form = frappe.form_dict
	return {
		"store": store_details(),
		"order": orders.get_order_summary(form.order_id, form.get("token")),
	}


@frappe.whitelist()
def account_orders() -> dict:
	from shop.storefront import accounts, pricing

	customer = pricing.session_customer()
	return {
		"store": store_details(),
		"orders": orders.get_orders(),
		"account_html": pricing.buying_for_html() + account_html([customer] if customer else []),
		"trade": accounts.trade_status(),
	}


def account_html(customers: list[str]) -> str:
	"""Invoices and quotes as ready-made HTML for the account page."""
	from shop.storefront import accounts

	esc = frappe.utils.escape_html
	html = ""
	trade = accounts.trade_status()
	if trade and trade.get("trade"):
		note = _("Trade account: you see your trade prices across the store.")
		if trade.get("on_account"):
			note += " " + _("You can pay on account ({0}).").format(trade.get("payment_terms"))
		html += f'<div class="account-note">{esc(note)}</div>'
	elif trade and trade.get("status") == "Pending":
		html += (
			f'<div class="account-note">{esc(_("Your trade account application is being reviewed."))}</div>'
		)
	else:
		html += (
			f'<div class="account-note">{esc(_("Buying for a business?"))} '
			f'<a href="{store_url("account/trade")}">{esc(_("Apply for a trade account"))}</a></div>'
		)
	rows = accounts.invoices(customers)
	if customers and frappe.db.exists(
		"GL Entry", {"party_type": "Customer", "party": ["in", customers], "is_cancelled": 0}
	):
		html += (
			f'<div class="account-actions"><a class="account-statement" '
			f'href="/api/method/shop.storefront.statements.statement_pdf">{esc(_("Download statement"))}</a> '
			f"<span>{esc(_('Your invoices and payments for the last 12 months.'))}</span></div>"
		)
	if rows:
		html += f"<h2>{esc(_('Invoices'))}</h2>" + owing_summary(rows) + "<div class='account-table'>"
		for row in rows:
			if frappe.utils.flt(row.outstanding_amount) <= 0:
				owing = esc(_("Paid"))
			elif row.overdue:
				owing = (
					f"<strong class='account-overdue'>{esc(_('Overdue'))}</strong> "
					f"{esc(row.formatted_outstanding)}, {esc(_('was due'))} {esc(frappe.utils.formatdate(row.due_date))}"
				)
			else:
				owing = f"{esc(_('Owing'))} {esc(row.formatted_outstanding)}, {esc(_('due'))} {esc(frappe.utils.formatdate(row.due_date))}"
			pay = (
				f'<a class="account-pay" href="{esc(row.pay_url)}">{esc(_("Pay"))}</a>' if row.pay_url else ""
			)
			html += (
				f'<div class="account-row"><span>{esc(row.name)}</span><span>{esc(frappe.utils.formatdate(row.posting_date))}</span>'
				f"<span>{esc(row.formatted_total)}</span><span>{owing}</span>"
				f'<span class="account-links"><a href="{esc(row.pdf_url)}">{esc(_("PDF"))}</a>{pay}</span></div>'
			)
		html += "</div>"
	quotes = (
		frappe.get_all(
			"Quotation",
			filters={
				"party_name": ["in", customers or [""]],
				"quotation_to": "Customer",
				"docstatus": ["<", 2],
			},
			fields=[
				"name",
				"transaction_date",
				"valid_till",
				"grand_total",
				"rounded_total",
				"currency",
				"docstatus",
				"status",
				"shop_access_token",
			],
			order_by="creation desc",
			limit=20,
		)
		if customers and frappe.get_meta("Quotation").has_field("shop_access_token")
		else []
	)
	if quotes:
		html += f"<h2>{esc(_('Quotes'))}</h2><div class='account-table'>"
		from frappe.utils import getdate, nowdate

		from shop.storefront.quotes import quote_status

		for row in quotes:
			expired = bool(row.valid_till and getdate(row.valid_till) < getdate(nowdate()))
			closed = row.status in ("Lost", "Cancelled")
			ordered = "Ordered" if row.status == "Ordered" else None
			state = quote_status(row, ordered, expired, closed)
			# a lost or expired quote has nothing to open
			can_open = row.docstatus == 1 and (ordered or not (expired or closed))
			link = store_url(f"quote/{row.name}?token={row.shop_access_token}") if can_open else ""
			total = flt(row.rounded_total) or flt(row.grand_total)
			html += (
				f'<div class="account-row"><span>{esc(row.name)}</span><span>{esc(frappe.utils.formatdate(row.transaction_date))}</span>'
				f"<span>{esc(frappe.utils.fmt_money(total, currency=row.currency))}</span><span>{esc(state)}</span>"
				+ (f'<a href="{esc(link)}">{esc(_("View"))}</a>' if link else "<span></span>")
				+ "</div>"
			)
		html += "</div>"
	return html


@frappe.whitelist(allow_guest=True)
def register_page() -> dict:
	from shop.storefront import checkout

	signed_in = frappe.session.user != "Guest"
	return {
		"store": store_details(),
		"terms": checkout.terms_details(),
		"show_form": None if signed_in else "true",
		"notice": _("You're signed in. Your orders and invoices are on your account page.")
		if signed_in
		else None,
		"trade_applications": trade_applications(),
	}


def trade_applications() -> str | None:
	"""Whether the store takes trade account applications, for pages that offer them."""
	return "true" if frappe.get_cached_doc("Shop Settings").allow_trade_applications else None


@frappe.whitelist(allow_guest=True)
def signin_page() -> dict:
	signed_in = frappe.session.user != "Guest"
	return {
		"store": store_details(),
		"show_form": None if signed_in else "true",
		"notice": _("You're signed in. Your orders and invoices are on your account page.")
		if signed_in
		else None,
		"redirect_to": return_path(frappe.form_dict.get("redirect-to")),
		"register_url": store_url("account/register"),
		"trade_applications": trade_applications(),
	}


def return_path(path: str | None) -> str:
	"""Where to go after signing in: a page on this site, else the account page."""
	from urllib.parse import urlsplit

	if path and SAFE_PATH.fullmatch(path) and not path.startswith("//") and not urlsplit(path).netloc:
		return path
	return store_url("account/orders")


# a path, its query and nothing that could end the HTML attribute it is put in
SAFE_PATH = re.compile(r"/[A-Za-z0-9/_\-.~%?=&+:,]*")


@frappe.whitelist(allow_guest=True)
def trade_page() -> dict:
	from shop.storefront import accounts, checkout

	return {
		"store": store_details(),
		"terms": checkout.terms_details(),
		"countries": checkout.countries(),
		"default_country": checkout.totals.company_country(),
		"prefill": checkout.checkout_prefill(),
		**trade_form_state(accounts.trade_status()),
		# what the business does: ERPNext's Industry Types, as on a Lead
		"industries": [{"value": "", "label": frappe._("What does your business do?")}]
		+ [
			{"value": name, "label": name}
			for name in frappe.get_all("Industry Type", pluck="name", order_by="name")
		],
	}


def trade_form_state(trade: dict | None) -> dict:
	"""Whether the trade application form shows, or what to tell a business that has applied."""
	if not trade_applications():
		return {
			"trade": trade,
			"show_form": None,
			"notice": _("We aren't taking trade account applications."),
		}
	status = (trade or {}).get("status")
	notice = {
		"Approved": _("Your trade account is open. Sign in to see your trade prices."),
		"Pending": _("We have your application and will email you once we've reviewed it."),
	}.get(status)
	if trade and trade.get("trade"):
		notice = _("Your trade account is open. Your trade prices show while you're signed in.")
	return {"trade": trade, "show_form": None if notice else "true", "notice": notice}


@frappe.whitelist(allow_guest=True)
def quote_page() -> dict:
	from shop.storefront import checkout, quotes

	form = frappe.form_dict
	try:
		quote = quotes.quote_summary(form.get("quote_id"), form.get("token"))
	except (frappe.PermissionError, frappe.DoesNotExistError):
		frappe.clear_messages()
		quote = None
	return {
		"store": store_details(),
		"quote": quote,
		"quote_invalid": None if quote else "true",
		"terms": checkout.terms_details(),
	}


@frappe.whitelist(allow_guest=True)
def terms_page() -> dict:
	from frappe.utils.html_utils import sanitize_html

	from shop.storefront import terms

	return {
		"store": store_details(),
		"terms_html": sanitize_html(terms.text()),
		"terms_version": terms.version() or "",
	}


def store_details() -> dict:
	from shop.storefront import returns, shipping

	settings = frappe.get_cached_doc("Shop Settings")
	signed_in = frappe.session.user not in ("Guest", None)
	delivery_note, returns_note = shipping.free_shipping_note(), returns.returns_note()
	return {
		"name": settings.store_name,
		"logo": settings.store_logo,
		"currency": settings.currency,
		"enable_cod": settings.enable_cod,
		"delivery_note": delivery_note,
		"returns_note": returns_note,
		"delivery_card": "true" if delivery_note or returns_note or settings.enable_cod else None,
		"account_label": frappe._("Account") if signed_in else frappe._("Sign in"),
		"account_url": store_url("account/orders") if signed_in else signin_url(store_url("account/orders")),
		"register_url": None if signed_in else store_url("account/register"),
		"home_url": store_url(""),
		"menu_label": settings.get("menu_label") or frappe._("Products"),
		"display_currency": pricing.display_currency(),
		"currency_picker_html": pricing.currency_picker_html(),
	}
