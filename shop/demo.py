import frappe

DEMO_PREFIX = "SHOP-DEMO-"
ITEM_GROUP = "Products"
STOCK_QTY = 25

COLLECTIONS = [
	{"title": "Apparel", "description": "Everyday staples, cut well and built to last."},
	{"title": "Home & Living", "description": "Small upgrades that make a room feel finished."},
	{"title": "Stationery", "description": "Tools for people who still love paper."},
	{"title": "Gifts", "description": "Safe bets for birthdays, thank-yous and just-because."},
]

PRODUCTS = [
	{
		"code": "001",
		"name": "Crew Neck T-Shirt",
		"price": 899,
		"collections": ["Apparel"],
		"short": "Heavyweight combed cotton tee with a boxy, modern fit.",
		"variants": {"Size": ["Small", "Medium", "Large"], "Colour": ["Black", "White"]},
	},
	{
		"code": "002",
		"name": "Zip Hoodie",
		"price": 2499,
		"collections": ["Apparel"],
		"short": "Brushed fleece hoodie with a two-way zip and drop shoulders.",
		"variants": {"Size": ["Small", "Medium", "Large"], "Colour": ["Charcoal", "Olive"]},
	},
	{
		"code": "003",
		"name": "Ceramic Mug",
		"price": 599,
		"collections": ["Home & Living", "Gifts"],
		"short": "Stoneware mug with a matte glaze and a generous 350ml pour.",
	},
	{
		"code": "004",
		"name": "Canvas Tote Bag",
		"price": 799,
		"collections": ["Apparel", "Gifts"],
		"short": "16oz cotton canvas tote that carries groceries and laptops alike.",
	},
	{
		"code": "005",
		"name": "Scented Soy Candle",
		"price": 899,
		"collections": ["Home & Living", "Gifts"],
		"short": "Cedar and amber soy candle, 40 hours of slow burn.",
	},
	{
		"code": "006",
		"name": "Leather Journal",
		"price": 1299,
		"collections": ["Stationery", "Gifts"],
		"short": "Full-grain leather cover around 240 pages of lay-flat paper.",
	},
	{
		"code": "007",
		"name": "Insulated Water Bottle",
		"price": 999,
		"collections": ["Home & Living"],
		"short": "Double-walled steel bottle that keeps drinks cold for 24 hours.",
	},
	{
		"code": "008",
		"name": "Enamel Pin Set",
		"price": 499,
		"collections": ["Gifts"],
		"short": "Set of four hard-enamel pins with rubber clutch backs.",
	},
	{
		"code": "009",
		"name": "Botanical Art Print",
		"price": 1499,
		"collections": ["Home & Living"],
		"short": "A3 giclée print on archival cotton paper, unframed.",
	},
	{
		"code": "010",
		"name": "Oak Desk Organizer",
		"price": 1999,
		"collections": ["Stationery", "Home & Living"],
		"short": "Solid oak tray with slots for pens, phone and loose change.",
	},
	{
		"code": "011",
		"name": "Wool Throw Blanket",
		"price": 2999,
		"collections": ["Home & Living"],
		"short": "Lambswool throw in a herringbone weave, 130 by 180 cm.",
	},
	{
		"code": "012",
		"name": "Wireless Charging Pad",
		"price": 1799,
		"collections": ["Gifts"],
		"short": "Slim 15W charger wrapped in fabric, with a non-slip base.",
	},
]


def setup(force: bool = False):
	settings = ensure_settings()
	create_attributes()
	create_items()
	create_prices(settings.price_list)
	create_stock(settings.default_warehouse, settings.company)
	create_collections()
	create_products()


def teardown():
	delete_products_and_collections()
	delete_stock_entries()
	delete_prices()
	delete_items()


def delete_products_and_collections():
	for name in frappe.get_all("Shop Product", filters={"item": ["like", f"{DEMO_PREFIX}%"]}, pluck="name"):
		frappe.delete_doc("Shop Product", name, ignore_permissions=True, force=True)
	titles = [collection["title"] for collection in COLLECTIONS]
	for name in frappe.get_all("Shop Collection", filters={"title": ["in", titles]}, pluck="name"):
		frappe.delete_doc("Shop Collection", name, ignore_permissions=True, force=True)


def delete_stock_entries():
	entries = frappe.get_all(
		"Stock Entry Detail",
		filters={"item_code": ["like", f"{DEMO_PREFIX}%"]},
		pluck="parent",
		distinct=True,
	)
	for name in entries:
		entry = frappe.get_doc("Stock Entry", name)
		if entry.docstatus == 1:
			entry.flags.ignore_permissions = True
			entry.cancel()
		frappe.delete_doc("Stock Entry", name, ignore_permissions=True, force=True)


def delete_prices():
	for name in frappe.get_all(
		"Item Price", filters={"item_code": ["like", f"{DEMO_PREFIX}%"]}, pluck="name"
	):
		frappe.delete_doc("Item Price", name, ignore_permissions=True, force=True)


def delete_items():
	variants_first = frappe.get_all(
		"Item",
		filters={"item_code": ["like", f"{DEMO_PREFIX}%"]},
		fields=["name", "variant_of"],
		order_by="variant_of desc",
	)
	for item in variants_first:
		try:
			frappe.delete_doc("Item", item.name, ignore_permissions=True)
		except frappe.LinkExistsError:
			frappe.db.set_value("Item", item.name, "disabled", 1)


