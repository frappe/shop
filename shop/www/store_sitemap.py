"""The store's products and collections for search engines. The site's sitemap.xml lists its pages
but not those made from one page per product (product/:slug), so robots.txt points to this too."""

from urllib.parse import quote

import frappe
from frappe.utils import get_url

from shop.routes import store_url

no_cache = 1


def get_context(context):
	from shop.storefront import catalog

	if not frappe.db.get_single_value("Shop Settings", "active_theme"):
		return {"links": []}
	links = [
		{"loc": get_url(store_url(f"product/{quote(row.slug)}")), "lastmod": f"{row.modified:%Y-%m-%d}"}
		for row in frappe.get_all("Shop Product", filters={"published": 1}, fields=["slug", "modified"])
		if row.slug
	]
	collections = frappe.get_all(
		"Shop Collection",
		filters={"name": ["in", list(catalog.published_collections())] or [""]},
		fields=["slug", "modified"],
	)
	links += [
		{"loc": get_url(store_url(f"collection/{quote(row.slug)}")), "lastmod": f"{row.modified:%Y-%m-%d}"}
		for row in collections
		if row.slug
	]
	return {"links": links}
