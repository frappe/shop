import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.website.utils import cleanup_page_name

from shop.api import only_managers
from shop.storefront import pricing, stock


@frappe.whitelist()
def get_products(
	search: str | None = None, status: str | None = None, start: int = 0, limit: int = 20
) -> dict:
	only_managers()
	filters = {}
	if status == "published":
		filters["published"] = 1
	elif status == "draft":
		filters["published"] = 0
	or_filters = None
	if search:
		term = f"%{search.strip()}%"
		or_filters = [["product_name", "like", term], ["slug", "like", term], ["item", "like", term]]
	products = frappe.get_all(
		"Shop Product",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "product_name", "slug", "item", "published", "ranking", "has_variants"],
		order_by="ranking desc, modified desc",
		start=cint(start),
		limit=min(cint(limit) or 20, 100),
	)
	decorate(products)
	return {"products": products, "total": frappe.db.count("Shop Product", filters=filters)}


def display_names(item_codes: list[str]) -> dict[str, str]:
	"""Human names for items; variants become "Parent · Value / Value" instead of code-ish item names."""
	if not item_codes:
		return {}
	items = frappe.get_all(
		"Item", filters={"name": ["in", item_codes]}, fields=["name", "item_name", "variant_of"]
	)
	parents = {item.variant_of for item in items if item.variant_of}
	parent_names = (
		{
			row.name: row.item_name
			for row in frappe.get_all(
				"Item", filters={"name": ["in", list(parents)]}, fields=["name", "item_name"]
			)
		}
		if parents
		else {}
	)
	values = {}
	for row in frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", [item.name for item in items if item.variant_of]]},
		fields=["parent", "attribute_value"],
		order_by="idx",
	):
		values.setdefault(row.parent, []).append(row.attribute_value)
	names = {}
	for item in items:
		if item.variant_of and values.get(item.name):
			names[item.name] = (
				f"{parent_names.get(item.variant_of, item.variant_of)} · {' / '.join(values[item.name])}"
			)
		else:
			names[item.name] = item.item_name
	return names


def decorate(products: list) -> None:
	for product in products:
		product["image"] = frappe.db.get_value(
			"Shop Product Image", {"parent": product.name}, "image", order_by="idx"
		)
		codes = sellable_codes(product.item, product.has_variants)
		prices = pricing.get_prices(codes)
		rates = [entry["rate"] for entry in prices.values()]
		product["formatted_price"] = pricing.format_amount(min(rates)) if rates else None
		product["stock"] = sum(stock.get_stock(codes).values())
		product["item_group"] = (
			frappe.get_cached_value("Item", product.item, "item_group") if product.item else None
		)


def sellable_codes(item: str, has_variants: bool) -> list[str]:
	if has_variants:
		return frappe.get_all("Item", filters={"variant_of": item}, pluck="name")
	return [item]


@frappe.whitelist()
def get_product(name: str) -> dict:
	only_managers()
	doc = frappe.get_doc("Shop Product", name)
	codes = sellable_codes(doc.item, doc.has_variants)
	prices = pricing.get_prices(codes)
	stock_map = stock.get_stock(codes)
	return {
		"name": doc.name,
		"item": doc.item,
		"product_name": doc.product_name,
		"slug": doc.slug,
		"published": doc.published,
		"ranking": doc.ranking,
		"short_description": doc.short_description,
		"description": doc.description,
		"compare_at_price": doc.compare_at_price,
		"highlights": doc.highlights,
		"has_variants": doc.has_variants,
		"images": [{"image": row.image, "alt_text": row.alt_text} for row in doc.images],
		"collections": [row.collection for row in doc.collections],
		"specifications": [
			{"specification": row.specification, "value": row.value} for row in doc.specifications
		],
		**item_details(doc.item),
		"price": prices.get(doc.item, {}).get("rate") if not doc.has_variants else None,
		"variants": [
			{
				"item_code": code,
				"price": prices.get(code, {}).get("rate"),
				"stock": stock_map.get(code, 0),
			}
			for code in codes
		],
		"stock": sum(stock_map.values()),
	}


