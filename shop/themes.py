import json
import os

import frappe
from frappe import _
from frappe.utils import now

from shop.routes import (
	HOME_ROUTE,
	get_prefix,
	normalize_prefix,
	page_route,
	rewrite_blocks,
	with_prefix_script,
)

LIVE_FOLDER = "Shop"


@frappe.whitelist()
def list_themes() -> list[dict]:
	ensure_manager()
	settings = frappe.get_cached_doc("Shop Settings")
	themes = [
		{
			"group": group,
			"title": manifest.get("title") or group.title(),
			"description": manifest.get("description"),
			"preview": manifest.get("preview") or home_preview(group),
			"order": manifest.get("order", 0),
			"pages": manifest.get("pages", []),
			"active": group == settings.active_theme,
		}
		for group, manifest in theme_manifests().items()
		if template_pages(group)
	]
	return sorted(themes, key=lambda theme: theme["order"])


def theme_manifests() -> dict[str, dict]:
	"""Shop's themes, then those other apps generate into the site and register in the
	`shop_themes` hook as {"group", "title", "description", "order"}."""
	from builder.template_sync import get_all_group_manifests

	manifests = get_all_group_manifests(app="shop")
	for theme in frappe.get_hooks("shop_themes") or []:
		manifests.setdefault(theme["group"], theme)
	return manifests


def home_preview(group: str) -> str | None:
	return frappe.db.get_value(
		"Builder Page",
		{"is_template": 1, "template_group": group, "route": HOME_ROUTE},
		"preview",
	)


def ensure_default_theme():
	"""Apply the lowest-order theme so a fresh install has a live storefront.

	Runs on every install/migrate but is a no-op once any theme is active.
	"""
	settings = frappe.get_cached_doc("Shop Settings")
	if settings.active_theme:
		return
	from builder.template_sync import get_all_group_manifests

	manifests = get_all_group_manifests(app="shop")
	if not manifests:
		return
	default_group = min(manifests, key=lambda group: manifests[group].get("order", 0))
	apply_theme(default_group)


@frappe.whitelist(methods=["POST"])
def apply_theme(group: str) -> None:
	ensure_manager()
	templates = template_pages(group)
	if not templates:
		frappe.throw(_("Theme {0} has no pages").format(group))
	if any(stale_components(page_blocks(template)) for template in templates):
		frappe.throw(
			_(
				"Theme {0} doesn't match its components (navbar, footer and the like). Update the site, then try again."
			).format(group)
		)
	settings = frappe.get_doc("Shop Settings")
	unpublish_active_theme(settings)
	tracked = {
		row.source_page: row
		for row in settings.theme_pages
		if row.template_group == group and frappe.db.exists("Builder Page", row.page)
	}
	prefix = get_prefix()
	for template in templates:
		if template not in tracked:
			clone_template(template, group, settings)
		elif stale_components(page_blocks(tracked[template].page)):
			# its navbar, footer or drawer has changed since the page was kept, and Builder would show them empty
			update_from_template(tracked[template].page, template, prefix)
		else:
			republish(tracked[template].page)
	settings.active_theme = group
	settings.applied_route_prefix = prefix
	settings.save(ignore_permissions=True)
	relink_components(prefix)
	set_home_page()
	clear_render_cache()


def page_blocks(name: str):
	return frappe.db.get_value("Builder Page", name, "blocks")


def stale_components(blocks, component_block=None) -> set[str]:
	"""Components a page lists out of step with the component itself: parts it no longer has,
	or has gained since. Builder renders only the parts a page lists, so these come out empty
	or incomplete."""
	component_block = component_block or (
		lambda name: frappe.db.get_value("Builder Component", name, "block")
	)
	parts = {}
	stale = set()

	def walk(node):
		name = node.get("extendedFromComponent")
		if name:
			if name not in parts:
				block = component_block(name)
				parts[name] = descendant_ids(frappe.parse_json(block)) if block else None
			if parts[name] is None or listed_parts(node, name) != parts[name]:
				stale.add(name)
		for child in node.get("children") or []:
			walk(child)

	for node in frappe.parse_json(blocks) or []:
		walk(node)
	return stale


def descendant_ids(block: dict) -> set[str]:
	ids = set()
	for child in block.get("children") or []:
		ids.add(child.get("blockId"))
		ids |= descendant_ids(child)
	return ids


