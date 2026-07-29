import frappe
from frappe import _
from frappe.utils import now

HOME_ROUTE = "home"


@frappe.whitelist()
def list_themes() -> list[dict]:
	ensure_manager()
	from builder.template_sync import get_all_group_manifests

	settings = frappe.get_cached_doc("Shop Settings")
	themes = [
		{
			"group": group,
			"title": manifest.get("title") or group.title(),
			"description": manifest.get("description"),
			"preview": manifest.get("preview"),
			"order": manifest.get("order", 0),
			"pages": manifest.get("pages", []),
			"active": group == settings.active_theme,
		}
		for group, manifest in get_all_group_manifests(app="shop").items()
	]
	return sorted(themes, key=lambda theme: theme["order"])


@frappe.whitelist(methods=["POST"])
def apply_theme(group: str) -> None:
	ensure_manager()
	templates = template_pages(group)
	if not templates:
		frappe.throw(_("Theme {0} has no pages").format(group))
	settings = frappe.get_doc("Shop Settings")
	unpublish_active_theme(settings)
	tracked = {
		row.source_page: row
		for row in settings.theme_pages
		if row.template_group == group and frappe.db.exists("Builder Page", row.page)
	}
	for template in templates:
		if template in tracked:
			republish(tracked[template].page)
		else:
			clone_template(template, group, settings)
	settings.active_theme = group
	settings.save(ignore_permissions=True)
	set_home_page()


def template_pages(group: str) -> list[str]:
	return frappe.get_all(
		"Builder Page", filters={"is_template": 1, "template_group": group}, pluck="name"
	)


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
	page.save(ignore_permissions=True)


def clone_template(template_name: str, group: str, settings):
	template = frappe.get_doc("Builder Page", template_name)
	clone = frappe.copy_doc(template)
	clone.page_name = live_page_name(template.page_name)
	clone.is_template = 0
	clone.template_group = None
	clone.is_standard = 0
	clone.app = None
	clone.route = template.route
	clone.draft_blocks = template.blocks
	clone.published = 1
	clone.published_at = now()
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
	frappe.db.set_value("Builder Settings", None, "home_page", HOME_ROUTE)
	frappe.cache.delete_key("home_page")


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


def ensure_manager():
	frappe.only_for(("Shop Manager", "System Manager"))