@frappe.whitelist(methods=["POST"])
def save_product(payload: dict) -> dict:
	only_managers()
	doc = (
		frappe.get_doc("Shop Product", payload["name"])
		if payload.get("name")
		else frappe.new_doc("Shop Product")
	)
	if not payload.get("name"):
		doc.item = payload["item"]
	doc.product_name = payload.get("product_name") or doc.product_name
	# a field left out of the payload keeps what it has
	for field in ("short_description", "description", "highlights"):
		if field in payload:
			doc.set(field, payload[field])
	if "compare_at_price" in payload:
		doc.compare_at_price = flt(payload["compare_at_price"]) or None
	if "ranking" in payload:
		doc.ranking = cint(payload["ranking"])
	if "published" in payload:
		doc.published = 1 if payload["published"] else 0
	if payload.get("slug"):
		doc.slug = cleanup_page_name(payload["slug"])
	set_images(doc, payload.get("images"))
	set_collections(doc, payload.get("collections"))
	if "specifications" in payload:
		set_specifications(doc, payload["specifications"])
	doc.save(ignore_permissions=True) if doc.get("name") and not doc.is_new() else doc.insert(
		ignore_permissions=True
	)
	# an emptied price field isn't a price of 0
	if payload.get("price") not in (None, "") and not doc.has_variants:
		set_price(doc.item, flt(payload["price"]))
	set_item_details(doc.item, payload)
	return get_product(doc.name)


def item_details(item_code: str) -> dict:
	"""The ERPNext Item fields the product editor shows: its group, weight, tax, stock keeping and
	where it can be sent."""
	item = frappe.get_cached_doc("Item", item_code)
	return {
		"item_group": item.item_group,
		"brand": item.brand,
		"weight": item.weight_per_unit,
		"weight_uom": item.weight_uom,
		"item_tax_template": item.taxes[0].item_tax_template if item.taxes else None,
		"track_stock": item.is_stock_item,
		"shipping_restriction": item.get("shop_shipping_restriction"),
	}


def set_item_details(item_code: str, payload: dict) -> None:
	item = frappe.get_doc("Item", item_code)
	before = item.as_dict()
	if payload.get("item_group"):
		item.item_group = payload["item_group"]
	if "brand" in payload:
		item.brand = ensure_named("Brand", "brand", payload["brand"])
	if "weight" in payload:
		item.weight_per_unit = flt(payload["weight"])
		if item.weight_per_unit and not item.weight_uom:
			item.weight_uom = default_weight_uom()
	current = item.taxes[0].item_tax_template if item.taxes else None
	if "item_tax_template" in payload and (payload["item_tax_template"] or None) != current:
		if len(item.taxes) > 1:
			frappe.throw(
				_(
					"{0} has several Item Tax rows (by tax category or date). Change them on the Item in Desk."
				).format(frappe.bold(item.item_name))
			)
		# one template for the item; ERPNext applies it wherever the store's taxes name its accounts
		item.taxes = []
		if payload["item_tax_template"]:
			item.append("taxes", {"item_tax_template": payload["item_tax_template"]})
	if "shipping_restriction" in payload:
		item.shop_shipping_restriction = payload["shipping_restriction"] or None
	if item.as_dict() != before:
		item.save(ignore_permissions=True)


def ensure_named(doctype: str, field: str, name: str | None) -> str | None:
	"""A record named this (a Brand or a Shop Specification), made when staff type a new one."""
	name = (name or "").strip()
	if name and not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, field: name}).insert(ignore_permissions=True)
	return name or None


def set_specifications(doc, rows: list[dict]) -> None:
	"""The product's specifications in the order given; a row without a value is left out."""
	doc.specifications = []
	for row in rows or []:
		value = (row.get("value") or "").strip()
		if not value:
			continue
		name = ensure_named("Shop Specification", "specification_name", row.get("specification"))
		if name:
			doc.append("specifications", {"specification": name, "value": value})


def default_weight_uom() -> str | None:
	"""The store's weight unit, else kilograms as ERPNext names them."""
	unit = frappe.get_cached_doc("Shop Settings").get("weight_uom")
	if unit:
		return unit
	for uom in ("Kg", "Kilogram"):
		if frappe.db.exists("UOM", uom):
			return uom
	return None


def set_images(doc, images) -> None:
	if images is None:
		return
	doc.images = []
	for image in images:
		url = image if isinstance(image, str) else image.get("image")
		if url:
			doc.append("images", {"image": url, "alt_text": doc.product_name})


def set_collections(doc, collections) -> None:
	if collections is None:
		return
	doc.collections = []
	for collection in collections:
		doc.append("collections", {"collection": collection})