def ensure_settings():
	settings = frappe.get_doc("Shop Settings")
	if not settings.company:
		settings.company = frappe.db.get_value("Company", {}, "name")
	if not settings.price_list:
		settings.price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	if not settings.default_warehouse:
		settings.default_warehouse = frappe.db.get_value(
			"Warehouse", {"company": settings.company, "warehouse_name": "Stores"}, "name"
		)
	if not settings.store_name:
		settings.store_name = "Demo Shop"
	settings.save(ignore_permissions=True)
	return settings


def create_attributes():
	attributes = {
		"Size": [("Small", "S"), ("Medium", "M"), ("Large", "L")],
		"Colour": [("Black", "BLA"), ("White", "WHI"), ("Charcoal", "CHL"), ("Olive", "OLV")],
	}
	for attribute, values in attributes.items():
		doc = get_or_new("Item Attribute", attribute, {"attribute_name": attribute})
		existing_values = {row.attribute_value for row in doc.item_attribute_values}
		existing_abbrs = {row.abbr for row in doc.item_attribute_values}
		for value, abbr in values:
			if value not in existing_values and abbr not in existing_abbrs:
				doc.append("item_attribute_values", {"attribute_value": value, "abbr": abbr})
		doc.save(ignore_permissions=True)


def create_items():
	for product in PRODUCTS:
		item_code = demo_item_code(product)
		if frappe.db.exists("Item", item_code):
			enable_item_tree(item_code)
			continue
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": product["name"],
				"item_group": ITEM_GROUP,
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"has_variants": 1 if product.get("variants") else 0,
				"description": product["short"],
			}
		)
		for attribute in product.get("variants", {}):
			item.append("attributes", {"attribute": attribute})
		item.insert(ignore_permissions=True)
		if product.get("variants"):
			create_variants(item, product)


def enable_item_tree(item_code):
	frappe.db.set_value("Item", item_code, "disabled", 0)
	for variant in frappe.get_all("Item", filters={"variant_of": item_code}, pluck="name"):
		frappe.db.set_value("Item", variant, "disabled", 0)


def create_variants(template, product):
	from erpnext.controllers.item_variant import create_variant

	for size in product["variants"]["Size"]:
		for colour in product["variants"]["Colour"]:
			variant = create_variant(template.name, {"Size": size, "Colour": colour})
			variant.insert(ignore_permissions=True)


def create_prices(price_list):
	for product in PRODUCTS:
		for item_code in sellable_item_codes(product):
			if frappe.db.exists("Item Price", {"item_code": item_code, "price_list": price_list}):
				continue
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": item_code,
					"price_list": price_list,
					"price_list_rate": product["price"],
				}
			).insert(ignore_permissions=True)


def create_stock(warehouse, company):
	items = []
	for product in PRODUCTS:
		for item_code in stockable_item_codes(product):
			if frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"):
				continue
			items.append(
				{
					"item_code": item_code,
					"qty": STOCK_QTY,
					"t_warehouse": warehouse,
					"basic_rate": product["price"] * 0.6,
					"allow_zero_valuation_rate": 1,
				}
			)
	if not items:
		return
	frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": company,
			"items": items,
		}
	).submit()


def create_collections():
	for collection in COLLECTIONS:
		if frappe.db.exists("Shop Collection", {"title": collection["title"]}):
			continue
		frappe.get_doc(
			{
				"doctype": "Shop Collection",
				"title": collection["title"],
				"description": collection["description"],
				"published": 1,
			}
		).insert(ignore_permissions=True)


def create_products():
	for ranking, product in enumerate(reversed(PRODUCTS)):
		if frappe.db.exists("Shop Product", {"item": demo_item_code(product)}):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Shop Product",
				"item": demo_item_code(product),
				"product_name": product["name"],
				"short_description": product["short"],
				"description": f"<p>{product['short']}</p>",
				"published": 1,
				"ranking": ranking,
			}
		)
		for title in product["collections"]:
			doc.append("collections", {"collection": collection_name(title)})
		doc.append("images", {"image": demo_image_url(product), "alt_text": product["name"]})
		doc.insert(ignore_permissions=True)


def demo_item_code(product):
	return f"{DEMO_PREFIX}{product['code']}"


def sellable_item_codes(product):
	if not product.get("variants"):
		return [demo_item_code(product)]
	return variant_codes(product)


def stockable_item_codes(product):
	if not product.get("variants"):
		return [demo_item_code(product)]
	return variant_codes(product)


def variant_codes(product):
	return frappe.get_all(
		"Item", filters={"variant_of": demo_item_code(product)}, pluck="name"
	)


def collection_name(title):
	return frappe.db.get_value("Shop Collection", {"title": title}, "name")


def demo_image_url(product):
	from frappe.website.utils import cleanup_page_name

	return f"/assets/shop/demo/{cleanup_page_name(product['name'])}.webp"


def get_or_new(doctype, name, defaults):
	if frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	return frappe.get_doc({"doctype": doctype, **defaults})