def listed_parts(block: dict, component: str) -> set[str]:
	ids = set()
	for child in block.get("children") or []:
		if child.get("isChildOfComponent") == component:
			ids.add(child.get("referenceBlockId"))
			ids |= listed_parts(child, component)
	return ids


def clear_render_cache():
	"""Builder resolves a page's components through the cached Builder Component doc.

	A stale entry no longer matches the block ids the pages reference, so navbars,
	footers and drawers render as empty divs. clear-website-cache does not touch it.
	"""
	frappe.clear_cache()


def template_pages(group: str) -> list[str]:
	return frappe.get_all("Builder Page", filters={"is_template": 1, "template_group": group}, pluck="name")


def unpublish_active_theme(settings=None):
	settings = settings or frappe.get_doc("Shop Settings")
	for row in settings.theme_pages:
		if row.template_group != settings.active_theme:
			continue
		if not frappe.db.exists("Builder Page", row.page):
			continue
		page = frappe.get_doc("Builder Page", row.page)
		if page.published:
			page.published = 0
			page.save(ignore_permissions=True)


def republish(name: str):
	page = frappe.get_doc("Builder Page", name)
	page.published = 1
	page.published_at = now()
	page.project_folder = ensure_folder(LIVE_FOLDER)
	page.save(ignore_permissions=True)


def update_from_template(name: str, template_name: str, prefix: str):
	template = frappe.get_doc("Builder Page", template_name)
	page = frappe.get_doc("Builder Page", name)
	page.route = page_route(template.route, prefix)
	page.blocks = rewrite_blocks(template.blocks, prefix)
	page.draft_blocks = page.blocks
	page.page_data_script = template.page_data_script
	page.page_title = template.page_title
	page.authenticated_access = template.authenticated_access
	page.disable_indexing = template.disable_indexing
	page.meta_description = template.meta_description
	page.body_html = with_prefix_script(template.body_html, prefix)
	page.client_scripts = []
	for script in template.client_scripts:
		page.append("client_scripts", {"builder_script": script.builder_script})
	page.published = 1
	page.published_at = page.published_at or now()
	page.project_folder = ensure_folder(LIVE_FOLDER)
	page.save(ignore_permissions=True)


def clone_template(template_name: str, group: str, settings):
	template = frappe.get_doc("Builder Page", template_name)
	clone = frappe.copy_doc(template)
	clone.page_name = live_page_name(template.page_name)
	clone.is_template = 0
	clone.template_group = None
	clone.is_standard = 0
	clone.app = None
	prefix = get_prefix()
	clone.route = page_route(template.route, prefix)
	clone.blocks = rewrite_blocks(template.blocks, prefix)
	clone.draft_blocks = clone.blocks
	clone.body_html = with_prefix_script(template.body_html, prefix)
	clone.published = 1
	clone.published_at = now()
	clone.project_folder = ensure_folder(LIVE_FOLDER)
	clone.insert(ignore_permissions=True)
	settings.append(
		"theme_pages",
		{
			"template_group": group,
			"source_page": template_name,
			"page": clone.name,
			"route": clone.route,
		},
	)


def live_page_name(page_name: str) -> str:
	name = f"{page_name}-live"
	if frappe.db.exists("Builder Page", name):
		name = f"{name}-{frappe.generate_hash(length=6)}"
	return name


def set_home_page():
	"""Make the storefront home the site home page, unless it is served under a route prefix.

	With a prefix the site keeps its own home page and the storefront home is /<prefix>.
	"""
	if get_prefix():
		return
	frappe.db.set_value("Builder Settings", None, "home_page", HOME_ROUTE)
	frappe.cache.delete_key("home_page")


def refresh_theme(group: str):
	"""Push updated template blocks into the live clones without unpublishing anything.

	reset + apply deletes the live pages first, which briefly serves shoppers a broken
	site. This updates each page in place and only clones pages that are new.
	"""
	ensure_manager()
	settings = frappe.get_doc("Shop Settings")
	tracked = {
		row.source_page: row
		for row in settings.theme_pages
		if row.template_group == group and frappe.db.exists("Builder Page", row.page)
	}
	prefix = get_prefix()
	for template_name in template_pages(group):
		if template_name in tracked:
			update_from_template(tracked[template_name].page, template_name, prefix)
		else:
			clone_template(template_name, group, settings)
	settings.applied_route_prefix = prefix
	settings.save(ignore_permissions=True)
	relink_components(prefix)
	set_home_page()
	clear_render_cache()


