import re

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt

from shop.routes import store_url
from shop.storefront import pricing, stock

MAX_PAGE_SIZE = 96
MAX_CATALOG_SIZE = 2000

SORT_ORDERS = {
	"ranking": "ranking desc, modified desc",
	"newest": "creation desc",
	"name": "product_name asc",
	"price_asc": None,
	"price_desc": None,
}


PRODUCT_FIELDS = [
	"name",
	"product_name",
	"slug",
	"short_description",
	"has_variants",
	"item",
	"compare_at_price",
]
BRAND = "brand"
PLACEHOLDER_IMAGE = "/assets/builder/images/fallback.png"


@frappe.whitelist(allow_guest=True)
def get_products(
	collection: str | None = None,
	search: str | None = None,
	sort: str = "ranking",
	start: int = 0,
	limit: int = 24,
	price_min: float | None = None,
	price_max: float | None = None,
	in_stock: bool = False,
	chosen: dict | None = None,
) -> dict:
	"""Published products, a page of them, with what they can be narrowed by.

	chosen holds the values picked for each narrowing ("brand", "spec:<Specification>",
	"option:<Item Attribute>"): a product has one of a narrowing's values, for every narrowing.
	Each narrowing lists its values with how many products have them given the others."""
	filters = {"published": 1}
	names = set(collection_members(collection)) if collection else None
	searched_as = None
	if search and search.strip():
		found = search_matches(search)
		if not found:
			# nothing for what was typed: the words as the store's products spell them
			searched_as = corrected(search)
			found = search_matches(searched_as) if searched_as else set()
		names = found if names is None else names & found
	if names is not None:
		filters["name"] = ["in", list(names) or [""]]
	candidates = frappe.get_all(
		"Shop Product",
		filters=filters,
		fields=PRODUCT_FIELDS,
		order_by=SORT_ORDERS.get(sort) or SORT_ORDERS["ranking"],
		limit=MAX_CATALOG_SIZE,
	)
	chosen = {key: set(values) for key, values in (chosen or {}).items() if values}
	traits = product_traits(candidates)
	facets = narrowings(candidates, traits, chosen)
	products = [p for p in candidates if has_all(traits[p.name], chosen)]
	by_price = sort in ("price_asc", "price_desc")
	if by_price or price_min is not None or price_max is not None or in_stock:
		decorate(products)
		products = apply_post_filters(products, price_min, price_max, in_stock)
		if by_price:
			products.sort(key=lambda p: p.price if p.price is not None else float("inf"))
			if sort == "price_desc":
				products.reverse()
		decorated = True
	else:
		decorated = False
	start = cint(start)
	limit = min(cint(limit) or 24, MAX_PAGE_SIZE)
	page = products[start : start + limit]
	if not decorated:
		decorate(page)
	return {"products": page, "total": len(products), "narrowings": facets, "searched_as": searched_as}


def product_traits(products: list) -> dict:
	"""What each product can be narrowed by: its brand, its specifications' values and the values
	its sellable variants have for each option."""
	traits = {p.name: {} for p in products}
	if not products:
		return traits
	items = {p.item: p.name for p in products}
	for row in frappe.get_all("Item", filters={"name": ["in", list(items)]}, fields=["name", "brand"]):
		if row.brand:
			traits[items[row.name]][BRAND] = {row.brand}
	for row in frappe.get_all(
		"Shop Product Specification",
		filters={"parenttype": "Shop Product", "parent": ["in", list(traits)]},
		fields=["parent", "specification", "value"],
	):
		traits[row.parent].setdefault(f"spec:{row.specification}", set()).add(row.value.strip())
	templates = [p.item for p in products if p.has_variants]
	variants = variants_by_template(templates)
	owner = {code: items[template] for template, codes in variants.items() for code in codes}
	for row in frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", list(owner) or [""]]},
		fields=["parent", "attribute", "attribute_value"],
	):
		if row.attribute_value:
			traits[owner[row.parent]].setdefault(f"option:{row.attribute}", set()).add(row.attribute_value)
	return traits


def has_all(traits: dict, chosen: dict, skip: str | None = None) -> bool:
	return all(key == skip or traits.get(key, set()) & values for key, values in chosen.items())


