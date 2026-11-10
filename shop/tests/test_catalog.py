from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from shop.storefront import catalog, product


class TestCatalog(IntegrationTestCase):
	def test_listing_returns_published_products(self):
		result = catalog.get_products()
		self.assertEqual(result["total"], frappe.db.count("Shop Product", {"published": 1}))
		self.assertTrue(result["products"])
		first = result["products"][0]
		self.assertIn("slug", first)
		self.assertIsNotNone(first.formatted_price)
		self.assertTrue(first.in_stock)

	def test_collection_filter(self):
		result = catalog.get_products(collection="apparel")
		slugs = {p.slug for p in result["products"]}
		self.assertIn("crew-neck-t-shirt", slugs)
		self.assertNotIn("ceramic-mug", slugs)

	def test_search_needs_every_word_and_forgives_a_typo(self):
		frappe.cache.delete_value("shop:search_words")
		names = lambda result: [p.product_name for p in result["products"]]  # noqa: E731
		self.assertIn("Ceramic Mug", names(catalog.get_products(search="ceramic mug")))
		self.assertNotIn("Ceramic Mug", names(catalog.get_products(search="ceramic zebraquartz")))
		typo = catalog.get_products(search="ceramik mugg")
		self.assertIn("Ceramic Mug", names(typo))
		self.assertEqual(typo["searched_as"], "ceramic mug")
		self.assertIsNone(catalog.get_products(search="mug")["searched_as"])

	def test_search_suggestions_list_a_few_products(self):
		self.assertEqual(catalog.search_suggestions("m")["products"], [])
		found = catalog.search_suggestions("mug")
		self.assertIn("Ceramic Mug", [row["title"] for row in found["products"]])
		self.assertLessEqual(len(found["products"]), 6)
		self.assertTrue(all(row["route"] for row in found["products"]))

	def test_search(self):
		result = catalog.get_products(search="mug")
		self.assertEqual(result["total"], 1)
		self.assertEqual(result["products"][0].slug, "ceramic-mug")

	def test_collections_have_counts(self):
		collections = catalog.get_collections()
		self.assertEqual(len(collections), 4)
		self.assertTrue(all(c.product_count > 0 for c in collections))

	def test_a_collection_inside_another(self):
		from shop.storefront import page_data

		apparel = frappe.get_doc("Shop Collection", {"slug": "apparel"})
		inner = frappe.get_doc(
			{
				"doctype": "Shop Collection",
				"title": "Tees (test)",
				"published": 1,
				"parent_collection": apparel.name,
			}
		).insert(ignore_permissions=True)
		mug = frappe.get_doc("Shop Product", {"slug": "ceramic-mug"})
		mug.append("collections", {"collection": inner.name})
		mug.save(ignore_permissions=True)

		def remove():
			frappe.db.delete("Shop Product Collection", {"collection": inner.name})
			frappe.delete_doc("Shop Collection", inner.name, force=True)

		self.addCleanup(remove)

		# the top collections stay the same; the new one is inside Apparel
		self.assertNotIn(inner.name, [c.name for c in catalog.get_collections()])
		self.assertEqual([c.name for c in catalog.get_collections(parent=apparel.name)], [inner.name])
		# Apparel lists the products of the collections inside it
		self.assertIn("ceramic-mug", {p.slug for p in catalog.get_products(collection="apparel")["products"]})
		nested = catalog.get_collections(nested=True)
		names = [c.name for c in nested]
		self.assertEqual(names.index(inner.name), names.index(apparel.name) + 1)

		with patch.object(frappe.local, "form_dict", frappe._dict(slug=inner.slug)):
			data = page_data.collection_page()
		self.assertEqual([crumb["title"] for crumb in data["breadcrumbs"]], [apparel.title])
		with patch.object(frappe.local, "form_dict", frappe._dict(slug="apparel")):
			self.assertEqual([c.name for c in page_data.collection_page()["sub_collections"]], [inner.name])

		# a collection can't end up inside itself
		apparel.parent_collection = inner.name
		self.assertRaises(frappe.ValidationError, apparel.save)

	def test_product_detail_simple(self):
		detail = product.get_product("ceramic-mug")
		self.assertEqual(detail["item"], "SHOP-DEMO-003")
		self.assertTrue(detail["in_stock"])
		self.assertTrue(detail["images"])
		self.assertFalse(detail["has_variants"])

	def test_product_detail_variants(self):
		detail = product.get_product("crew-neck-t-shirt")
		self.assertTrue(detail["has_variants"])
		self.assertEqual(len(detail["variants"]), 6)
		attributes = {a["attribute"]: a["values"] for a in detail["attributes"]}
		self.assertEqual(attributes["Size"], ["Small", "Medium", "Large"])
		self.assertIn(detail["default_item_code"], [v["item_code"] for v in detail["variants"]])

	def test_unpublished_product_hidden(self):
		with self.assertRaises(frappe.DoesNotExistError):
			product.get_product("does-not-exist")

	def test_listing_pages_keep_the_filters(self):
		from shop.storefront import page_data

		with patch.object(page_data, "PER_PAGE", (2, 4)):
			frappe.form_dict.update({"sort": "name_asc", "page": 1})
			first = page_data.listing()
			self.assertIsNone(first["pager"]["prev_url"])
			self.assertIn("page=2", first["pager"]["next_url"])
			self.assertIn("sort=name_asc", first["pager"]["next_url"])
			frappe.form_dict.update({"page": 2})
			second = page_data.listing()
			self.assertNotIn("page=", second["pager"]["prev_url"])
		frappe.form_dict.clear()

	def narrowable(self):
		"""Brands and specifications on three products, put back afterwards."""
		for brand in ("_Test Brand North", "_Test Brand South"):
			if not frappe.db.exists("Brand", brand):
				frappe.get_doc({"doctype": "Brand", "brand": brand}).insert(ignore_permissions=True)
		if not frappe.db.exists("Shop Specification", "_Test Capacity"):
			frappe.get_doc(
				{"doctype": "Shop Specification", "specification_name": "_Test Capacity", "unit": "ml"}
			).insert(ignore_permissions=True)
		for slug, brand, capacity in (
			("ceramic-mug", "_Test Brand North", "350"),
			("insulated-water-bottle", "_Test Brand North", "750"),
			("canvas-tote-bag", "_Test Brand South", None),
		):
			doc = frappe.get_doc("Shop Product", slug)
			item_brand = frappe.db.get_value("Item", doc.item, "brand")
			self.addCleanup(frappe.db.set_value, "Item", doc.item, "brand", item_brand)
			frappe.db.set_value("Item", doc.item, "brand", brand)
			if capacity:
				doc.append("specifications", {"specification": "_Test Capacity", "value": capacity})
				doc.save(ignore_permissions=True)
				self.addCleanup(frappe.db.delete, "Shop Product Specification", {"parent": slug})

	def test_products_are_narrowed_by_brand_specification_and_option(self):
		self.narrowable()
		everything = catalog.get_products()
		narrowings = {n["key"]: n for n in everything["narrowings"]}
		self.assertEqual(
			{v["value"]: v["count"] for v in narrowings["brand"]["values"]},
			{"_Test Brand North": 2, "_Test Brand South": 1},
		)
		self.assertEqual(
			[v["label"] for v in narrowings["spec:_Test Capacity"]["values"]], ["350 ml", "750 ml"]
		)
		self.assertIn("option:Size", narrowings)

		north = catalog.get_products(chosen={"brand": ["_Test Brand North"]})
		self.assertEqual({p.slug for p in north["products"]}, {"ceramic-mug", "insulated-water-bottle"})
		# a narrowing's own values still count as if it weren't chosen; the others count what is left
		narrowings = {n["key"]: n for n in north["narrowings"]}
		self.assertEqual(len(narrowings["brand"]["values"]), 2)
		self.assertEqual(sum(v["count"] for v in narrowings["spec:_Test Capacity"]["values"]), 2)

		both = catalog.get_products(chosen={"brand": ["_Test Brand North"], "spec:_Test Capacity": ["750"]})
		self.assertEqual([p.slug for p in both["products"]], ["insulated-water-bottle"])
		small = catalog.get_products(chosen={"option:Size": ["Small"]})
		self.assertTrue(small["products"])
		self.assertTrue(all(p.has_variants for p in small["products"]))

		# a specification that isn't a filter isn't offered
		frappe.db.set_value("Shop Specification", "_Test Capacity", "use_as_filter", 0)
		self.addCleanup(frappe.db.set_value, "Shop Specification", "_Test Capacity", "use_as_filter", 1)
		self.assertNotIn("spec:_Test Capacity", {n["key"] for n in catalog.get_products()["narrowings"]})

	def test_a_collection_can_include_an_item_group(self):
		collection = frappe.get_doc(
			{
				"doctype": "Shop Collection",
				"title": "_Test Everything",
				"slug": "test-everything",
				"published": 1,
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Shop Collection", collection.name, force=True)
		self.assertEqual(catalog.get_products(collection="test-everything")["total"], 0)
		collection.db_set("item_group", "All Item Groups")
		total = catalog.get_products(collection="test-everything")["total"]
		self.assertEqual(total, frappe.db.count("Shop Product", {"published": 1}))
		self.assertEqual(
			next(c for c in catalog.get_collections() if c.slug == "test-everything").product_count, total
		)

	def test_the_listing_page_has_filters_with_links_that_keep_the_page(self):
		from werkzeug.test import EnvironBuilder
		from werkzeug.wrappers import Request

		from shop.storefront import page_data

		self.narrowable()
		frappe.local.request = Request(EnvironBuilder(path="/store/collection/apparel").get_environ())
		frappe.form_dict.clear()
		frappe.form_dict.update({"slug": "apparel", "brand": "_Test Brand North", "view": "list"})
		try:
			data = page_data.collection_page()
		finally:
			frappe.form_dict.clear()
		self.assertEqual(data["title"], "Apparel")
		self.assertEqual(data["view"], "list")
		self.assertEqual(data["applied"][0]["label"], "Brand: _Test Brand North")
		self.assertTrue(all(a["url"].startswith("/store/collection/apparel") for a in data["applied"]))
		labels = [group["label"] for group in data["filter_groups"]]
		self.assertIn("Availability", labels)
		self.assertIn("Brand", labels)
		self.assertTrue(data["sort_options"] and data["per_page_options"])

	def test_staff_give_a_product_its_brand_and_specifications(self):
		from shop.api import products

		mug = frappe.get_doc("Shop Product", "ceramic-mug")
		brand = frappe.db.get_value("Item", mug.item, "brand")
		self.addCleanup(frappe.db.set_value, "Item", mug.item, "brand", brand)
		self.addCleanup(frappe.db.delete, "Shop Product Specification", {"parent": "ceramic-mug"})
		for name in ("_Test Volume", "_Test Finish", "_Test Glaze"):
			self.addCleanup(frappe.db.delete, "Shop Specification", {"name": name})
		current = products.get_product("ceramic-mug")
		saved = products.save_product(
			{
				# the whole form, as the product editor sends it
				**{
					key: current[key]
					for key in (
						"name",
						"product_name",
						"slug",
						"short_description",
						"description",
						"highlights",
						"ranking",
						"published",
						"collections",
						"item_group",
					)
				},
				"images": [row["image"] for row in current["images"]],
				"brand": "_Test Brand Kiln",
				"specifications": [
					{"specification": "_Test Volume", "value": " 350 "},
					{"specification": "_Test Finish", "value": "Gloss"},
					{"specification": "_Test Empty", "value": ""},
				],
			}
		)
		self.addCleanup(frappe.db.delete, "Brand", {"name": "_Test Brand Kiln"})
		self.assertEqual(saved["brand"], "_Test Brand Kiln")
		self.assertEqual(
			saved["specifications"],
			[
				{"specification": "_Test Volume", "value": "350"},
				{"specification": "_Test Finish", "value": "Gloss"},
			],
		)
		self.assertFalse(frappe.db.exists("Shop Specification", "_Test Empty"))

		products.save_specification("_Test Volume", unit="ml", name="_Test Volume")
		page = product.get_product("ceramic-mug")
		self.assertEqual(page["specifications"][0], {"label": "_Test Volume", "value": "350 ml"})

		# renamed, the products keep their values; one in use isn't removed
		listed = products.save_specification("_Test Glaze", name="_Test Finish", use_as_filter=0)
		self.assertIn("_Test Glaze", [row.name for row in listed])
		self.assertEqual(
			frappe.db.get_value(
				"Shop Product Specification", {"parent": "ceramic-mug", "value": "Gloss"}, "specification"
			),
			"_Test Glaze",
		)
		with self.assertRaises(frappe.ValidationError):
			products.delete_specification("_Test Glaze")

	def test_a_collection_is_saved_with_the_item_group_it_includes(self):
		from shop.api import products

		products.save_collection({"title": "_Test Grouped", "item_group": "All Item Groups", "published": 1})
		name = frappe.db.get_value("Shop Collection", {"title": "_Test Grouped"})
		self.addCleanup(frappe.delete_doc, "Shop Collection", name, force=True)
		row = next(c for c in products.get_collections() if c.name == name)
		self.assertEqual(row.item_group, "All Item Groups")
		self.assertEqual(row.product_count, frappe.db.count("Shop Product"))