def set_price(item_code: str, rate: float) -> None:
	"""The store price the storefront shows: the price list's Item Price for everyone (not a
	customer's own) that applies today, saved as ERPNext saves it."""
	from frappe.utils import getdate

	settings = frappe.get_cached_doc("Shop Settings")
	today = getdate()
	for row in frappe.get_all(
		"Item Price",
		filters={"item_code": item_code, "price_list": settings.price_list, "customer": ["is", "not set"]},
		fields=["name", "valid_from", "valid_upto"],
		order_by="valid_from desc",
	):
		if (row.valid_from and getdate(row.valid_from) > today) or (
			row.valid_upto and getdate(row.valid_upto) < today
		):
			continue
		price = frappe.get_doc("Item Price", row.name)
		price.price_list_rate = rate
		price.flags.ignore_permissions = True
		price.save()
		return
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": item_code,
			"price_list": settings.price_list,
			"price_list_rate": rate,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def create_product(
	product_name: str,
	price: float,
	description: str | None = None,
	short_description: str | None = None,
	compare_at_price: float | None = None,
	opening_stock: float = 0,
	images: list | None = None,
	collections: list | None = None,
	published: bool = True,
	item_group: str | None = None,
	track_stock: bool = True,
) -> dict:
	"""Create the ERPNext Item, its price and stock, and the storefront product in one step."""
	only_managers()
	settings = frappe.get_cached_doc("Shop Settings")
	item_code = unique_item_code(product_name)
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": product_name,
			"item_group": item_group or default_item_group(),
			"stock_uom": "Nos",
			"is_stock_item": 1 if track_stock else 0,
			"description": short_description or product_name,
		}
	).insert(ignore_permissions=True)
	set_price(item_code, flt(price))
	if track_stock and flt(opening_stock) > 0:
		receive_stock(item_code, flt(opening_stock), settings)
	return save_product(
		{
			"item": item_code,
			"product_name": product_name,
			"short_description": short_description,
			"description": description,
			"compare_at_price": compare_at_price,
			"images": images or [],
			"collections": collections or [],
			"published": published,
		}
	)


def unique_item_code(product_name: str) -> str:
	base = cleanup_page_name(product_name).upper()[:30] or "PRODUCT"
	code = base
	suffix = 2
	while frappe.db.exists("Item", code):
		code = f"{base}-{suffix}"
		suffix += 1
	return code


def default_item_group() -> str:
	"""ERPNext's Default Item Group (Stock Settings), else its usual "Products" group as named on
	this site, else the root Item Group."""
	from frappe.utils.nestedset import get_root_of

	default = frappe.db.get_single_value("Stock Settings", "item_group")
	for group in (default, _("Products"), "Products"):
		if group and frappe.db.exists("Item Group", group):
			return group
	return get_root_of("Item Group")


@frappe.whitelist()
def get_item_groups() -> dict:
	"""The Item Groups a product can be in, and the one new products get."""
	only_managers()
	company = frappe.get_cached_doc("Shop Settings").company
	return {
		"item_groups": frappe.get_all("Item Group", order_by="lft", pluck="name"),
		"brands": frappe.get_all("Brand", order_by="name", pluck="name"),
		"specifications": frappe.get_all("Shop Specification", order_by="ranking desc, name", pluck="name"),
		"shipping_restrictions": frappe.get_all("Shop Shipping Restriction", order_by="name", pluck="name"),
		"default": default_item_group(),
		"item_tax_templates": frappe.get_all(
			"Item Tax Template", filters={"company": company, "disabled": 0}, pluck="name"
		),
	}


def receive_stock(item_code: str, qty: float, settings) -> None:
	from shop.api.inventory import valuation_rate
	from shop.storefront.stock import primary_warehouse

	warehouse = primary_warehouse()
	if not warehouse:
		frappe.throw(_("Add a warehouse under Fulfillment locations in Settings to receive stock"))

	entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": settings.company,
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"t_warehouse": warehouse,
					# valued as ERPNext values the item, never made up from the selling price
					"basic_rate": valuation_rate(item_code, warehouse),
					"allow_zero_valuation_rate": 1,
				}
			],
		}
	)
	entry.flags.ignore_permissions = True
	entry.submit()


@frappe.whitelist(methods=["POST"])
def set_published(name: str, published: bool) -> None:
	only_managers()
	frappe.db.set_value("Shop Product", name, "published", 1 if published else 0)


@frappe.whitelist(methods=["POST"])
def delete_product(name: str) -> None:
	only_managers()
	for review in frappe.get_all("Shop Review", filters={"product": name}, pluck="name"):
		frappe.delete_doc("Shop Review", review, ignore_permissions=True, force=True)
	frappe.delete_doc("Shop Product", name, ignore_permissions=True)


