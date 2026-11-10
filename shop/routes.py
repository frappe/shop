"""Storefront URLs under an optional route prefix.

By default the storefront is served from the site root (/products, /cart, and the
theme's home page becomes the site home page). Sites that already have a website,
for example one built with Frappe Builder, can serve the storefront under a prefix
instead: with the prefix "store" the pages live at /store, /store/products,
/store/cart and so on, and the site's own home page is left alone.

The prefix comes from Shop Settings > Route Prefix, falling back to the
`shop_route_prefix` site config key so it can be set before Shop is installed.
"""

import json
import re
from urllib.parse import quote

import frappe

HOME_ROUTE = "home"

# First path segment of every storefront route the themes link to.
STOREFRONT_SEGMENTS = frozenset(
	{
		"products",
		"product",
		"collection",
		"cart",
		"checkout",
		"account",
		"order-confirmation",
		"faq",
		"about",
		"contact",
		"terms",
		"quote",
		HOME_ROUTE,
	}
)

# First path segments Frappe answers itself, before website routing, or uses for the Desk.
FRAPPE_SEGMENTS = frozenset({"api", "app", "assets", "files", "private", "backups", "desk", "login"})

LINK_ATTRIBUTES = ("href", "action")
HTML_LINK = re.compile(r"""(\b(?:href|action)\s*=\s*)(["'])(/[^"']*)\2""")


def normalize_prefix(value: str | None) -> str:
	"""'/Store/' -> 'store'. Only lowercase letters, digits, '-', '_' and '/' are kept."""
	value = (value or "").strip().strip("/").lower()
	value = re.sub(r"[^a-z0-9/_-]", "-", value)
	return re.sub(r"/{2,}", "/", value).strip("/")


def get_prefix() -> str:
	prefix = None
	if "shop" in frappe.get_installed_apps():
		prefix = frappe.get_cached_doc("Shop Settings").get("route_prefix")
	return normalize_prefix(prefix or frappe.conf.get("shop_route_prefix"))


def store_url(path: str = "", prefix: str | None = None) -> str:
	"""URL of a storefront page: store_url("cart") -> "/store/cart" (or "/cart" without a prefix).

	Query strings are kept: store_url("products?search=mug").
	"""
	prefix = get_prefix() if prefix is None else normalize_prefix(prefix)
	path = (path or "").lstrip("/")
	if path == HOME_ROUTE:
		path = ""
	base = f"/{prefix}" if prefix else ""
	if not path:
		return base or "/"
	return f"{base}/{path}"


def signin_url(redirect_to: str | None = None) -> str:
	"""The store's sign-in page, coming back to redirect_to."""
	url = store_url("account/signin")
	return f"{url}?redirect-to={quote(redirect_to)}" if redirect_to else url


def page_route(template_route: str, prefix: str | None = None) -> str:
	"""Route for a live theme page cloned from a template: 'cart' -> 'store/cart', 'home' -> 'store'."""
	prefix = get_prefix() if prefix is None else normalize_prefix(prefix)
	route = (template_route or "").strip("/")
	if not prefix:
		return route
	if route == HOME_ROUTE:
		return prefix
	return f"{prefix}/{route}"


def rewrite_url(url: str, prefix: str, old_prefix: str = "") -> str:
	"""Point a storefront link at prefix.

	Accepts links at the site root ("/cart") and links under old_prefix ("/old/cart"), so it
	is safe to run again on content that was already rewritten, or on templates that were
	re-imported with root links. Links outside the storefront (/login, /app, /assets/...,
	external URLs) are unchanged.
	"""
	if not isinstance(url, str) or not url.startswith("/") or url.startswith("//"):
		return url
	prefix, old_prefix = normalize_prefix(prefix), normalize_prefix(old_prefix)
	path = url
	# the longer prefix first: of "store/shop" and "store", "store" alone would match both
	for known in sorted({old_prefix, prefix} - {""}, key=len, reverse=True):
		if path == f"/{known}" or path.startswith((f"/{known}/", f"/{known}?", f"/{known}#")):
			path = path[len(known) + 1 :] or "/"
			if not path.startswith("/"):
				path = "/" + path
			break
	if path != "/" and not path.startswith(("/?", "/#")):
		segment = re.split(r"[/?#]", path[1:], maxsplit=1)[0]
		if segment not in STOREFRONT_SEGMENTS:
			return url
		if segment == HOME_ROUTE:  # "/home" is the storefront root
			path = "/" + path[len("/home") :].lstrip("/")
	if not prefix:
		return path
	if path == "/":
		return f"/{prefix}"
	if path.startswith(("/?", "/#")):
		return f"/{prefix}{path[1:]}"
	return f"/{prefix}{path}"


