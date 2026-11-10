import frappe
from frappe.tests import IntegrationTestCase

from shop.themes import apply_theme, ensure_default_theme, list_themes, reset_theme, stale_components


class TestThemes(IntegrationTestCase):
	def tearDown(self):
		settings = frappe.get_cached_doc("Shop Settings")
		if settings.active_theme:
			reset_theme(settings.active_theme)

	def test_ensure_default_theme_publishes_lowest_order_theme(self):
		ensure_default_theme()
		settings = frappe.get_doc("Shop Settings")
		self.assertEqual(settings.active_theme, "frappe")
		live_pages = frappe.get_all("Builder Page", filters={"is_template": 0}, fields=["route", "published"])
		self.assertEqual(len(live_pages), 16)
		routes = {page.route for page in live_pages}
		# the store's account, trade, quote and terms pages are part of the theme
		for route in ("account/signin", "account/register", "account/trade", "quote/:quote_id", "terms"):
			self.assertTrue(any(r.endswith(route) for r in routes), route)
		self.assertTrue(all(page.published for page in live_pages))

	def test_ensure_default_theme_is_a_noop_once_a_theme_is_active(self):
		ensure_default_theme()
		live_pages_before = frappe.get_all("Builder Page", filters={"is_template": 0}, pluck="name")

		ensure_default_theme()

		live_pages_after = frappe.get_all("Builder Page", filters={"is_template": 0}, pluck="name")
		self.assertEqual(sorted(live_pages_before), sorted(live_pages_after))

	def test_switching_back_keeps_edited_pages_and_rebuilds_out_of_date_ones(self):
		ensure_default_theme()
		home, products = live_page("home"), live_page("products")
		edited = frappe.parse_json(frappe.db.get_value("Builder Page", products, "blocks"))
		edited.append({"element": "div", "blockId": "merchant-note", "innerHTML": "Merchant note"})
		frappe.db.set_value("Builder Page", products, "blocks", frappe.as_json(edited))
		# a page kept from before the navbar changed lists a part the navbar no longer has
		blocks = frappe.db.get_value("Builder Page", home, "blocks")
		part = first_part(frappe.parse_json(blocks), "shop-navbar")
		frappe.db.set_value("Builder Page", home, "blocks", blocks.replace(part, "gone"))

		apply_theme("dot")
		apply_theme("frappe")

		self.assertIn("Merchant note", frappe.db.get_value("Builder Page", products, "blocks"))
		self.assertFalse(stale_components(frappe.db.get_value("Builder Page", home, "blocks")))
		self.assertTrue(frappe.db.get_value("Builder Page", home, "published"))

	def test_a_theme_out_of_step_with_its_components_is_not_applied(self):
		ensure_default_theme()
		template = frappe.db.get_value(
			"Builder Page",
			{"is_template": 1, "template_group": "dot", "route": "home"},
			["name", "blocks"],
			as_dict=True,
		)
		part = first_part(frappe.parse_json(template.blocks), "dot-navbar")
		frappe.db.set_value("Builder Page", template.name, "blocks", template.blocks.replace(part, "gone"))
		try:
			self.assertRaises(frappe.ValidationError, apply_theme, "dot")
		finally:
			frappe.db.set_value("Builder Page", template.name, "blocks", template.blocks)

		self.assertEqual(frappe.db.get_single_value("Shop Settings", "active_theme"), "frappe")
		self.assertTrue(frappe.db.get_value("Builder Page", live_page("home"), "published"))

	def test_themes_other_apps_register_can_be_chosen(self):
		ensure_default_theme()
		with self.patch_hooks({"shop_themes": [{"group": "dot", "title": "Dotted", "order": -1}]}):
			themes = {theme["group"]: theme for theme in list_themes()}
		self.assertEqual(themes["dot"]["title"], "Dot")  # Shop's own manifest wins
		with self.patch_hooks({"shop_themes": [{"group": "no-such-theme", "title": "Missing"}]}):
			groups = [theme["group"] for theme in list_themes()]
		self.assertNotIn("no-such-theme", groups)


def live_page(route: str) -> str:
	settings = frappe.get_doc("Shop Settings")
	return next(
		row.page
		for row in settings.theme_pages
		if row.template_group == settings.active_theme
		and frappe.db.get_value("Builder Page", row.source_page, "route") == route
	)


def first_part(blocks, component: str) -> str:
	for node in blocks:
		if node.get("isChildOfComponent") == component:
			return node["referenceBlockId"]
		found = first_part(node.get("children") or [], component)
		if found:
			return found