def narrowings(products: list, traits: dict, chosen: dict) -> list[dict]:
	"""Each way the products can be narrowed, with its values and how many products have each
	given the other narrowings chosen. One with a single value narrows nothing and is left out,
	unless it is chosen."""
	specifications = {
		row.name: row
		for row in frappe.get_all(
			"Shop Specification",
			fields=["name", "unit", "use_as_filter", "ranking"],
			order_by="ranking desc, name",
		)
	}
	keys = {key for product_traits in traits.values() for key in product_traits} | set(chosen)
	keys = [
		key
		for key in keys
		if not key.startswith("spec:") or (specifications.get(key[5:]) or {}).get("use_as_filter")
	]

	def order(key):
		if key == BRAND:
			return (0, 0, "")
		if key.startswith("spec:"):
			return (1, -cint(specifications[key[5:]].ranking), key)
		return (2, 0, key)

	result = []
	for key in sorted(keys, key=order):
		counts: dict[str, int] = {}
		for product in products:
			if has_all(traits[product.name], chosen, skip=key):
				for value in traits[product.name].get(key, ()):
					counts[value] = counts.get(value, 0) + 1
		picked = chosen.get(key, set())
		if len(counts) < 2 and not picked:
			continue
		unit = specifications[key[5:]].unit if key.startswith("spec:") else None
		values = sorted(set(counts) | picked, key=value_order)
		result.append(
			{
				"key": key,
				# labels are put into the page as HTML, and a value can come from the URL
				"label": frappe._("Brand")
				if key == BRAND
				else frappe.utils.escape_html(key.split(":", 1)[1]),
				"values": [
					{
						"value": value,
						"label": frappe.utils.escape_html(f"{value} {unit}" if unit else value),
						"count": counts.get(value, 0),
						"chosen": value in picked,
					}
					for value in values
				],
			}
		)
	return result


def value_order(value: str):
	"""Values that start with a number by its size (2 before 10), then the others by name."""
	number = re.match(r"\s*(\d+(?:\.\d+)?)", value)
	return (0, float(number.group(1)), value.lower()) if number else (1, 0, value.lower())


def apply_post_filters(products, price_min, price_max, in_stock):
	def keep(product):
		# the price ranges are the prices as the store shows them
		price = (
			pricing.shown_amount(product.price, pricing.item_tax_rate(product.item))
			if product.price is not None
			else None
		)
		if price_min is not None and (price is None or price < flt(price_min)):
			return False
		if price_max is not None and (price is None or price >= flt(price_max)):
			return False
		if in_stock and not product.in_stock:
			return False
		return True

	return [product for product in products if keep(product)]


@frappe.whitelist(allow_guest=True)
def catalog_menu() -> list[dict]:
	"""The store's collections as a tree, for the catalogue menu: each with its link, image and
	how many products it has, and the collections inside it."""
	rows = get_collections(nested=True)
	by_name = {
		row.name: {
			"title": row.title,
			"route": row.route,
			"image": row.image,
			"count": row.product_count,
			"children": [],
		}
		for row in rows
	}
	tree = []
	for row in rows:
		parent = by_name.get(row.parent_collection)
		(parent["children"] if parent else tree).append(by_name[row.name])

	def shown(entries):
		return [{**entry, "children": shown(entry["children"])} for entry in entries if entry["count"]]

	return shown(tree)


@frappe.whitelist(allow_guest=True)
def get_collections(parent: str | None = None, nested: bool = False) -> list[dict]:
	"""Published collections: those inside parent (the top ones when not given), or with nested
	every one, each followed by the collections inside it."""
	tree = published_collections()
	if nested:
		collections = [row for top in children(tree, None) for row in with_descendants(tree, top)]
	else:
		collections = children(tree, parent)
	counts = collection_counts([c.name for c in collections])
	for row in collections:
		row.route = store_url(f"collection/{row.slug}")
		row.product_count = counts.get(row.name, 0)
		row.image_css = tile_background(row.image)
	return collections


def published_collections() -> dict:
	"""Published collections by name. One inside an unpublished collection is left out with it."""
	rows = frappe.get_all(
		"Shop Collection",
		filters={"published": 1},
		fields=["name", "title", "slug", "description", "image", "parent_collection", "item_group"],
		order_by="ranking desc, title asc",
	)
	tree = {row.name: row for row in rows}
	for row in rows:
		row.level = 0
		parent = row.parent_collection
		while parent:
			if parent not in tree:
				row.hidden = True
				break
			row.level += 1
			parent = tree[parent].parent_collection
	return {name: row for name, row in tree.items() if not row.get("hidden")}


def children(tree: dict, parent: str | None) -> list:
	return [row for row in tree.values() if (row.parent_collection or None) == parent]


def with_descendants(tree: dict, row) -> list:
	return [row, *[d for child in children(tree, row.name) for d in with_descendants(tree, child)]]


def ancestors(tree: dict, name: str) -> list:
	"""The collections a collection is inside, outermost first."""
	trail, parent = [], tree[name].parent_collection
	while parent in tree:
		trail.insert(0, tree[parent])
		parent = tree[parent].parent_collection
	return trail