def apply_route_prefix():
	"""Move the live storefront to the current route prefix. Safe to run repeatedly.

	Re-routes every live theme page, rewrites storefront links in pages (keeping merchant
	edits) and in the theme components, and sets or leaves the site home page. Runs when
	Shop Settings > Route Prefix changes and after every migrate, because migrate
	re-imports theme components with root links.
	"""
	settings = frappe.get_doc("Shop Settings")
	prefix = get_prefix()
	old_prefix = normalize_prefix(settings.applied_route_prefix)
	for row in settings.theme_pages:
		if not frappe.db.exists("Builder Page", row.page):
			continue
		page = frappe.get_doc("Builder Page", row.page)
		before = (page.route, page.blocks, page.draft_blocks, page.body_html)
		template_route = frappe.db.get_value("Builder Page", row.source_page, "route")
		if template_route:
			page.route = page_route(template_route, prefix)
		page.blocks = rewrite_blocks(page.blocks, prefix, old_prefix)
		page.draft_blocks = rewrite_blocks(page.draft_blocks, prefix, old_prefix)
		page.body_html = with_prefix_script(page.body_html, prefix)
		if (page.route, page.blocks, page.draft_blocks, page.body_html) != before:
			page.save(ignore_permissions=True)
		if row.route != page.route:
			frappe.db.set_value("Shop Theme Page", row.name, "route", page.route, update_modified=False)
	relink_components(prefix, old_prefix)
	frappe.db.set_single_value("Shop Settings", "applied_route_prefix", prefix)
	if not prefix and old_prefix and settings.active_theme:
		set_home_page()
	clear_render_cache()


def theme_component_names() -> list[str]:
	"""Builder Components shipped in this app's theme folders."""
	root = frappe.get_app_path("shop", "builder_templates")
	names = []
	if not os.path.isdir(root):
		return names
	for group in os.listdir(root):
		components = os.path.join(root, group, "components")
		if not os.path.isdir(components):
			continue
		for folder in os.listdir(components):
			path = os.path.join(components, folder, f"{folder}.json")
			if os.path.isfile(path):
				with open(path, encoding="utf-8") as f:
					names.append(json.load(f).get("name") or folder)
	return names


def relink_components(prefix: str, old_prefix: str = ""):
	"""Rewrite storefront links in the theme components (navbar, footer, cart drawer)."""
	from shop.routes import theme_components

	for name in sorted(theme_components()):
		if not frappe.db.exists("Builder Component", name):
			continue
		block = frappe.db.get_value("Builder Component", name, "block")
		relinked = rewrite_blocks(block, prefix, old_prefix)
		if relinked != block:
			frappe.db.set_value("Builder Component", name, "block", relinked, update_modified=False)


def reset_theme(group: str):
	"""Discard materialized pages for a group so the next apply re-clones from templates."""
	ensure_manager()
	settings = frappe.get_doc("Shop Settings")
	keep = []
	for row in settings.theme_pages:
		if row.template_group != group:
			keep.append(row)
		elif frappe.db.exists("Builder Page", row.page):
			frappe.delete_doc("Builder Page", row.page, ignore_permissions=True, force=True)
	settings.theme_pages = keep
	if settings.active_theme == group:
		settings.active_theme = None
	settings.save(ignore_permissions=True)


def ensure_folder(name: str) -> str:
	if not frappe.db.exists("Builder Project Folder", name):
		frappe.get_doc({"doctype": "Builder Project Folder", "folder_name": name}).insert(
			ignore_permissions=True
		)
	return name


def organize_template_folders():
	"""Group synced template pages into a folder per theme."""
	from builder.template_sync import get_all_group_manifests

	for group, manifest in get_all_group_manifests(app="shop").items():
		folder = ensure_folder(manifest.get("title") or group.title())
		frappe.db.set_value(
			"Builder Page",
			{"is_template": 1, "template_group": group},
			"project_folder",
			folder,
			update_modified=False,
		)
	settings = frappe.get_cached_doc("Shop Settings")
	clones = [row.page for row in settings.theme_pages if frappe.db.exists("Builder Page", row.page)]
	if clones:
		frappe.db.set_value(
			"Builder Page",
			{"name": ["in", clones]},
			"project_folder",
			ensure_folder(LIVE_FOLDER),
			update_modified=False,
		)


def ensure_manager():
	frappe.only_for(("Shop Manager", "System Manager"))