@frappe.whitelist()
def get_collections() -> list[dict]:
	only_managers()
	collections = frappe.get_all(
		"Shop Collection",
		fields=[
			"name",
			"title",
			"slug",
			"description",
			"image",
			"published",
			"ranking",
			"parent_collection",
			"item_group",
		],
		order_by="ranking desc, title asc",
	)
	from shop.storefront.catalog import members

	titles = {collection.name: collection.title for collection in collections}
	for collection in collections:
		collection["parent_title"] = titles.get(collection.parent_collection)
		# those added to it, and those of the Item Group it includes
		collection["product_count"] = len(members([collection]))
	return collections


@frappe.whitelist(methods=["POST"])
def save_collection(payload: dict) -> None:
	only_managers()
	doc = (
		frappe.get_doc("Shop Collection", payload["name"])
		if payload.get("name")
		else frappe.new_doc("Shop Collection")
	)
	doc.title = payload["title"]
	doc.description = payload.get("description")
	doc.image = payload.get("image")
	doc.ranking = cint(payload.get("ranking"))
	doc.published = 1 if payload.get("published") else 0
	doc.parent_collection = payload.get("parent_collection") or None
	doc.item_group = payload.get("item_group") or None
	doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def delete_collection(name: str) -> None:
	only_managers()
	# the collections inside it move up to where it was
	parent = frappe.db.get_value("Shop Collection", name, "parent_collection")
	for child in frappe.get_all("Shop Collection", filters={"parent_collection": name}, pluck="name"):
		frappe.db.set_value("Shop Collection", child, "parent_collection", parent)
	frappe.delete_doc("Shop Collection", name, ignore_permissions=True)


@frappe.whitelist()
def get_item_group_tree() -> list[dict]:
	"""Every Item Group in tree order, with its depth and how many products are in it."""
	only_managers()
	from shop.api.pricing import item_group_depths

	depths = item_group_depths()
	counts = dict(
		frappe.get_all(
			"Item",
			filters={"variant_of": ["is", "not set"], "disabled": 0},
			fields=["item_group", {"COUNT": "*", "as": "count"}],
			group_by="item_group",
			as_list=True,
		)
	)
	return [
		{
			"name": group.name,
			"parent": group.parent_item_group,
			"depth": depths.get(group.name, 1),
			"products": counts.get(group.name, 0),
			"children": cint(group.rgt) - cint(group.lft) > 1,
		}
		for group in frappe.get_all(
			"Item Group", fields=["name", "parent_item_group", "lft", "rgt"], order_by="lft"
		)
	]


@frappe.whitelist(methods=["POST"])
def save_item_group(item_group_name: str, parent: str, name: str | None = None) -> list[dict]:
	"""Make an Item Group, or rename and move one."""
	from shop.api.pricing import arrange

	only_managers()
	item_group_name = (item_group_name or "").strip()
	if not item_group_name:
		frappe.throw(_("Name the Item Group"))
	if not frappe.db.exists("Item Group", parent):
		frappe.throw(_("Choose where the Item Group goes"))
	if not cint(frappe.db.get_value("Item Group", parent, "is_group")):
		frappe.db.set_value("Item Group", parent, "is_group", 1)
	if not name:
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": item_group_name,
				"parent_item_group": parent,
				"is_group": 1,
			}
		).insert(ignore_permissions=True)
		return get_item_group_tree()
	if item_group_name != name:
		from frappe.model.rename_doc import rename_doc

		name = rename_doc("Item Group", name, item_group_name, ignore_permissions=True)
	doc = frappe.get_doc("Item Group", name)
	if doc.parent_item_group != parent:
		doc.parent_item_group = parent
		doc.save(ignore_permissions=True)
	arrange()
	return get_item_group_tree()


@frappe.whitelist(methods=["POST"])
def delete_item_group(name: str) -> list[dict]:
	"""Remove an Item Group that has no products and no Item Groups inside it."""
	only_managers()
	lft, rgt = frappe.db.get_value("Item Group", name, ["lft", "rgt"]) or (0, 0)
	if cint(rgt) - cint(lft) > 1:
		frappe.throw(_("Move or remove the Item Groups inside {0} first").format(frappe.bold(name)))
	if frappe.db.exists("Item", {"item_group": name}):
		frappe.throw(_("Move the products in {0} to another Item Group first").format(frappe.bold(name)))
	frappe.delete_doc("Item Group", name, ignore_permissions=True)
	return get_item_group_tree()