def tile_background(image: str | None) -> str | None:
	if not image:
		return None
	return f"url('{image}')"


def collection_members(slug: str) -> list[str]:
	"""The products in a collection and in the collections inside it."""
	tree = published_collections()
	collection = next((row for row in tree.values() if row.slug == slug), None)
	if not collection:
		return []
	return list(members(with_descendants(tree, collection)))


def members(collections: list) -> set:
	"""The products added to these collections, and those in the Item Groups they include."""
	names = {
		*frappe.get_all(
			"Shop Product Collection",
			filters={"collection": ["in", [c.name for c in collections]]},
			pluck="parent",
		)
	}
	return names | group_products([c.item_group for c in collections if c.get("item_group")])


def group_products(item_groups: list[str]) -> set:
	"""Products whose item is in one of these Item Groups or a group inside one."""
	if not item_groups:
		return set()
	inside = set()
	for lft, rgt in frappe.get_all(
		"Item Group", filters={"name": ["in", item_groups]}, fields=["lft", "rgt"], as_list=True
	):
		inside.update(
			frappe.get_all("Item Group", filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, pluck="name")
		)
	items = frappe.get_all("Item", filters={"item_group": ["in", list(inside) or [""]]}, pluck="name")
	return set(frappe.get_all("Shop Product", filters={"item": ["in", items or [""]]}, pluck="name"))


def collection_counts(collections: list[str]) -> dict:
	"""How many products each collection has, with those in the collections inside it."""
	if not collections:
		return {}
	tree = published_collections()
	if not any(name in tree for name in collections):
		return {}
	published = set(frappe.get_all("Shop Product", filters={"published": 1}, pluck="name"))
	return {
		name: len(members(with_descendants(tree, tree[name])) & published)
		for name in collections
		if name in tree
	}


def search_words(text: str) -> list[str]:
	return re.findall(r"[\w][\w.-]*", (text or "").lower())[:8]


def search_matches(text: str) -> set[str]:
	"""Published products with every word somewhere: their name, item code, descriptions, brand,
	specifications or variants' names."""
	matches = None
	for word in search_words(text):
		term = f"%{word}%"
		found = set(
			frappe.get_all(
				"Shop Product",
				filters={"published": 1},
				or_filters=[
					["product_name", "like", term],
					["short_description", "like", term],
					["description", "like", term],
					["item", "like", term],
				],
				pluck="name",
			)
		)
		items = frappe.get_all(
			"Item",
			or_filters=[["item_name", "like", term], ["brand", "like", term], ["name", "like", term]],
			fields=["name", "variant_of"],
		)
		codes = {row.variant_of or row.name for row in items}
		if codes:
			found |= set(frappe.get_all("Shop Product", filters={"item": ["in", list(codes)]}, pluck="name"))
		found |= set(
			frappe.get_all(
				"Shop Product Specification",
				filters={"parenttype": "Shop Product", "value": ["like", term]},
				pluck="parent",
			)
		)
		matches = found if matches is None else matches & found
		if not matches:
			return set()
	return matches or set()


def corrected(text: str) -> str | None:
	"""What was typed, with words the store's products don't use swapped for the nearest ones they
	do; None when there's nothing to swap."""
	from difflib import get_close_matches

	known = store_words()
	words = search_words(text)
	fixed = [
		word if word in known else (get_close_matches(word, known, n=1, cutoff=0.75) or [word])[0]
		for word in words
	]
	return " ".join(fixed) if fixed != words else None


def store_words() -> list[str]:
	"""The words in the names, short descriptions, brands and specifications of the store's
	products and its collections' names, kept a while."""
	key = "shop:search_words"
	words = frappe.cache.get_value(key)
	if words is None:
		texts = [
			text
			for row in frappe.get_all(
				"Shop Product", filters={"published": 1}, fields=["product_name", "short_description"]
			)
			for text in (row.product_name, frappe.utils.strip_html(row.short_description or ""))
		]
		texts += frappe.get_all("Shop Collection", filters={"published": 1}, pluck="title")
		texts += frappe.get_all("Item", filters={"brand": ["is", "set"]}, pluck="brand", distinct=True)
		texts += frappe.get_all("Shop Product Specification", pluck="value", distinct=True)
		words = sorted({word for text in texts for word in search_words(text) if len(word) > 2})
		frappe.cache.set_value(key, words, expires_in_sec=10 * 60)
	return words


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60)
def search_suggestions(text: str) -> dict:
	"""Products for what has been typed so far, for the list under a search box."""
	if len((text or "").strip()) < 2:
		return {"products": []}
	result = get_products(search=text[:100], limit=6)
	return {
		"products": [
			{
				"title": product.product_name,
				"route": product.route,
				"image": product.image,
				"price": product.formatted_price,
			}
			for product in result["products"]
		],
		"total": result["total"],
		"searched_as": result["searched_as"],
	}