def rewrite_html(html: str | None, prefix: str, old_prefix: str = "") -> str | None:
	if not html:
		return html
	return HTML_LINK.sub(
		lambda m: f"{m.group(1)}{m.group(2)}{rewrite_url(m.group(3), prefix, old_prefix)}{m.group(2)}",
		html,
	)


def theme_components() -> set[str]:
	"""Builder Components whose links belong to the storefront: Shop's theme components plus
	those other apps register in the `shop_theme_components` hook. Every other component (a
	site's own header or footer, say) keeps its links as they are."""
	from shop.themes import theme_component_names

	return set(theme_component_names()) | set(frappe.get_hooks("shop_theme_components") or [])


def foreign_component(node: dict, ours: set[str]) -> bool:
	component = node.get("extendedFromComponent") or node.get("isChildOfComponent")
	return bool(component) and component not in ours


def rewrite_blocks(blocks, prefix: str, old_prefix: str = ""):
	"""Rewrite storefront links in a Builder block tree (JSON string, list or dict).

	Links inside components that are not storefront components are left alone.
	Returns the same type it was given; a JSON string comes back untouched (same object)
	when no link changed, so callers can compare before saving.
	"""
	if not blocks:
		return blocks
	as_string = isinstance(blocks, str)
	tree = json.loads(blocks) if as_string else blocks
	changed = False
	ours = theme_components()

	def walk(node):
		nonlocal changed
		if isinstance(node, list):
			for item in node:
				walk(item)
		elif isinstance(node, dict):
			if foreign_component(node, ours):
				return
			attributes = node.get("attributes")
			if isinstance(attributes, dict):
				for key in LINK_ATTRIBUTES:
					value = attributes.get(key)
					if isinstance(value, str):
						new = rewrite_url(value, prefix, old_prefix)
						if new != value:
							attributes[key], changed = new, True
			if isinstance(node.get("innerHTML"), str):
				new = rewrite_html(node["innerHTML"], prefix, old_prefix)
				if new != node["innerHTML"]:
					node["innerHTML"], changed = new, True
			for value in node.values():
				if isinstance(value, (list, dict)):
					walk(value)

	walk(tree)
	if as_string:
		return json.dumps(tree) if changed else blocks
	return tree


def prefix_script(prefix: str) -> str:
	"""Snippet that tells storefront.js where the storefront lives."""
	base = f"/{normalize_prefix(prefix)}" if normalize_prefix(prefix) else ""
	return f'<script data-shop-route-prefix>window.shop_route_prefix = "{base}";</script>'


PREFIX_SCRIPT_RE = re.compile(r"<script data-shop-route-prefix>.*?</script>\s*", re.S)


def with_prefix_script(body_html: str | None, prefix: str) -> str:
	"""body_html with exactly one up-to-date prefix snippet in front."""
	body_html = PREFIX_SCRIPT_RE.sub("", body_html or "")
	if not normalize_prefix(prefix):
		return body_html
	return prefix_script(prefix) + "\n" + body_html


def token_matches(expected: str | None, given: str | None) -> bool:
	"""Compare a secret link token in constant time."""
	import hmac

	return bool(expected and given) and hmac.compare_digest(str(expected), str(given))
