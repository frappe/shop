import glob
import os
from unittest.mock import patch

import frappe
from builder.builder.doctype.builder_client_script.builder_client_script import BuilderClientScript
from frappe.tests import IntegrationTestCase

from shop.theme_generators import dot
from shop.theme_generators import frappe as frappe_theme
from shop.themes import stale_components


class TestThemeGenerators(IntegrationTestCase):
	def test_shipped_themes_match_their_components(self):
		root = frappe.get_app_path("shop", "builder_templates")
		components = {}
		for path in glob.glob(os.path.join(root, "*", "components", "*", "*.json")):
			fixture = frappe.parse_json(read(path))
			components[fixture["name"]] = fixture["block"]
		for path in glob.glob(os.path.join(root, "*", "pages", "*", "*.json")):
			with self.subTest(page=os.path.relpath(path, root)):
				blocks = frappe.parse_json(read(path))["blocks"]
				self.assertFalse(stale_components(blocks, components.get))

	def test_site_theme_in_each_generator(self):
		for generator, prefix in ((frappe_theme, "shop"), (dot, "dot")):
			with self.subTest(generator=generator.GROUP):
				self.assert_site_theme(generator, prefix)

	def assert_site_theme(self, generator, prefix):
		group = f"acme-{generator.GROUP}"
		frappe.get_doc(
			{
				"doctype": "Builder Component",
				"component_id": f"{group}-footer",
				"component_name": "Acme Footer",
				"block": frappe.as_json({"element": "footer", "children": []}),
			}
		).insert(ignore_permissions=True)
		site_theme = generator.Theme(
			group=group,
			title="Acme",
			skip_routes={"about"},
			component_ids={f"{prefix}-navbar": f"{group}-bar", f"{prefix}-footer": f"{group}-footer"},
			site_components={f"{group}-footer"},
			faqs=[("Do you ship to the moon?", "Not yet.")],
			listing_subtitle="Everything Acme makes.",
			product_description="below",
			extra_css=".acme-only { color: red; }",
		)

		# developer mode would export the test theme into the app's templates, and writing a script's
		# file commits, so neither happens here
		with (
			patch.dict(frappe.conf, {"developer_mode": 0}),
			patch(f"{BuilderClientScript.__module__}.BuilderClientScript.update_script_file"),
		):
			generator.generate(site_theme)
			saved = theme_records(group)
			generator.generate(site_theme)
		# generating again changes nothing, so the exported templates only change when the theme does
		self.assertEqual(theme_records(group), saved)

		pages = frappe.get_all(
			"Builder Page",
			filters={"template_group": group, "is_template": 1},
			fields=["route", "blocks"],
		)
		routes = {page.route: page for page in pages}
		for page in pages:
			self.assertFalse(stale_components(page.blocks), page.route)
		self.assertNotIn("about", routes)
		self.assertIn("checkout", routes)
		self.assertIn("Do you ship to the moon?", routes["faq"].blocks)
		self.assertIn("Everything Acme makes.", routes["products"].blocks)
		self.assertIn(f"{group}-bar", routes["home"].blocks)
		# the description has its own section under the images, and isn't in the buy box too
		names = block_names(frappe.parse_json(routes["product/:slug"].blocks))
		self.assertIn("Section · Product Description", names)
		self.assertEqual(names.count("Product Description"), 1)
		self.assertIn(f"{group}-footer", routes["home"].blocks)

		self.assertEqual(
			frappe.db.get_value("Builder Component", f"{group}-bar", "component_name"), "Acme Store Navbar"
		)
		self.assertEqual(
			frappe.db.get_value("Builder Component", f"{group}-footer", "component_name"), "Acme Footer"
		)
		self.assertIn(".acme-only", frappe.db.get_value("Builder Client Script", f"{group}-styles", "script"))
		# the generator's own components are left as they were
		self.assertEqual(
			frappe.db.get_value("Builder Component", f"{group}-hero", "component_name"), "Acme Store Hero"
		)
		self.assertIn(f"{group}-hero", routes["home"].blocks)
		self.assertNotIn(f'"{prefix}-hero"', routes["home"].blocks)
		self.assertEqual(generator.THEME.group, generator.GROUP)


def theme_records(group: str) -> dict:
	return {
		doctype: frappe.get_all(doctype, filters=filters, fields=["name", "modified"], order_by="name")
		for doctype, filters in (
			("Builder Page", {"template_group": group}),
			("Builder Component", {"name": ["like", f"{group}-%"]}),
			("Builder Client Script", {"name": ["like", f"{group}-%"]}),
		)
	}


def read(path: str) -> str:
	with open(path, encoding="utf-8") as f:
		return f.read()


def block_names(blocks) -> list[str]:
	names = []
	for node in blocks:
		if node.get("blockName"):
			names.append(node["blockName"])
		names += block_names(node.get("children") or [])
	return names