def decorate(products: list) -> None:
	from shop.storefront import reviews

	images = first_images([p.name for p in products])
	prices = display_prices(products)
	availability = display_stock(products)
	ratings = reviews.summaries([p.name for p in products])
	for product in products:
		product.route = store_url(f"product/{product.slug}")
		product.image = images.get(product.name) or PLACEHOLDER_IMAGE
		price = prices.get(product.item, {})
		product.price = price.get("rate")
		product.formatted_price = price.get("display")
		product.formatted_price_excl = price.get("display_excl")
		if price.get("retail"):
			product.compare_at_price = max(flt(product.get("compare_at_price")), flt(price["retail"]))
		product.in_stock = availability.get(product.item, False)
		product.stock_state = "in" if product.in_stock else "out"
		product.stock_label = _("In stock") if product.in_stock else _("Out of stock")
		# a product of one version is added from its card; one with options is chosen on its page
		product.can_add = (
			"true" if not product.has_variants and product.in_stock and product.price is not None else None
		)
		product.choose_options = "true" if product.has_variants else None
		apply_compare_at(product, product.price)
		rating = ratings.get(product.name)
		product.rating_average = rating["average"] if rating else None
		product.rating_count = rating["count"] if rating else 0
		product.rating_stars = star_string(rating["average"]) if rating else None


def apply_compare_at(target, price) -> None:
	compare_at = flt(target.get("compare_at_price"))
	if not price or compare_at <= flt(price):
		target["compare_at_price"] = None
		return
	tax_rate = pricing.item_tax_rate(target.get("item"))
	target["formatted_compare_at"] = pricing.display_amount(compare_at, tax_rate)
	target["discount_pct"] = round((compare_at - flt(price)) * 100 / compare_at)
	target["formatted_savings"] = pricing.display_amount(compare_at - flt(price), tax_rate)


def star_string(average: float) -> str:
	full = int(flt(average) + 0.5)
	return "★" * full + "☆" * (5 - full)


def first_images(product_names: list[str]) -> dict:
	if not product_names:
		return {}
	rows = frappe.get_all(
		"Shop Product Image",
		filters={"parent": ["in", product_names]},
		fields=["parent", "image"],
		order_by="parent, idx",
	)
	images = {}
	for row in rows:
		images.setdefault(row.parent, row.image)
	return images


def display_prices(products: list, customer: str | None = "session") -> dict:
	"""Each product's price for the customer (the shopper's by default); a product with variants
	shows its lowest. One lookup for the page."""
	simple = [p.item for p in products if not p.has_variants]
	variants = variants_by_template([p.item for p in products if p.has_variants])
	prices = pricing.get_prices(
		simple + [code for codes in variants.values() for code in codes], customer=customer
	)
	for template, codes in variants.items():
		rates = [prices[code]["rate"] for code in codes if code in prices]
		if rates:
			prices[template] = {
				"rate": min(rates),
				"formatted": pricing.format_amount(min(rates)),
				**pricing.display_fields(min(rates), template),
			}
	return prices


def display_stock(products: list) -> dict:
	settings = frappe.get_cached_doc("Shop Settings")
	if settings.allow_out_of_stock:
		return dict.fromkeys([p.item for p in products], True)
	simple = [p.item for p in products if not p.has_variants]
	templates = [p.item for p in products if p.has_variants]
	variants = variants_by_template(templates)
	codes = simple + [code for group in variants.values() for code in group]
	stocked = {code for code in codes if stock.is_stock_item(code)}
	quantities = stock.get_stock([code for code in codes if code in stocked], sellable=True)
	# services aren't counted in stock
	available = {code: code not in stocked or quantities.get(code, 0) > 0 for code in codes}
	availability = {code: available[code] for code in simple}
	for template, group in variants.items():
		availability[template] = any(available[code] for code in group)
	return availability


def variants_by_template(templates: list[str]) -> dict[str, list[str]]:
	if not templates:
		return {}
	# variants that can be sold, as the product page offers them
	rows = frappe.get_all(
		"Item", filters={"variant_of": ["in", templates], "disabled": 0}, fields=["name", "variant_of"]
	)
	grouped = {}
	for row in rows:
		grouped.setdefault(row.variant_of, []).append(row.name)
	return grouped