@frappe.whitelist()
def get_item_group(name: str) -> dict:
	"""An Item Group's products (with their store product, when listed) and the groups inside it."""
	only_managers()
	if not frappe.db.exists("Item Group", name):
		frappe.throw(_("Item Group {0} not found").format(name), frappe.DoesNotExistError)
	items = frappe.get_all(
		"Item",
		filters={"item_group": name, "variant_of": ["is", "not set"]},
		fields=["name", "item_name", "disabled", "has_variants", "image"],
		order_by="item_name",
	)
	listed = {
		row.item: row
		for row in frappe.get_all(
			"Shop Product",
			filters={"item": ["in", [item.name for item in items] or [""]]},
			fields=["name", "item", "product_name", "published"],
		)
	}
	return {
		"name": name,
		"parent": frappe.db.get_value("Item Group", name, "parent_item_group"),
		"groups_inside": frappe.get_all(
			"Item Group", filters={"parent_item_group": name}, order_by="lft", pluck="name"
		),
		"products": [
			{
				"item_code": item.name,
				"name": (listed.get(item.name) or {}).get("product_name") or item.item_name,
				"product": (listed.get(item.name) or {}).get("name"),
				"published": (listed.get(item.name) or {}).get("published", 0),
				"disabled": item.disabled,
				"has_variants": item.has_variants,
				"image": product_image((listed.get(item.name) or {}).get("name")) or item.image,
			}
			for item in items
		],
	}


def product_image(product: str | None) -> str | None:
	if not product:
		return None
	return frappe.db.get_value("Shop Product Image", {"parent": product}, "image", order_by="idx")


@frappe.whitelist(methods=["POST"])
def move_products(item_codes: list[str], item_group: str) -> dict:
	"""Put products in an Item Group, their variants with them."""
	only_managers()
	if not frappe.db.exists("Item Group", item_group):
		frappe.throw(_("Choose an Item Group"))
	for code in item_codes or []:
		if frappe.db.get_value("Item", code, "variant_of"):
			continue
		for name in [code, *frappe.get_all("Item", filters={"variant_of": code}, pluck="name")]:
			item = frappe.get_doc("Item", name)
			if item.item_group != item_group:
				item.item_group = item_group
				item.flags.ignore_permissions = True
				item.save(ignore_permissions=True)
	return get_item_group(item_group)


@frappe.whitelist()
def get_specifications() -> list[dict]:
	"""The kinds of specification products are described by, with how many products use each."""
	only_managers()
	counts = dict(
		frappe.get_all(
			"Shop Product Specification",
			filters={"parenttype": "Shop Product"},
			fields=["specification", {"COUNT": "*", "as": "count"}],
			group_by="specification",
			as_list=True,
		)
	)
	rows = frappe.get_all(
		"Shop Specification",
		fields=["name", "unit", "use_as_filter", "ranking"],
		order_by="ranking desc, name",
	)
	for row in rows:
		row["products"] = counts.get(row.name, 0)
	return rows


@frappe.whitelist(methods=["POST"])
def save_specification(
	specification_name: str,
	unit: str | None = None,
	use_as_filter: int = 1,
	ranking: int = 0,
	name: str | None = None,
) -> list[dict]:
	"""Make a specification, or rename and change one; products keep their values."""
	only_managers()
	specification_name = (specification_name or "").strip()
	if not specification_name:
		frappe.throw(_("Name the specification"))
	if name and name != specification_name:
		from frappe.model.rename_doc import rename_doc

		name = rename_doc("Shop Specification", name, specification_name, ignore_permissions=True)
	doc = frappe.get_doc("Shop Specification", name) if name else frappe.new_doc("Shop Specification")
	doc.update(
		{
			"specification_name": specification_name,
			"unit": (unit or "").strip() or None,
			"use_as_filter": 1 if cint(use_as_filter) else 0,
			"ranking": cint(ranking),
		}
	)
	doc.save(ignore_permissions=True)
	return get_specifications()


@frappe.whitelist(methods=["POST"])
def delete_specification(name: str) -> list[dict]:
	"""Remove a specification no product uses."""
	only_managers()
	if frappe.db.exists("Shop Product Specification", {"specification": name, "parenttype": "Shop Product"}):
		frappe.throw(_("Products use {0}. Take it off them first").format(frappe.bold(name)))
	frappe.delete_doc("Shop Specification", name, ignore_permissions=True)
	return get_specifications()
