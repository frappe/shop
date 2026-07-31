"""Dot: technical monochrome storefront. Dot grid canvas, floating capsule nav, rounded panels, mono spec labels."""

from shop.theme_generators.blocks import (
	block,
	component_ref,
	dv,
	repeater,
	root,
	upsert_client_script,
	upsert_component,
	upsert_page,
	upsert_variables,
)

GROUP = "dot"
HEAD = "Space Grotesk"
MONO = "DM Mono"

PALETTE = {
	"paper": ("#FFFFFF", "#151517"),
	"canvas": ("#EFEFEF", "#09090A"),
	"ink": ("#0B0B0C", "#F4F4F5"),
	"muted": ("#8A8A8F", "#94949B"),
	"line": ("#E4E4E7", "#2A2A2F"),
	"card": ("#F3F3F4", "#1D1D21"),
	"dots": ("#D1D1D4", "#26262B"),
	"accent": ("#E5322D", "#FF5A54"),
	"success": ("#15803D", "#4ADE80"),
}


def data_script(fn: str, expose: tuple = ()) -> str:
	lines = [f'result = frappe.call("shop.storefront.page_data.{fn}")', "data.update(result)"]
	if expose:
		exposed = ", ".join(f'"{key}": result.get("{key}")' for key in expose)
		lines.append(f"data.page_data = {{{exposed}}}")
	return "\n".join(lines)


def generate():
	refs = upsert_variables(GROUP, PALETTE)
	styles = upsert_client_script("dot-styles", "CSS", theme_css(refs))
	register_components(refs)
	pages = [
		("dot-home", "Home", "home", home_blocks(refs), "home", (), False),
		("dot-products", "Products", "products", products_blocks(refs), "listing", (), False),
		("dot-product", "Product", "product/:slug", product_blocks(refs), "product_page", ("product",), False),
		("dot-collection", "Collection", "collection/:slug", collection_blocks(refs), "collection_page", (), False),
		("dot-cart", "Cart", "cart", cart_blocks(refs), "cart_page", ("cart",), False),
		("dot-checkout", "Checkout", "checkout", checkout_blocks(refs), "checkout_page", ("cart", "addresses"), False),
		(
			"dot-order-confirmation",
			"Order Confirmed",
			"order-confirmation/:order_id",
			confirmation_blocks(refs),
			"order_confirmation",
			(),
			False,
		),
		("dot-account-orders", "Your Orders", "account/orders", account_blocks(refs), "account_orders", (), True),
		("dot-about", "About", "about", about_blocks(refs), "basic", (), False),
		("dot-contact", "Contact", "contact", contact_blocks(refs), "basic", (), False),
		("dot-faq", "FAQ", "faq", faq_blocks(refs), "basic", (), False),
	]
	for page_name, title, route, blocks, data_fn, expose, authenticated in pages:
		upsert_page(
			GROUP,
			page_name,
			title,
			route,
			blocks,
			data_script(data_fn, expose),
			client_scripts=[styles],
			authenticated_access=authenticated,
		)


def register_components(refs):
	"""Reusable pieces listed in Builder's insert panel; ids are namespaced so themes never overwrite each other."""
	for component_id, component_name, node in [
		("dot-navbar", "Dot Navbar", nav(refs)),
		("dot-footer", "Dot Footer", footer(refs)),
		("dot-cart-drawer", "Dot Cart Drawer", cart_drawer()),
		("dot-hero", "Dot Hero", hero(refs)),
		("dot-product-card", "Dot Product Card", product_card(refs)),
		("dot-collection-tile", "Dot Collection Tile", collection_tile(refs)),
		("dot-filter-bar", "Dot Filter Bar", filter_bar(refs)),
		("dot-review-card", "Dot Review Card", review_card(refs)),
		("dot-delivery-card", "Dot Delivery Promise", delivery_card(refs)),
		("dot-trust-row", "Dot Spec Row", trust_row(refs)),
	]:
		upsert_component(component_id, component_name, node)


def theme_css(refs):
	return f"""
button {{ cursor: pointer; }}
button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
:focus-visible {{ outline: 2px solid {refs["ink"]}; outline-offset: 3px; }}
input, textarea, select {{ font-family: {MONO}, monospace; }}
input::placeholder, textarea::placeholder {{ color: {refs["muted"]}; }}
input[type="radio"] {{ accent-color: {refs["ink"]}; }}
[data-shop="variant-option"][data-selected="true"] {{
	background: {refs["ink"]};
	color: {refs["paper"]};
	border-color: {refs["ink"]};
}}
[data-shop="cart-count"][data-empty="true"] {{ display: none; }}
a[data-active="true"] {{
	background: {refs["ink"]};
	color: {refs["paper"]};
	border-color: {refs["ink"]};
}}
[data-shop="rating-star"] {{ cursor: pointer; }}
[data-shop="rating-star"][data-selected="true"] {{ color: {refs["ink"]}; }}
[data-shop="thumb"][data-selected="true"] {{ border-color: {refs["ink"]}; }}
[data-shop="order-progress"] .progress-stage {{
	align-items: center;
	display: flex;
	flex: 1;
	flex-direction: column;
	gap: 9px;
	position: relative;
}}
[data-shop="order-progress"] .progress-stage::before {{
	background: {refs["line"]};
	content: "";
	height: 1px;
	position: absolute;
	right: 50%;
	top: 4px;
	width: 100%;
}}
[data-shop="order-progress"] .progress-stage:first-child::before {{ display: none; }}
[data-shop="order-progress"] .progress-stage[data-done="true"]::before {{ background: {refs["ink"]}; }}
.progress-stage .stage-dot {{
	background: {refs["paper"]};
	border: 1px solid {refs["line"]};
	border-radius: 50%;
	height: 9px;
	position: relative;
	width: 9px;
	z-index: 1;
}}
.progress-stage[data-done="true"] .stage-dot {{ background: {refs["ink"]}; border-color: {refs["ink"]}; }}
.progress-stage .stage-label {{
	color: {refs["muted"]};
	font-family: {MONO}, monospace;
	font-size: 10px;
	letter-spacing: 0.08em;
	text-align: center;
	text-transform: uppercase;
}}
.progress-stage[data-done="true"] .stage-label {{ color: {refs["ink"]}; }}
[data-shop="cart-drawer"] {{
	position: fixed;
	inset: 0;
	z-index: 90;
	pointer-events: none;
}}
[data-shop="cart-drawer"] .drawer-backdrop {{
	position: absolute;
	inset: 0;
	background: rgba(0, 0, 0, 0.45);
	display: none;
}}
[data-shop="cart-drawer"] .drawer-panel {{
	position: absolute;
	top: 0;
	right: 0;
	height: 100%;
	width: min(420px, 100vw);
	background: {refs["paper"]};
	color: {refs["ink"]};
	display: none;
	flex-direction: column;
}}
[data-shop="cart-drawer"][data-open="true"] {{ pointer-events: auto; }}
[data-shop="cart-drawer"][data-open="true"] .drawer-backdrop {{ display: block; }}
[data-shop="cart-drawer"][data-open="true"] .drawer-panel {{ display: flex; }}
.drawer-header {{
	align-items: center;
	border-bottom: 1px solid {refs["line"]};
	display: flex;
	flex-shrink: 0;
	justify-content: space-between;
	padding: 20px 24px;
}}
.drawer-title {{
	font-family: {MONO}, monospace;
	font-size: 12px;
	letter-spacing: 0.12em;
	text-transform: uppercase;
}}
.drawer-close {{
	background: none;
	border: 0;
	color: {refs["ink"]};
	font-size: 20px;
	line-height: 1;
	padding: 2px 6px;
}}
.drawer-items {{ flex: 1; overflow-y: auto; padding: 4px 24px; }}
.drawer-item {{
	align-items: flex-start;
	border-bottom: 1px solid {refs["line"]};
	display: flex;
	gap: 14px;
	padding: 18px 0;
}}
.drawer-item:last-child {{ border-bottom: 0; }}
.drawer-thumb {{
	background: {refs["card"]};
	border-radius: 10px;
	flex-shrink: 0;
	height: 64px;
	object-fit: cover;
	width: 64px;
}}
.drawer-info {{ display: flex; flex: 1; flex-direction: column; gap: 4px; min-width: 0; }}
.drawer-name {{
	color: {refs["ink"]};
	font-size: 13px;
	font-weight: 500;
	line-height: 1.45;
	text-decoration: none;
}}
.drawer-rate {{
	color: {refs["muted"]};
	font-family: {MONO}, monospace;
	font-size: 11px;
	letter-spacing: 0.04em;
}}
.drawer-qty {{ align-items: center; display: flex; gap: 8px; margin-top: 8px; }}
.drawer-qty > button {{
	align-items: center;
	background: {refs["paper"]};
	border: 1px solid {refs["line"]};
	border-radius: 999px;
	color: {refs["ink"]};
	display: flex;
	font-size: 13px;
	height: 26px;
	justify-content: center;
	width: 26px;
}}
.drawer-qty > span {{
	font-family: {MONO}, monospace;
	font-size: 12px;
	min-width: 16px;
	text-align: center;
}}
.drawer-qty > .drawer-remove {{
	background: none;
	border: 0;
	color: {refs["muted"]};
	font-family: {MONO}, monospace;
	font-size: 10px;
	height: auto;
	letter-spacing: 0.1em;
	margin-left: 8px;
	padding: 0;
	text-transform: uppercase;
	width: auto;
}}
.drawer-amount {{
	flex-shrink: 0;
	font-family: {MONO}, monospace;
	font-size: 12px;
	font-weight: 500;
}}
.drawer-empty {{
	color: {refs["muted"]};
	font-family: {MONO}, monospace;
	font-size: 12px;
	letter-spacing: 0.08em;
	padding: 48px 0;
	text-align: center;
	text-transform: uppercase;
}}
.drawer-footer {{
	border-top: 1px solid {refs["line"]};
	display: flex;
	flex-direction: column;
	flex-shrink: 0;
	gap: 12px;
	padding: 18px 24px 22px;
}}
.drawer-total-row {{
	align-items: baseline;
	display: flex;
	font-family: {MONO}, monospace;
	font-size: 13px;
	justify-content: space-between;
	letter-spacing: 0.06em;
	text-transform: uppercase;
}}
.drawer-note {{
	color: {refs["muted"]};
	font-size: 11px;
	line-height: 1.5;
	margin-top: -6px;
}}
.drawer-actions {{ display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }}
.drawer-view, .drawer-checkout {{
	border-radius: 999px;
	font-family: {MONO}, monospace;
	font-size: 11px;
	letter-spacing: 0.12em;
	padding: 13px 16px;
	text-align: center;
	text-decoration: none;
	text-transform: uppercase;
}}
.drawer-view {{
	border: 1px solid {refs["ink"]};
	color: {refs["ink"]};
}}
.drawer-checkout {{
	background: {refs["ink"]};
	border: 1px solid {refs["ink"]};
	color: {refs["paper"]};
}}
.pdp-buybar {{
	bottom: 18px;
	display: flex;
	justify-content: center;
	left: 0;
	padding: 0 20px;
	position: fixed;
	right: 0;
	z-index: 80;
}}
.pdp-buybar[data-visible="false"] {{ display: none; }}
.pdp-buybar-inner {{
	align-items: center;
	background: {refs["paper"]};
	border: 1px solid {refs["line"]};
	border-radius: 999px;
	display: flex;
	gap: 20px;
	justify-content: space-between;
	padding: 10px 10px 10px 24px;
	width: fit-content;
}}
@media (max-width: 640px) {{
	.pdp-buybar {{ bottom: 0; padding: 0 12px 10px; }}
	.pdp-buybar-inner {{ width: 100%; }}
	[data-shop="qty-inc"], [data-shop="qty-dec"], [data-drawer-step] {{ min-height: 36px; min-width: 36px; }}
	.drawer-close {{ padding: 10px; margin: -10px; }}
	[data-shop="remove"], .drawer-remove {{ padding: 8px 6px; }}
}}
#reviews {{ scroll-margin-top: 100px; }}
"""


def mono(size="12px", weight="400", color=None, spacing="0.1em", upper=True) -> dict:
	styles = {
		"fontFamily": MONO,
		"fontSize": size,
		"fontWeight": weight,
		"height": "fit-content",
		"letterSpacing": spacing,
		"width": "fit-content",
	}
	if color:
		styles["color"] = color
	if upper:
		styles["textTransform"] = "uppercase"
	return styles


def label(refs, text, color=None, size="11px", element="p", **extra):
	return block(element, text=text, styles=mono(size=size, color=color or refs["muted"], spacing="0.14em"), **extra)


def display(refs, text, size="34px", mobile_size="26px", element="h2", weight="500"):
	return block(
		element,
		text=text,
		styles={
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": size,
			"fontWeight": weight,
			"height": "fit-content",
			"letterSpacing": "-0.02em",
			"lineHeight": "1.1",
			"width": "fit-content",
		},
		mobile={"fontSize": mobile_size},
	)


def prose(refs, text, size="14px", color=None, width="100%"):
	return block(
		"p",
		text=text,
		styles={
			"color": color or refs["muted"],
			"fontSize": size,
			"height": "fit-content",
			"lineHeight": "1.65",
			"width": width,
		},
	)


def run(refs, parts, size="12px", color=None, weight="400", family=None):
	"""Row of spans with no gap so bound values sit inside literal text."""
	spans = []
	for bound, value in parts:
		styles = {
			"color": color or refs["muted"],
			"fontSize": size,
			"fontWeight": weight,
			"height": "fit-content",
			"whiteSpace": "pre",
			"width": "fit-content",
		}
		if family:
			styles["fontFamily"] = family
			styles["letterSpacing"] = "0.06em"
		spans.append(
			block(
				"span",
				text="" if bound else value,
				styles=styles,
				dynamicValues=[dv(value, "innerHTML")] if bound else [],
			)
		)
	return block(
		"div",
		styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "width": "fit-content"},
		children=spans,
	)


def pill(refs, text, href=None, variant="solid", full=False, attrs=None, **extra):
	element = "a" if href else "button"
	base_attrs = {"href": href} if href else {"type": "button"}
	base_attrs.update(attrs or {})
	styles = {
		"backgroundColor": refs["ink"] if variant == "solid" else "transparent",
		"borderColor": refs["ink"] if variant != "quiet" else refs["line"],
		"borderRadius": "999px",
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["paper"] if variant == "solid" else refs["ink"],
		"fontFamily": MONO,
		"fontSize": "11px",
		"height": "fit-content",
		"letterSpacing": "0.14em",
		"padding": "14px 28px",
		"textAlign": "center",
		"textDecoration": "none",
		"textTransform": "uppercase",
		"width": "100%" if full else "fit-content",
	}
	return block(element, text=text, attrs=base_attrs, styles=styles, **extra)


def panel(refs, children, styles=None, mobile=None, name=None, tone="paper"):
	base = {
		"backgroundColor": refs[tone],
		"borderRadius": "20px",
		"display": "flex",
		"flexDirection": "column",
		"flexShrink": 0,
		"gap": "24px",
		"padding": "40px",
		"width": "100%",
	}
	base.update(styles or {})
	responsive = {"borderRadius": "16px", "gap": "20px", "padding": "24px 18px"}
	responsive.update(mobile or {})
	return block("div", name=name, styles=base, mobile=responsive, children=children)


def stack(children, name=None):
	return block(
		"div",
		name=name or "Stack",
		styles={
			"display": "flex",
			"flexDirection": "column",
			"flexShrink": 0,
			"gap": "16px",
			"maxWidth": "1040px",
			"padding": "0 20px",
			"width": "100%",
		},
		mobile={"gap": "12px", "padding": "0 12px"},
		children=children,
	)


def section_head(refs, index, title, link_label=None, link_href=None):
	left = block(
		"div",
		styles={"display": "flex", "flexDirection": "column", "gap": "10px", "width": "fit-content"},
		children=[label(refs, index), display(refs, title, size="24px", mobile_size="20px")],
	)
	children = [left]
	if link_label:
		children.append(
			block(
				"a",
				text=link_label,
				attrs={"href": link_href},
				styles={**mono(size="11px", color=refs["muted"], spacing="0.14em"), "textDecoration": "none"},
			)
		)
	return block(
		"div",
		name="Section Head",
		styles={
			"alignItems": "flex-end",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"width": "100%",
		},
		children=children,
	)


def spec_strip(refs, items, tone=None):
	entry = lambda text: block(
		"p",
		text=text,
		styles=mono(size="10px", color=tone or refs["muted"], spacing="0.16em"),
	)
	return block(
		"div",
		name="Spec Strip",
		styles={
			"borderTopColor": refs["line"],
			"borderTopStyle": "solid",
			"borderTopWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"flexWrap": "wrap",
			"gap": "10px 28px",
			"paddingTop": "18px",
			"width": "100%",
		},
		children=[entry(text) for text in items],
	)


def utility_row(refs, text, href, glyph="→"):
	color = refs["ink"]
	return block(
		"a",
		name="Utility Row",
		attrs={"href": href},
		styles={
			"alignItems": "center",
			"borderColor": refs["line"],
			"borderRadius": "999px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": color,
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "13px 20px",
			"textDecoration": "none",
			"width": "100%",
		},
		children=[
			block("span", text=text, styles=mono(size="11px", color=color, spacing="0.14em")),
			block("span", text=glyph, styles=mono(size="12px", color=refs["muted"], spacing="0")),
		],
	)


def shell(refs, children):
	node = root(
		{
			"alignItems": "center",
			"backgroundColor": refs["canvas"],
			"backgroundImage": f"radial-gradient({refs['dots']} 1px, transparent 1px)",
			"backgroundSize": "24px 24px",
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"flexShrink": 0,
			"fontFamily": HEAD,
			"gap": "16px",
			"minHeight": "100vh",
			"paddingTop": "94px",
			"width": "100%",
		},
		children + [component_ref("dot-cart-drawer")],
	)
	node["mobileStyles"] = {"gap": "12px", "paddingTop": "78px"}
	return [node]


def brand(refs):
	color = refs["ink"]
	return block(
		"a",
		name="Brand",
		attrs={"href": "/"},
		styles={
			"alignItems": "center",
			"color": color,
			"display": "flex",
			"flexDirection": "row",
			"gap": "9px",
			"height": "fit-content",
			"textDecoration": "none",
			"whiteSpace": "nowrap",
			"width": "fit-content",
		},
		children=[
			block(
				"span",
				styles={
					"backgroundColor": refs["accent"],
					"borderRadius": "50%",
					"flexShrink": 0,
					"height": "8px",
					"width": "8px",
				},
			),
			block(
				"span",
				text="Shop",
				styles=mono(size="13px", weight="500", color=color, spacing="0.16em"),
				dynamicValues=[dv("store.name", "innerHTML")],
			),
		],
	)


def nav(refs):
	link_style = {**mono(size="11px", color=refs["ink"], spacing="0.14em"), "textDecoration": "none"}
	badge = block(
		"span",
		text="0",
		attrs={"data-shop": "cart-count", "data-empty": "true"},
		styles={
			"alignItems": "center",
			"backgroundColor": refs["ink"],
			"borderRadius": "999px",
			"color": refs["paper"],
			"display": "flex",
			"fontFamily": MONO,
			"fontSize": "10px",
			"height": "18px",
			"justifyContent": "center",
			"minWidth": "18px",
			"padding": "0 5px",
		},
	)
	cart_link = block(
		"a",
		name="Cart Link",
		attrs={"href": "/cart", "data-shop": "cart-toggle"},
		styles={
			"alignItems": "center",
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "row",
			"gap": "8px",
			"height": "fit-content",
			"textDecoration": "none",
			"width": "fit-content",
		},
		children=[block("span", text="Cart", styles=dict(link_style)), badge],
	)
	capsule = block(
		"div",
		name="Capsule",
		styles={
			"alignItems": "center",
			"backgroundColor": refs["paper"],
			"borderColor": refs["line"],
			"borderRadius": "999px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "32px",
			"justifyContent": "space-between",
			"maxWidth": "1000px",
			"padding": "13px 24px",
			"width": "100%",
		},
		mobile={"gap": "12px", "padding": "11px 16px"},
		children=[
			brand(refs),
			block(
				"div",
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "26px"},
				mobile={"gap": "14px"},
				children=[
					block("a", text="Shop", attrs={"href": "/products"}, styles=dict(link_style)),
					block("a", text="About", attrs={"href": "/about"}, styles=dict(link_style), mobile={"display": "none"}),
					block("a", text="Contact", attrs={"href": "/contact"}, styles=dict(link_style), mobile={"display": "none"}),
					block(
						"a",
						text="Account",
						attrs={"href": "/account/orders"},
						styles=dict(link_style),
						dynamicValues=[
							dv("store.account_label", "innerHTML"),
							dv("store.account_url", "href", "attribute"),
						],
					),
					cart_link,
				],
			),
		],
	)
	return block(
		"div",
		name="Nav",
		styles={
			"display": "flex",
			"justifyContent": "center",
			"left": "0",
			"padding": "0 20px",
			"position": "fixed",
			"right": "0",
			"top": "16px",
			"width": "100%",
			"zIndex": "70",
		},
		mobile={"padding": "0 12px", "top": "10px"},
		children=[capsule],
	)


def footer_column(refs, title, links):
	return block(
		"div",
		styles={"display": "flex", "flexDirection": "column", "gap": "12px", "width": "100%"},
		children=[
			block("p", text=title, styles=mono(size="10px", color=refs["muted"], spacing="0.16em")),
			*[
				block(
					"a",
					text=text,
					attrs={"href": href},
					styles={**mono(size="11px", color=refs["ink"], spacing="0.1em"), "textDecoration": "none"},
				)
				for text, href in links
			],
		],
	)


def footer(refs):
	"""Sits on the canvas rather than in a panel so it stays out of the way."""
	inner = block(
		"div",
		name="Footer Inner",
		styles={"display": "flex", "flexDirection": "column", "gap": "32px", "width": "100%"},
		mobile={"gap": "24px"},
		children=[
			block(
				"div",
				styles={
					"display": "flex",
					"flexDirection": "row",
					"gap": "48px",
					"justifyContent": "space-between",
					"width": "100%",
				},
				mobile={"flexDirection": "column", "gap": "26px"},
				children=[
					block(
						"div",
						styles={"display": "flex", "flexDirection": "column", "gap": "14px", "maxWidth": "300px", "width": "100%"},
						children=[
							brand(refs),
							prose(
								refs,
								"A short catalogue of everyday objects, made in small runs and built to be kept.",
								size="13px",
							),
						],
					),
					block(
						"div",
						styles={
							"display": "grid",
							"gap": "40px",
							"gridTemplateColumns": "repeat(3, minmax(110px, 1fr))",
							"width": "fit-content",
						},
						mobile={"gap": "22px", "gridTemplateColumns": "repeat(3, minmax(0, 1fr))", "width": "100%"},
						children=[
							footer_column(refs, "Shop", [("All products", "/products"), ("Collections", "/products")]),
							footer_column(refs, "Support", [("Contact", "/contact"), ("FAQ", "/faq")]),
							footer_column(refs, "Legal", [("Privacy", "/about"), ("Terms", "/about")]),
						],
					),
				],
			),
			block(
				"div",
				styles={
					"alignItems": "center",
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "row",
					"gap": "6px",
					"paddingTop": "20px",
					"width": "100%",
				},
				children=[
					block("span", text="© 2026", styles=mono(size="10px", color=refs["muted"], spacing="0.12em")),
					block(
						"span",
						text="Shop",
						styles=mono(size="10px", color=refs["muted"], spacing="0.12em"),
						dynamicValues=[dv("store.name", "innerHTML")],
					),
					block("span", text="· All rights reserved", styles=mono(size="10px", color=refs["muted"], spacing="0.12em")),
				],
			),
		],
	)
	return block(
		"div",
		name="Footer",
		styles={
			"display": "flex",
			"flexShrink": 0,
			"justifyContent": "center",
			"marginTop": "auto",
			"padding": "40px 0 48px",
			"width": "100%",
		},
		mobile={"padding": "28px 0 36px"},
		children=[
			block(
				"div",
				styles={"display": "flex", "maxWidth": "1040px", "padding": "0 20px", "width": "100%"},
				mobile={"padding": "0 12px"},
				children=[inner],
			)
		],
	)


def cart_drawer():
	return block(
		"aside",
		name="Cart Drawer",
		attrs={"data-shop": "cart-drawer", "data-open": "false", "aria-label": "Shopping cart"},
		children=[
			block("div", name="Backdrop", attrs={"data-shop": "drawer-backdrop"}, classes=["drawer-backdrop"]),
			block(
				"div",
				name="Panel",
				classes=["drawer-panel"],
				children=[
					block(
						"div",
						name="Drawer Header",
						classes=["drawer-header"],
						children=[
							block("h2", text="Your cart", classes=["drawer-title"]),
							block(
								"button",
								text="×",
								attrs={"type": "button", "data-shop": "drawer-close", "aria-label": "Close cart"},
								classes=["drawer-close"],
							),
						],
					),
					block("div", name="Drawer Items", attrs={"data-shop": "drawer-items"}, classes=["drawer-items"]),
					block(
						"div",
						name="Drawer Footer",
						classes=["drawer-footer"],
						children=[
							block(
								"div",
								classes=["drawer-total-row"],
								children=[
									block("span", text="Subtotal"),
									block("span", text="", attrs={"data-shop": "drawer-total"}),
								],
							),
							block("p", text="Shipping and taxes calculated at checkout.", classes=["drawer-note"]),
							block(
								"div",
								classes=["drawer-actions"],
								children=[
									block("a", text="View cart", attrs={"href": "/cart"}, classes=["drawer-view"]),
									block("a", text="Checkout", attrs={"href": "/checkout"}, classes=["drawer-checkout"]),
								],
							),
						],
					),
				],
			),
		],
	)


def error_banner(refs):
	return block(
		"div",
		name="Error",
		text="",
		attrs={"data-shop": "error", "role": "alert"},
		styles={
			"borderColor": refs["accent"],
			"borderRadius": "12px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["accent"],
			"display": "none",
			"fontSize": "13px",
			"lineHeight": "1.5",
			"padding": "12px 16px",
			"width": "100%",
		},
	)


def page_header(refs, index, title, subtitle=None, extra=None, aside=None):
	"""Headings sit straight on the dot canvas; content lives in the panels below."""
	children = [label(refs, index), display(refs, title, size="38px", mobile_size="26px", element="h1")]
	if subtitle:
		children.append(prose(refs, subtitle, size="14px", width="min(520px, 100%)"))
	children.extend(extra or [])
	stacked = block(
		"div",
		styles={"display": "flex", "flexDirection": "column", "gap": "12px", "width": "100%"},
		children=children,
	)
	return block(
		"div",
		name="Page Header",
		styles={
			"alignItems": "flex-end",
			"display": "flex",
			"flexDirection": "row",
			"gap": "24px",
			"justifyContent": "space-between",
			"padding": "26px 4px 6px",
			"width": "100%",
		},
		mobile={"alignItems": "stretch", "flexDirection": "column", "gap": "14px", "padding": "16px 4px 2px"},
		children=[stacked, aside] if aside else [stacked],
	)


def hero(refs):
	return panel(
		refs,
		[
			label(refs, "( 01 ) New drop"),
			block(
				"h1",
				text="Fewer things.<br>Made properly.",
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "62px",
					"fontWeight": "500",
					"height": "fit-content",
					"letterSpacing": "-0.03em",
					"lineHeight": "1.02",
					"maxWidth": "700px",
					"width": "100%",
				},
				mobile={"fontSize": "36px"},
			),
			prose(
				refs,
				"A short catalogue of everyday objects. Considered materials, honest prices "
				"and nothing in the box you will not use.",
				size="15px",
				width="min(460px, 100%)",
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "10px", "marginTop": "4px"},
				children=[
					pill(refs, "Shop all", href="/products"),
					pill(refs, "Collections", href="/products", variant="outline"),
				],
			),
			spec_strip(refs, ["48h dispatch", "14 day returns", "Free shipping", "Cash on delivery"]),
		],
		styles={"gap": "20px", "padding": "56px 40px 34px"},
		mobile={"gap": "18px", "padding": "30px 18px 22px"},
		name="Hero",
	)


def product_card(refs):
	well = block(
		"div",
		name="Image Well",
		styles={
			"aspectRatio": "4 / 5",
			"backgroundColor": refs["card"],
			"borderRadius": "14px",
			"display": "flex",
			"overflow": "hidden",
			"width": "100%",
		},
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={"display": "block", "height": "100%", "objectFit": "cover", "width": "100%"},
				dynamicValues=[dv("image", "src", "attribute"), dv("product_name", "alt", "attribute")],
			)
		],
	)
	price_row = block(
		"div",
		name="Card Price",
		styles={
			"alignItems": "baseline",
			"display": "flex",
			"flexDirection": "row",
			"flexWrap": "wrap",
			"gap": "4px 10px",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="",
				visibilityCondition={"key": "formatted_price", "comesFrom": "dataScript"},
				styles=mono(size="13px", weight="500", color=refs["ink"], spacing="0.04em", upper=False),
				dynamicValues=[dv("formatted_price", "innerHTML")],
			),
			block(
				"span",
				text="",
				visibilityCondition={"key": "formatted_compare_at", "comesFrom": "dataScript"},
				styles={
					**mono(size="11px", color=refs["muted"], spacing="0.04em", upper=False),
					"textDecoration": "line-through",
				},
				dynamicValues=[dv("formatted_compare_at", "innerHTML")],
			),
			block(
				"div",
				visibilityCondition={"key": "discount_pct", "comesFrom": "dataScript"},
				styles={"display": "flex", "flexDirection": "row", "width": "fit-content"},
				children=[
					run(
						refs,
						[(False, "−"), (True, "discount_pct"), (False, "%")],
						size="11px",
						color=refs["accent"],
						family=MONO,
					)
				],
			),
		],
	)
	rating_row = block(
		"div",
		name="Card Rating",
		visibilityCondition={"key": "rating_count", "comesFrom": "dataScript"},
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "6px", "width": "fit-content"},
		children=[
			stars_span(refs, "rating_stars", size="11px"),
			run(refs, [(False, "("), (True, "rating_count"), (False, ")")], size="11px", family=MONO),
		],
	)
	return block(
		"a",
		name="Product Card",
		attrs={"href": "#"},
		styles={
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			well,
			block(
				"h3",
				text="Product",
				styles={
					"fontSize": "14px",
					"fontWeight": "500",
					"height": "fit-content",
					"letterSpacing": "-0.01em",
					"lineHeight": "1.35",
					"width": "100%",
				},
				dynamicValues=[dv("product_name", "innerHTML")],
			),
			rating_row,
			price_row,
		],
	)


def stars_span(refs, key, size="12px"):
	return block(
		"span",
		text="★★★★★",
		styles={
			"color": refs["ink"],
			"fontSize": size,
			"height": "fit-content",
			"letterSpacing": "1px",
			"lineHeight": "1",
			"width": "fit-content",
		},
		dynamicValues=[dv(key, "innerHTML")],
	)


def product_grid(refs, key, source, columns=4):
	return repeater(
		key,
		component_ref("dot-product-card"),
		{
			"display": "grid",
			"gap": "34px 20px",
			"gridTemplateColumns": f"repeat({columns}, minmax(0, 1fr))",
			"width": "100%",
		},
		mobile={"gap": "22px 12px", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
		tablet={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
		name=f"Grid · {source}",
	)


def collection_tile(refs):
	photo = block(
		"div",
		name="Tile Photo",
		styles={"backgroundPosition": "center", "backgroundSize": "cover", "inset": "0", "position": "absolute"},
		dynamicValues=[dv("image_css", "background-image", "style")],
	)
	title_pill = block(
		"span",
		text="Collection",
		styles={
			**mono(size="11px", weight="500", color=refs["ink"], spacing="0.12em"),
			"backgroundColor": refs["paper"],
			"borderRadius": "999px",
			"padding": "9px 16px",
			"position": "relative",
		},
		dynamicValues=[dv("title", "innerHTML")],
	)
	return block(
		"a",
		name="Collection Tile",
		attrs={"href": "#"},
		styles={
			"alignItems": "flex-start",
			"backgroundColor": refs["card"],
			"borderRadius": "16px",
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"justifyContent": "flex-end",
			"minHeight": "210px",
			"overflow": "hidden",
			"padding": "16px",
			"position": "relative",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[photo, title_pill],
	)


def filter_bar(refs):
	option_chip = block(
		"a",
		name="Filter Option",
		text="Option",
		attrs={"href": "#", "data-active": "false"},
		styles={
			"borderColor": refs["line"],
			"borderRadius": "999px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontFamily": MONO,
			"fontSize": "10px",
			"height": "fit-content",
			"letterSpacing": "0.06em",
			"padding": "6px 12px",
			"textDecoration": "none",
			"whiteSpace": "nowrap",
			"width": "fit-content",
		},
		dynamicValues=[
			dv("url", "href", "attribute"),
			dv("label", "innerHTML"),
			dv("active", "data-active", "attribute"),
		],
	)
	filter_group = block(
		"div",
		name="Filter Group",
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "14px", "width": "100%"},
		mobile={"alignItems": "flex-start", "flexDirection": "column", "gap": "6px"},
		children=[
			block(
				"p",
				text="Filter",
				styles={
					**mono(size="9px", color=refs["muted"], spacing="0.14em"),
					"flexShrink": 0,
					"minWidth": "74px",
				},
				dynamicValues=[dv("label", "innerHTML")],
			),
			repeater(
				"options",
				option_chip,
				{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "6px", "width": "100%"},
				name="Filter Options",
			),
		],
	)
	return repeater(
		"filters",
		filter_group,
		{"display": "flex", "flexDirection": "column", "gap": "8px", "width": "100%"},
		name="Filters",
	)


def review_card(refs):
	return block(
		"div",
		name="Review",
		styles={
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "8px",
			"padding": "20px 0",
			"width": "100%",
		},
		children=[
			stars_span(refs, "stars", size="12px"),
			block(
				"h3",
				text="Review title",
				styles={"fontSize": "14px", "fontWeight": "500", "height": "fit-content", "width": "100%"},
				dynamicValues=[dv("title", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "lineHeight": "1.6", "width": "100%"},
				dynamicValues=[dv("review", "innerHTML")],
			),
			block(
				"div",
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "10px", "width": "100%"},
				children=[
					run(refs, [(True, "reviewer_name"), (False, " · "), (True, "posted_on")], size="10px", family=MONO),
					block(
						"span",
						text="Verified buyer",
						visibilityCondition={"key": "verified", "comesFrom": "dataScript"},
						styles=mono(size="10px", color=refs["success"], spacing="0.12em"),
					),
				],
			),
		],
	)


def delivery_card(refs):
	line = lambda text, **extra: block(
		"p",
		text=text,
		styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.5", "width": "100%"},
		**extra,
	)
	return block(
		"div",
		name="Delivery",
		styles={
			"backgroundColor": refs["card"],
			"borderRadius": "14px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "6px",
			"padding": "16px 18px",
			"width": "100%",
		},
		children=[
			block("p", text="Free delivery", styles=mono(size="11px", color=refs["ink"], spacing="0.12em")),
			line("Ships in 48 hours. 14 day easy returns."),
			line(
				"Cash on delivery available.",
				visibilityCondition={"key": "store.enable_cod", "comesFrom": "dataScript"},
			),
		],
	)


def trust_row(refs):
	return spec_strip(refs, ["Secure payments", "Easy returns", "Quality checked", "Support that replies"])


def home_blocks(refs):
	collections = panel(
		refs,
		[
			section_head(refs, "( 02 ) Collections", "Shop by collection", "All products →", "/products"),
			repeater(
				"collections",
				component_ref("dot-collection-tile"),
				{
					"display": "grid",
					"gap": "16px",
					"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				tablet={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
				name="Grid · collections",
			),
		],
		name="Section · Collections",
	)
	best_sellers = panel(
		refs,
		[
			section_head(refs, "( 03 ) Best sellers", "What people keep buying", "View all →", "/products"),
			product_grid(refs, "featured_products", "featured"),
		],
		name="Section · Best Sellers",
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([component_ref("dot-hero"), collections, best_sellers]),
			component_ref("dot-footer"),
		],
	)


def search_form(refs):
	go = pill(refs, "Go", attrs={"type": "submit"})
	go["baseStyles"]["padding"] = "10px 20px"
	return block(
		"form",
		name="Search",
		attrs={"data-shop": "search-form", "action": "/products"},
		styles={"display": "flex", "flexDirection": "row", "gap": "8px", "width": "fit-content"},
		mobile={"width": "100%"},
		children=[
			block(
				"input",
				attrs={"type": "search", "name": "search", "placeholder": "Search"},
				dynamicValues=[dv("search", "value", "attribute")],
				styles={
					"backgroundColor": refs["paper"],
					"borderColor": refs["line"],
					"borderRadius": "999px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"fontSize": "11px",
					"padding": "9px 16px",
					"width": "200px",
				},
				mobile={"width": "100%"},
			),
			go,
		],
	)


def products_blocks(refs):
	active_search = block(
		"div",
		name="Active Search",
		visibilityCondition={"key": "search_label", "comesFrom": "dataScript"},
		styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "gap": "12px", "width": "fit-content"},
		children=[
			block(
				"p",
				text="Results",
				styles=mono(size="11px", color=refs["ink"], spacing="0.1em", upper=False),
				dynamicValues=[dv("search_label", "innerHTML")],
			),
			block(
				"a",
				text="Clear",
				attrs={"href": "/products"},
				styles={**mono(size="10px", color=refs["muted"], spacing="0.14em"), "textDecoration": "underline"},
			),
		],
	)
	header = page_header(
		refs,
		"( Catalogue )",
		"All products",
		"Everything in the store, filtered however you like.",
		extra=[active_search],
		aside=search_form(refs),
	)
	controls = panel(
		refs,
		[component_ref("dot-filter-bar")],
		styles={"padding": "18px 28px"},
		mobile={"padding": "16px 14px"},
		name="Section · Controls",
	)
	empty = block(
		"div",
		name="No Results",
		visibilityCondition={"key": "no_results", "comesFrom": "dataScript"},
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"padding": "40px 0",
			"width": "100%",
		},
		children=[
			block("p", text="Nothing matches those filters", styles=mono(size="12px", color=refs["ink"], spacing="0.1em")),
			block(
				"a",
				text="Clear all",
				attrs={"href": "/products"},
				styles={**mono(size="10px", color=refs["muted"], spacing="0.14em"), "textDecoration": "underline"},
			),
		],
	)
	grid = panel(refs, [product_grid(refs, "products", "products"), empty], name="Section · Product Grid")
	return shell(
		refs,
		[component_ref("dot-navbar"), stack([header, controls, grid]), component_ref("dot-footer")],
	)


def collection_blocks(refs):
	title = display(refs, "Collection", size="38px", mobile_size="26px", element="h1")
	title["dynamicValues"] = [dv("collection.title", "innerHTML")]
	description = block(
		"p",
		text="",
		visibilityCondition={"key": "collection.description", "comesFrom": "dataScript"},
		styles={
			"color": refs["muted"],
			"fontSize": "14px",
			"height": "fit-content",
			"lineHeight": "1.65",
			"width": "min(520px, 100%)",
		},
		dynamicValues=[dv("collection.description", "innerHTML")],
	)
	header = block(
		"div",
		name="Page Header",
		styles={"display": "flex", "flexDirection": "column", "gap": "12px", "padding": "26px 4px 6px", "width": "100%"},
		mobile={"padding": "16px 4px 2px"},
		children=[label(refs, "( Collection )"), title, description],
	)
	grid = panel(refs, [product_grid(refs, "products", "collection")], name="Section · Collection Grid")
	return shell(refs, [component_ref("dot-navbar"), stack([header, grid]), component_ref("dot-footer")])


def inset(refs, children, styles=None, **extra):
	base = {
		"backgroundColor": refs["card"],
		"borderRadius": "14px",
		"display": "flex",
		"flexDirection": "column",
		"gap": "6px",
		"padding": "18px 20px",
		"width": "100%",
	}
	base.update(styles or {})
	return block("div", styles=base, children=children, **extra)


def field_styles(refs, radius="12px"):
	return {
		"backgroundColor": refs["paper"],
		"borderColor": refs["line"],
		"borderRadius": radius,
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["ink"],
		"fontSize": "12px",
		"padding": "12px 14px",
		"width": "100%",
	}


def money_row(refs, text, bound_key=None, static_value=None, strong=False):
	return block(
		"div",
		styles={"display": "flex", "flexDirection": "row", "justifyContent": "space-between", "width": "100%"},
		children=[
			block(
				"p",
				text=text,
				styles=mono(size="11px", color=refs["ink"] if strong else refs["muted"], spacing="0.12em"),
			),
			block(
				"p",
				text=static_value or "",
				styles=mono(
					size="14px" if strong else "12px",
					weight="500" if strong else "400",
					color=refs["success"] if static_value == "Free" else refs["ink"],
					spacing="0.04em",
					upper=False,
				),
				dynamicValues=[dv(bound_key, "innerHTML")] if bound_key else [],
			),
		],
	)


def discount_row(refs, bound_key, condition_key):
	return block(
		"div",
		name="Discount Row",
		visibilityCondition={"key": condition_key, "comesFrom": "dataScript"},
		styles={"display": "flex", "flexDirection": "row", "justifyContent": "space-between", "width": "100%"},
		children=[
			block("p", text="Discount", styles=mono(size="11px", color=refs["muted"], spacing="0.12em")),
			run(refs, [(False, "−"), (True, bound_key)], size="12px", color=refs["accent"], family=MONO),
		],
	)


def breadcrumb(refs, trail_key):
	crumb = {**mono(size="10px", color=refs["muted"], spacing="0.14em"), "textDecoration": "none"}
	return block(
		"div",
		name="Breadcrumb",
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"gap": "8px",
			"padding": "20px 4px 0",
			"width": "100%",
		},
		children=[
			block("a", text="Home", attrs={"href": "/"}, styles=dict(crumb)),
			block("span", text="/", styles=dict(crumb)),
			block("a", text="Products", attrs={"href": "/products"}, styles=dict(crumb)),
			block("span", text="/", styles=dict(crumb)),
			block("span", text="Product", styles={**crumb, "color": refs["ink"]}, dynamicValues=[dv(trail_key, "innerHTML")]),
		],
	)


def pdp_gallery(refs):
	thumb = block(
		"img",
		name="Thumbnail",
		attrs={
			"src": "/assets/builder/images/fallback.png",
			"alt": "",
			"loading": "lazy",
			"data-shop": "thumb",
			"data-selected": "false",
		},
		styles={
			"aspectRatio": "1 / 1",
			"backgroundColor": refs["card"],
			"borderColor": refs["line"],
			"borderRadius": "10px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"cursor": "pointer",
			"display": "block",
			"objectFit": "cover",
			"width": "66px",
		},
		dynamicValues=[
			dv("image", "src", "attribute"),
			dv("image", "data-image", "attribute"),
			dv("alt_text", "alt", "attribute"),
		],
	)
	return block(
		"div",
		name="Gallery",
		styles={"display": "flex", "flexDirection": "column", "gap": "12px", "width": "100%"},
		children=[
			block(
				"div",
				name="Image Well",
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["card"],
					"borderRadius": "16px",
					"display": "flex",
					"overflow": "hidden",
					"width": "100%",
				},
				children=[
					block(
						"img",
						name="Main Image",
						attrs={
							"src": "/assets/builder/images/fallback.png",
							"alt": "",
							"loading": "eager",
							"data-shop": "main-image",
						},
						styles={"display": "block", "height": "100%", "objectFit": "cover", "width": "100%"},
						dynamicValues=[
							dv("product.image", "src", "attribute"),
							dv("product.product_name", "alt", "attribute"),
						],
					)
				],
			),
			repeater(
				"product.images",
				thumb,
				{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "10px", "width": "100%"},
				name="Thumbnails",
			),
		],
	)


def pdp_price(refs):
	price_row = block(
		"div",
		styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "12px", "width": "100%"},
		children=[
			block(
				"p",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles=mono(size="26px", weight="500", color=refs["ink"], spacing="-0.01em", upper=False),
				dynamicValues=[dv("product.formatted_price", "innerHTML")],
			),
			block(
				"span",
				text="",
				visibilityCondition={"key": "product.formatted_compare_at", "comesFrom": "dataScript"},
				styles={
					**mono(size="13px", color=refs["muted"], spacing="0.04em", upper=False),
					"textDecoration": "line-through",
				},
				dynamicValues=[dv("product.formatted_compare_at", "innerHTML")],
			),
			block(
				"div",
				attrs={"data-shop": "pdp-discount"},
				visibilityCondition={"key": "product.discount_pct", "comesFrom": "dataScript"},
				styles={
					"borderColor": refs["accent"],
					"borderRadius": "999px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"display": "flex",
					"flexDirection": "row",
					"padding": "3px 10px",
					"width": "fit-content",
				},
				children=[
					run(refs, [(True, "product.discount_pct"), (False, "% OFF")], size="10px", color=refs["accent"], family=MONO)
				],
			),
		],
	)
	savings = block(
		"div",
		attrs={"data-shop": "pdp-savings"},
		visibilityCondition={"key": "product.formatted_savings", "comesFrom": "dataScript"},
		styles={"display": "flex", "flexDirection": "row", "width": "fit-content"},
		children=[
			run(refs, [(False, "You save "), (True, "product.formatted_savings")], size="11px", color=refs["accent"], family=MONO)
		],
	)
	return block(
		"div",
		name="Price",
		styles={"display": "flex", "flexDirection": "column", "gap": "6px", "width": "100%"},
		children=[price_row, savings],
	)


def pdp_details(refs):
	option_button = block(
		"button",
		name="Option",
		text="Value",
		attrs={"type": "button", "data-shop": "variant-option"},
		styles={
			"backgroundColor": refs["paper"],
			"borderColor": refs["line"],
			"borderRadius": "999px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontFamily": MONO,
			"fontSize": "11px",
			"letterSpacing": "0.06em",
			"minWidth": "46px",
			"padding": "10px 16px",
			"width": "fit-content",
		},
		dynamicValues=[
			dv("value", "innerHTML"),
			dv("attribute", "data-attribute", "attribute"),
			dv("value", "data-value", "attribute"),
		],
	)
	attribute_group = block(
		"div",
		name="Attribute",
		styles={"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
		children=[
			block(
				"p",
				text="Attribute",
				styles=mono(size="10px", color=refs["muted"], spacing="0.16em"),
				dynamicValues=[dv("attribute", "innerHTML")],
			),
			repeater(
				"values",
				option_button,
				{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "8px", "width": "100%"},
				name="Options",
			),
		],
	)
	stock_line = block(
		"div",
		name="Stock",
		visibilityCondition={"key": "product.in_stock", "comesFrom": "dataScript"},
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "8px", "width": "fit-content"},
		children=[
			block(
				"span",
				styles={"backgroundColor": refs["success"], "borderRadius": "50%", "flexShrink": 0, "height": "7px", "width": "7px"},
			),
			block("span", text="In stock, ready to dispatch", styles=mono(size="10px", color=refs["ink"], spacing="0.12em")),
		],
	)
	highlight = block(
		"span",
		name="Highlight",
		text="Highlight",
		styles={
			"borderColor": refs["line"],
			"borderRadius": "999px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontFamily": MONO,
			"fontSize": "10px",
			"height": "fit-content",
			"letterSpacing": "0.08em",
			"padding": "6px 13px",
			"width": "fit-content",
		},
		dynamicValues=[dv("label", "innerHTML")],
	)
	buy_button = lambda name, text, hook, styles: block(
		"button",
		name=name,
		text=text,
		attrs={
			"type": "button",
			"data-shop": hook,
			"data-label": text,
			"data-added-label": "Added",
			"data-out-of-stock-label": "Out of stock",
		},
		styles=styles,
		dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
	)
	actions = block(
		"div",
		name="Actions",
		styles={"display": "flex", "flexDirection": "row", "gap": "10px", "width": "100%"},
		mobile={"flexDirection": "column"},
		children=[
			buy_button(
				"Add to cart",
				"Add to cart",
				"add-to-cart",
				{**pill(refs, "", variant="outline", full=True)["baseStyles"], "flexGrow": "1"},
			),
			buy_button("Buy now", "Buy now", "buy-now", {**pill(refs, "", full=True)["baseStyles"], "flexGrow": "1"}),
		],
	)
	return block(
		"div",
		name="Details",
		styles={"display": "flex", "flexDirection": "column", "gap": "18px", "width": "100%"},
		children=[
			block(
				"h1",
				text="Product",
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "30px",
					"fontWeight": "500",
					"height": "fit-content",
					"letterSpacing": "-0.02em",
					"lineHeight": "1.15",
					"width": "100%",
				},
				mobile={"fontSize": "24px"},
				dynamicValues=[dv("product.product_name", "innerHTML")],
			),
			pdp_rating_row(refs),
			pdp_price(refs),
			repeater(
				"product.attribute_options",
				attribute_group,
				{"display": "flex", "flexDirection": "column", "gap": "16px", "width": "100%"},
				name="Variant Picker",
			),
			stock_line,
			repeater(
				"product.highlights",
				highlight,
				{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "8px", "width": "100%"},
				name="Highlights",
			),
			actions,
			error_banner(refs),
			component_ref("dot-delivery-card"),
			block(
				"p",
				text="",
				visibilityCondition={"key": "product.description_text", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "lineHeight": "1.7", "width": "100%"},
				dynamicValues=[dv("product.description_text", "innerHTML")],
			),
			component_ref("dot-trust-row"),
		],
	)


def pdp_rating_row(refs):
	return block(
		"div",
		name="Rating",
		visibilityCondition={"key": "product.rating.count", "comesFrom": "dataScript"},
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "8px", "width": "fit-content"},
		children=[
			stars_span(refs, "product.rating.stars", size="13px"),
			block(
				"span",
				text="",
				styles=mono(size="11px", color=refs["ink"], spacing="0.06em", upper=False),
				dynamicValues=[dv("product.rating.average", "innerHTML")],
			),
			block(
				"a",
				text="Read reviews",
				attrs={"href": "#reviews"},
				styles={**mono(size="10px", color=refs["muted"], spacing="0.12em"), "textDecoration": "underline"},
			),
		],
	)


def rating_summary(refs):
	histogram_row = block(
		"div",
		name="Histogram Row",
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "12px", "width": "100%"},
		children=[
			block(
				"span",
				text="5",
				styles={**mono(size="11px", color=refs["muted"], spacing="0.04em", upper=False), "flexShrink": 0, "width": "10px"},
				dynamicValues=[dv("stars", "innerHTML")],
			),
			block(
				"div",
				styles={
					"backgroundColor": refs["line"],
					"borderRadius": "999px",
					"flexGrow": "1",
					"height": "4px",
					"overflow": "hidden",
					"width": "100%",
				},
				children=[
					block(
						"div",
						styles={"backgroundColor": refs["ink"], "height": "100%", "width": "0%"},
						dynamicValues=[dv("width", "width", "style")],
					)
				],
			),
			block(
				"span",
				text="0",
				styles={
					**mono(size="11px", color=refs["muted"], spacing="0.04em", upper=False),
					"flexShrink": 0,
					"minWidth": "18px",
					"textAlign": "right",
				},
				dynamicValues=[dv("count", "innerHTML")],
			),
		],
	)
	return block(
		"div",
		name="Rating Summary",
		styles={"display": "flex", "flexDirection": "column", "gap": "10px", "height": "fit-content", "width": "100%"},
		children=[
			block(
				"p",
				text="",
				styles=mono(size="52px", weight="500", color=refs["ink"], spacing="-0.03em", upper=False),
				mobile={"fontSize": "40px"},
				dynamicValues=[dv("reviews.average", "innerHTML")],
			),
			stars_span(refs, "product.rating.stars", size="14px"),
			run(refs, [(False, "Based on "), (True, "reviews.count"), (False, " reviews")], size="10px", family=MONO),
			repeater(
				"reviews.histogram",
				histogram_row,
				{"display": "flex", "flexDirection": "column", "gap": "9px", "marginTop": "8px", "width": "100%"},
				name="Histogram",
			),
		],
	)


def reviews_panel(refs):
	node = panel(
		refs,
		[
			section_head(refs, "( Reviews )", "Ratings and reviews"),
			block(
				"div",
				styles={
					"display": "grid",
					"gap": "64px",
					"gridTemplateColumns": "minmax(0, 280px) minmax(0, 1fr)",
					"width": "100%",
				},
				mobile={"gap": "24px", "gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					rating_summary(refs),
					repeater(
						"reviews.reviews",
						component_ref("dot-review-card"),
						{"display": "flex", "flexDirection": "column", "marginTop": "-20px", "width": "100%"},
						name="Review List",
					),
				],
			),
		],
		name="Section · Reviews",
	)
	node["attributes"]["id"] = "reviews"
	node["visibilityCondition"] = {"key": "reviews.count", "comesFrom": "dataScript"}
	return node


def review_form_panel(refs):
	star = lambda value: block(
		"button",
		text="★",
		attrs={
			"type": "button",
			"data-shop": "rating-star",
			"data-value": str(value),
			"data-selected": "false",
			"aria-label": f"{value} out of 5 stars",
		},
		styles={
			"backgroundColor": "transparent",
			"borderWidth": "0px",
			"color": refs["line"],
			"fontSize": "24px",
			"lineHeight": "1",
			"padding": "0",
			"width": "fit-content",
		},
	)
	form = block(
		"form",
		name="Review Form",
		attrs={"data-shop": "review-form"},
		styles={"display": "none", "flexDirection": "column", "gap": "10px", "maxWidth": "520px", "width": "100%"},
		children=[
			block(
				"div",
				name="Rating Stars",
				styles={"display": "flex", "flexDirection": "row", "gap": "4px"},
				children=[star(value) for value in range(1, 6)],
			),
			input_block(refs, "title", "Title (optional)"),
			block(
				"textarea",
				attrs={"name": "review", "rows": "4", "placeholder": "What did you think?"},
				styles=field_styles(refs),
			),
			pill(refs, "Submit review", attrs={"type": "submit"}),
		],
	)
	return panel(
		refs,
		[
			section_head(refs, "( Write )", "Share your experience"),
			error_banner(refs),
			block(
				"a",
				name="Review Sign-in",
				text="Sign in to write a review",
				attrs={"data-shop": "review-signin", "href": "/login"},
				styles={**mono(size="11px", color=refs["ink"], spacing="0.12em"), "textDecoration": "underline"},
			),
			form,
		],
		styles={"gap": "18px"},
		name="Section · Write a Review",
	)


def buy_bar(refs):
	price = block(
		"span",
		text="",
		attrs={"data-shop": "pdp-price"},
		styles=mono(size="14px", weight="500", color=refs["ink"], spacing="0.02em", upper=False),
		dynamicValues=[dv("product.formatted_price", "innerHTML")],
	)
	buy = block(
		"button",
		name="Bar Buy Now",
		text="Buy now",
		attrs={
			"type": "button",
			"data-shop": "buy-now",
			"data-label": "Buy now",
			"data-out-of-stock-label": "Out of stock",
		},
		styles={**pill(refs, "")["baseStyles"], "padding": "12px 26px"},
		dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
	)
	return block(
		"div",
		name="Buy Bar",
		classes=["pdp-buybar"],
		children=[block("div", classes=["pdp-buybar-inner"], children=[price, buy])],
	)


def product_blocks(refs):
	main = panel(
		refs,
		[
			block(
				"div",
				styles={
					"display": "grid",
					"gap": "48px",
					"gridTemplateColumns": "minmax(0, 1fr) minmax(0, 1fr)",
					"width": "100%",
				},
				mobile={"gap": "26px", "gridTemplateColumns": "minmax(0, 1fr)"},
				children=[pdp_gallery(refs), pdp_details(refs)],
			)
		],
		name="Section · Product",
	)
	related = panel(
		refs,
		[
			section_head(refs, "( More )", "You may also like", "All products →", "/products"),
			product_grid(refs, "related_products", "related"),
		],
		name="Section · Related",
	)
	blocks = shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([breadcrumb(refs, "product.product_name"), main, reviews_panel(refs), review_form_panel(refs), related]),
			component_ref("dot-footer"),
			buy_bar(refs),
		],
	)
	blocks[0]["baseStyles"]["paddingBottom"] = "72px"
	return blocks


def cart_blocks(refs):
	qty_button = {
		"alignItems": "center",
		"backgroundColor": refs["paper"],
		"borderColor": refs["line"],
		"borderRadius": "999px",
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["ink"],
		"display": "flex",
		"fontSize": "13px",
		"height": "28px",
		"justifyContent": "center",
		"width": "28px",
	}
	line_item = block(
		"div",
		name="Line Item",
		styles={
			"alignItems": "center",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "16px",
			"padding": "18px 0",
			"width": "100%",
		},
		mobile={"gap": "10px"},
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["card"],
					"borderRadius": "10px",
					"display": "block",
					"objectFit": "cover",
					"width": "58px",
				},
				dynamicValues=[dv("image", "src", "attribute"), dv("product_name", "alt", "attribute")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "flexGrow": "1", "gap": "4px"},
				children=[
					block(
						"h3",
						text="Product",
						styles={"fontSize": "14px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("product_name", "innerHTML")],
					),
					block(
						"p",
						text="",
						styles=mono(size="11px", color=refs["muted"], spacing="0.04em", upper=False),
						dynamicValues=[dv("formatted_rate", "innerHTML")],
					),
				],
			),
			block(
				"div",
				name="Qty",
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "8px"},
				children=[
					block(
						"button",
						text="−",
						attrs={"type": "button", "data-shop": "qty-dec", "aria-label": "Decrease quantity"},
						styles=dict(qty_button),
						dynamicValues=[dv("item_code", "data-item-code", "attribute")],
					),
					block(
						"span",
						text="1",
						styles={**mono(size="12px", color=refs["ink"], spacing="0", upper=False), "minWidth": "18px", "textAlign": "center"},
						dynamicValues=[dv("qty", "innerHTML")],
					),
					block(
						"button",
						text="+",
						attrs={"type": "button", "data-shop": "qty-inc", "aria-label": "Increase quantity"},
						styles=dict(qty_button),
						dynamicValues=[dv("item_code", "data-item-code", "attribute")],
					),
				],
			),
			block(
				"p",
				text="",
				styles={
					**mono(size="13px", weight="500", color=refs["ink"], spacing="0.02em", upper=False),
					"minWidth": "84px",
					"textAlign": "right",
				},
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
			block(
				"button",
				text="Remove",
				attrs={"type": "button", "data-shop": "remove"},
				styles={
					**mono(size="10px", color=refs["muted"], spacing="0.12em"),
					"backgroundColor": "transparent",
					"borderWidth": "0px",
					"textDecoration": "underline",
				},
				dynamicValues=[dv("item_code", "data-item-code", "attribute")],
			),
		],
	)
	cart_panel = panel(
		refs,
		[
			block(
				"p",
				text="Your cart is empty.",
				visibilityCondition={"key": "cart.is_empty", "comesFrom": "dataScript"},
				styles=mono(size="12px", color=refs["muted"], spacing="0.12em"),
			),
			repeater(
				"cart.items",
				line_item,
				{"display": "flex", "flexDirection": "column", "marginTop": "-18px", "width": "100%"},
				name="Line Items",
			),
			block(
				"div",
				name="Totals",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				styles={"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
				children=[
					money_row(refs, "Subtotal", bound_key="cart.formatted_subtotal"),
					discount_row(refs, "cart.formatted_discount", "cart.coupon.code"),
					money_row(refs, "Total", bound_key="cart.formatted_total", strong=True),
					pill(refs, "Checkout", href="/checkout", full=True),
				],
			),
		],
		name="Section · Cart",
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([page_header(refs, "( Cart )", "Your cart"), error_banner(refs), cart_panel]),
			component_ref("dot-footer"),
		],
	)


def submit_button(refs, text):
	node = pill(refs, text, attrs={"type": "submit"}, full=True)
	node["baseStyles"].update({"gridColumn": "span 2", "marginTop": "10px"})
	return node


def input_block(refs, name, label_text, input_type="text", required=False, half=False, prefill=False):
	attrs = {"type": input_type, "name": name, "placeholder": label_text}
	if required:
		attrs["required"] = "required"
	return block(
		"input",
		name=f"Input · {name}",
		attrs=attrs,
		dynamicValues=[dv(f"prefill.{name}", "value", "attribute")] if prefill else [],
		styles={**field_styles(refs), "gridColumn": "span 1" if half else "span 2"},
	)


def coupon_box(refs):
	form = block(
		"form",
		name="Coupon Form",
		attrs={"data-shop": "coupon-form"},
		styles={"display": "flex", "flexDirection": "row", "gap": "8px", "width": "100%"},
		children=[
			block(
				"input",
				attrs={"type": "text", "name": "code", "placeholder": "Coupon code"},
				styles={**field_styles(refs, radius="999px"), "flexGrow": "1", "minWidth": "0px"},
			),
			pill(refs, "Apply", variant="outline", attrs={"type": "submit"}),
		],
	)
	applied = block(
		"div",
		name="Coupon Applied",
		visibilityCondition={"key": "cart.coupon.code", "comesFrom": "dataScript"},
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "10px", "width": "100%"},
		children=[
			block(
				"p",
				text="",
				styles={
					**mono(size="10px", weight="500", color=refs["ink"], spacing="0.12em"),
					"backgroundColor": refs["card"],
					"borderRadius": "999px",
					"padding": "5px 12px",
				},
				dynamicValues=[dv("cart.coupon.code", "innerHTML")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "flexGrow": "1", "justifyContent": "flex-end"},
				children=[
					run(refs, [(False, "−"), (True, "cart.coupon.formatted_discount")], size="12px", color=refs["accent"], family=MONO)
				],
			),
			block(
				"button",
				text="Remove",
				attrs={"type": "button", "data-shop": "coupon-remove"},
				styles={
					**mono(size="10px", color=refs["muted"], spacing="0.12em"),
					"backgroundColor": "transparent",
					"borderWidth": "0px",
					"textDecoration": "underline",
				},
			),
		],
	)
	return block(
		"div",
		name="Coupon",
		styles={
			"borderTopColor": refs["line"],
			"borderTopStyle": "solid",
			"borderTopWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"paddingTop": "16px",
			"width": "100%",
		},
		children=[form, applied],
	)


def checkout_blocks(refs):
	payment_option = block(
		"label",
		name="Payment Method",
		styles={
			"alignItems": "center",
			"borderColor": refs["line"],
			"borderRadius": "999px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "10px",
			"padding": "12px 18px",
			"width": "100%",
		},
		children=[
			block(
				"input",
				attrs={"type": "radio", "name": "payment_method"},
				styles={"accentColor": refs["ink"], "height": "14px", "width": "14px"},
				dynamicValues=[dv("method", "value", "attribute")],
			),
			block(
				"span",
				text="Payment",
				styles=mono(size="11px", color=refs["ink"], spacing="0.1em"),
				dynamicValues=[dv("label", "innerHTML")],
			),
		],
	)
	form = block(
		"form",
		name="Checkout Form",
		attrs={"data-shop": "checkout-form"},
		styles={"display": "grid", "gap": "10px", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "width": "100%"},
		children=[
			block("p", text="Contact", styles={**mono(size="10px", color=refs["muted"], spacing="0.16em"), "gridColumn": "span 2"}),
			input_block(refs, "email", "Email address", "email", required=True, prefill=True),
			block(
				"p",
				text="Shipping address",
				styles={
					**mono(size="10px", color=refs["muted"], spacing="0.16em"),
					"gridColumn": "span 2",
					"marginTop": "12px",
				},
			),
			block(
				"div",
				name="Saved Addresses",
				visibilityCondition={"key": "has_addresses", "comesFrom": "dataScript"},
				styles={"display": "flex", "gridColumn": "span 2", "width": "100%"},
				children=[
					repeater(
						"addresses",
						block(
							"option",
							text="Address",
							dynamicValues=[dv("name", "value", "attribute"), dv("line", "innerHTML")],
						),
						field_styles(refs),
						element="select",
						attrs={"data-shop": "address-picker", "aria-label": "Saved addresses"},
					)
				],
			),
			input_block(refs, "full_name", "Full name", required=True, prefill=True),
			input_block(refs, "phone", "Phone", "tel", prefill=True),
			input_block(refs, "address_line1", "Address", required=True, prefill=True),
			input_block(refs, "address_line2", "Apartment, suite, etc. (optional)", prefill=True),
			input_block(refs, "city", "City", required=True, half=True, prefill=True),
			input_block(refs, "state", "State", half=True, prefill=True),
			input_block(refs, "pincode", "Pincode", half=True, prefill=True),
			input_block(refs, "country", "Country", half=True, prefill=True),
			block(
				"p",
				text="Payment",
				styles={
					**mono(size="10px", color=refs["muted"], spacing="0.16em"),
					"gridColumn": "span 2",
					"marginTop": "12px",
				},
			),
			repeater(
				"payment_methods",
				payment_option,
				{"display": "flex", "flexDirection": "column", "gap": "8px", "gridColumn": "span 2", "width": "100%"},
				name="Payment Methods",
			),
			block(
				"p",
				text="You will be redirected to a secure payment gateway to complete your purchase.",
				attrs={"data-shop": "gateway-note", "hidden": "hidden"},
				styles={
					"color": refs["muted"],
					"fontSize": "12px",
					"gridColumn": "span 2",
					"height": "fit-content",
					"lineHeight": "1.5",
					"width": "100%",
				},
			),
			submit_button(refs, "Place order"),
		],
	)
	summary_row = block(
		"div",
		name="Summary Row",
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "12px", "width": "100%"},
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["card"],
					"borderRadius": "8px",
					"display": "block",
					"objectFit": "cover",
					"width": "42px",
				},
				dynamicValues=[dv("image", "src", "attribute"), dv("product_name", "alt", "attribute")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "flexGrow": "1", "gap": "3px"},
				children=[
					block(
						"p",
						text="Item",
						styles={"fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("product_name", "innerHTML")],
					),
					block(
						"p",
						text="",
						styles=mono(size="10px", color=refs["muted"], spacing="0.08em"),
						dynamicValues=[dv("qty", "innerHTML")],
					),
				],
			),
			block(
				"p",
				text="",
				styles=mono(size="12px", weight="500", color=refs["ink"], spacing="0.02em", upper=False),
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
		],
	)
	summary = panel(
		refs,
		[
			label(refs, "Order summary", element="h2"),
			repeater(
				"cart.items",
				summary_row,
				{"display": "flex", "flexDirection": "column", "gap": "14px", "width": "100%"},
				name="Summary Items",
			),
			coupon_box(refs),
			block(
				"div",
				styles={
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"gap": "10px",
					"paddingTop": "16px",
					"width": "100%",
				},
				children=[
					money_row(refs, "Subtotal", bound_key="cart.formatted_subtotal"),
					discount_row(refs, "cart.formatted_discount", "cart.coupon.code"),
					money_row(refs, "Shipping", bound_key="cart.formatted_shipping", static_value="Free"),
					money_row(refs, "Total", bound_key="cart.formatted_total", strong=True),
				],
			),
			block(
				"p",
				text="Secure checkout · 14 day easy returns",
				styles={**mono(size="9px", color=refs["muted"], spacing="0.14em"), "textAlign": "center", "width": "100%"},
			),
		],
		styles={"gap": "18px", "height": "fit-content"},
		name="Summary",
	)
	empty = panel(
		refs,
		[
			block("p", text="Your cart is empty.", styles=mono(size="12px", color=refs["ink"], spacing="0.12em")),
			pill(refs, "Continue shopping", href="/products", variant="outline"),
		],
		styles={"alignItems": "center", "gap": "16px", "padding": "60px 40px"},
		name="Empty Checkout",
	)
	empty["visibilityCondition"] = {"key": "cart.is_empty", "comesFrom": "dataScript"}
	grid = block(
		"div",
		visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
		styles={
			"display": "grid",
			"gap": "16px",
			"gridTemplateColumns": "minmax(0, 3fr) minmax(0, 2fr)",
			"width": "100%",
		},
		mobile={"gap": "12px", "gridTemplateColumns": "minmax(0, 1fr)"},
		children=[panel(refs, [form], name="Section · Checkout Form"), summary],
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([page_header(refs, "( Checkout )", "Checkout"), error_banner(refs), empty, grid]),
			component_ref("dot-footer"),
		],
	)


def confirmation_blocks(refs):
	item_row = block(
		"div",
		name="Order Item",
		styles={
			"alignItems": "center",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "12px 0",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "gap": "10px"},
				children=[
					block(
						"p",
						text="Item",
						styles={"fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("item_name", "innerHTML")],
					),
					block(
						"p",
						text="",
						styles=mono(size="10px", color=refs["muted"], spacing="0.08em"),
						dynamicValues=[dv("qty", "innerHTML")],
					),
				],
			),
			block(
				"p",
				text="",
				styles=mono(size="12px", weight="500", color=refs["ink"], spacing="0.02em", upper=False),
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
		],
	)
	progress_stage = block(
		"div",
		name="Progress Stage",
		classes=["progress-stage"],
		attrs={"data-shop": "progress-stage"},
		dynamicValues=[dv("done", "data-done", "attribute")],
		children=[
			block("span", classes=["stage-dot"]),
			block("p", text="Stage", classes=["stage-label"], dynamicValues=[dv("label", "innerHTML")]),
		],
	)
	progress = repeater(
		"order.progress",
		progress_stage,
		{"display": "flex", "flexDirection": "row", "width": "100%"},
		name="Order Progress",
		attrs={"data-shop": "order-progress"},
	)
	tile_body = lambda text, **extra: block(
		"p",
		text=text,
		styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.55", "width": "100%"},
		**extra,
	)
	info_tile = lambda title, body, **extra: inset(
		refs,
		[block("p", text=title, styles=mono(size="10px", color=refs["ink"], spacing="0.14em")), tile_body(body)],
		**extra,
	)
	delivery_tile = inset(
		refs,
		[
			block("p", text="Delivery", styles=mono(size="10px", color=refs["ink"], spacing="0.14em")),
			tile_body(
				"Your order is with the courier.",
				dynamicValues=[dv("order.shipment.line", "innerHTML")],
				visibilityCondition={"key": "order.shipment.line", "comesFrom": "dataScript"},
			),
			block(
				"a",
				text="Track shipment",
				attrs={"target": "_blank", "rel": "noopener"},
				styles={**mono(size="10px", color=refs["ink"], spacing="0.12em"), "textDecoration": "underline"},
				dynamicValues=[dv("order.shipment.tracking_url", "href", "attribute")],
				visibilityCondition={"key": "order.shipment.tracking_url", "comesFrom": "dataScript"},
			),
		],
		name="Delivery Tile",
		visibilityCondition={"key": "order.shipment", "comesFrom": "dataScript"},
	)
	order_panel = panel(
		refs,
		[
			progress,
			block(
				"div",
				styles={
					"alignItems": "baseline",
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"paddingTop": "22px",
					"width": "100%",
				},
				children=[
					label(refs, "Order summary", element="h2"),
					block(
						"p",
						text="Order",
						styles=mono(size="10px", color=refs["muted"], spacing="0.1em"),
						dynamicValues=[dv("order.name", "innerHTML")],
					),
				],
			),
			repeater(
				"order.items",
				item_row,
				{"display": "flex", "flexDirection": "column", "marginTop": "-14px", "width": "100%"},
				name="Order Items",
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
				children=[
					money_row(refs, "Subtotal", bound_key="order.formatted_total"),
					discount_row(refs, "order.formatted_discount", "order.formatted_discount"),
					money_row(refs, "Shipping", bound_key="order.formatted_shipping", static_value="Free"),
					money_row(refs, "Total", bound_key="order.formatted_grand_total", strong=True),
				],
			),
			block(
				"div",
				styles={"display": "grid", "gap": "12px", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "width": "100%"},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					info_tile(
						"Shipping",
						"Your order ships in 48 hours. We will email you the tracking number.",
						name="Shipping Tile",
						visibilityCondition={"key": "order.awaiting_shipment", "comesFrom": "dataScript"},
					),
					delivery_tile,
					info_tile("Receipt", "A confirmation for this order has been sent to your email address."),
				],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "10px", "width": "100%"},
				children=[
					pill(refs, "Track my order", href="/account/orders"),
					pill(refs, "Continue shopping", href="/products", variant="outline"),
				],
			),
		],
		name="Section · Order",
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack(
				[
					page_header(
						refs,
						"( Confirmed )",
						"Thank you for your order!",
						"Your order is confirmed. A copy with tracking details is on its way to your email.",
					),
					order_panel,
					returns_panel(refs),
				]
			),
			component_ref("dot-footer"),
		],
	)


def returns_panel(refs):
	request_row = block(
		"div",
		name="Return Request",
		styles={
			"alignItems": "baseline",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "12px",
			"justifyContent": "space-between",
			"padding": "12px 0",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "gap": "4px"},
				children=[
					block(
						"p",
						text="Request",
						styles={"fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("line", "innerHTML")],
					),
					block(
						"p",
						text="",
						visibilityCondition={"key": "resolution_note", "comesFrom": "dataScript"},
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.5", "width": "100%"},
						dynamicValues=[dv("resolution_note", "innerHTML")],
					),
				],
			),
			block(
				"p",
				text="Requested",
				styles=mono(size="10px", color=refs["muted"], spacing="0.12em"),
				dynamicValues=[dv("status", "innerHTML")],
			),
		],
	)
	item_option = block(
		"option",
		text="Item",
		dynamicValues=[dv("item_code", "value", "attribute"), dv("item_name", "innerHTML")],
	)
	form = block(
		"form",
		name="Return Form",
		attrs={"data-shop": "return-form"},
		visibilityCondition={"key": "order.returns.eligible", "comesFrom": "dataScript"},
		styles={"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
		children=[
			block(
				"p",
				text="Something not right? You have 14 days from shipping to ask for a return or a replacement.",
				styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.55", "width": "100%"},
			),
			block(
				"div",
				styles={"display": "grid", "gap": "10px", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "width": "100%"},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					repeater(
						"order.items",
						item_option,
						field_styles(refs),
						element="select",
						name="Item Select",
						attrs={"name": "item_code"},
					),
					block(
						"select",
						attrs={"name": "request_type"},
						styles=field_styles(refs),
						children=[
							block("option", text="Return", attrs={"value": "Return"}),
							block("option", text="Replacement", attrs={"value": "Replacement"}),
						],
					),
				],
			),
			block(
				"textarea",
				attrs={"name": "reason", "placeholder": "What went wrong?", "rows": "3", "required": "required"},
				styles=field_styles(refs),
			),
			pill(refs, "Submit request", variant="outline", attrs={"type": "submit"}),
		],
	)
	requests = repeater(
		"order.returns.requests",
		request_row,
		{"display": "flex", "flexDirection": "column", "width": "100%"},
		name="Return Requests",
		visibilityCondition={"key": "order.returns.has_requests", "comesFrom": "dataScript"},
	)
	node = panel(
		refs,
		[label(refs, "Returns & replacements", element="h2"), requests, form],
		styles={"gap": "18px"},
		name="Returns Panel",
	)
	node["visibilityCondition"] = {"key": "order.returns.show", "comesFrom": "dataScript"}
	return node


def account_blocks(refs):
	order_row = block(
		"a",
		name="Order Row",
		attrs={"data-shop": "order-link"},
		dynamicValues=[dv("url", "href", "attribute")],
		styles={
			"alignItems": "center",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"color": refs["ink"],
			"display": "grid",
			"gap": "16px",
			"gridTemplateColumns": "2fr 1fr 1fr 1fr",
			"padding": "16px 0",
			"textDecoration": "none",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "1fr 1fr"},
		children=[
			block(
				"p",
				text="Order",
				styles=mono(size="11px", weight="500", color=refs["ink"], spacing="0.06em", upper=False),
				dynamicValues=[dv("name", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles=mono(size="10px", color=refs["muted"], spacing="0.08em"),
				dynamicValues=[dv("formatted_date", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles=mono(size="10px", color=refs["success"], spacing="0.12em"),
				dynamicValues=[dv("display_status", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={
					**mono(size="12px", weight="500", color=refs["ink"], spacing="0.02em", upper=False),
					"justifySelf": "end",
				},
				dynamicValues=[dv("formatted_total", "innerHTML")],
			),
		],
	)
	orders_panel = panel(
		refs,
		[
			repeater(
				"orders",
				order_row,
				{"display": "flex", "flexDirection": "column", "marginTop": "-16px", "width": "100%"},
				name="Orders",
			)
		],
		name="Section · Orders",
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([page_header(refs, "( Account )", "Your orders"), orders_panel]),
			component_ref("dot-footer"),
		],
	)


def about_blocks(refs):
	stat = lambda value, text: block(
		"div",
		styles={"display": "flex", "flexDirection": "column", "gap": "6px", "width": "100%"},
		children=[
			block("p", text=value, styles=mono(size="26px", weight="500", color=refs["ink"], spacing="-0.02em", upper=False)),
			block("p", text=text, styles=mono(size="10px", color=refs["muted"], spacing="0.14em")),
		],
	)
	content = panel(
		refs,
		[
			prose(
				refs,
				"This store exists for one reason: objects worth keeping. Considered materials, "
				"a fit that survives real use, and small runs that are never overproduced.",
				size="15px",
				width="min(620px, 100%)",
			),
			prose(
				refs,
				"We keep our margins honest and stand behind everything we sell. If something is "
				"not right, write to us and we will fix it.",
				size="15px",
				width="min(620px, 100%)",
			),
			block(
				"div",
				styles={
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "grid",
					"gap": "24px",
					"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
					"paddingTop": "28px",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[stat("2020", "Founded"), stat("120+", "Products shipped"), stat("48h", "Dispatch time")],
			),
		],
		name="Section · About",
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([page_header(refs, "( About )", "Everything here earns its place."), content]),
			component_ref("dot-footer"),
		],
	)


def contact_blocks(refs):
	detail = lambda text, value: block(
		"div",
		styles={
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "16px 0",
			"width": "100%",
		},
		children=[
			block("p", text=text, styles=mono(size="10px", color=refs["muted"], spacing="0.14em")),
			block("p", text=value, styles=mono(size="11px", color=refs["ink"], spacing="0.04em", upper=False)),
		],
	)
	content = panel(
		refs,
		[
			prose(refs, "Questions about an order, a product or anything else. We reply within a day.", size="15px", width="min(520px, 100%)"),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "width": "100%"},
				children=[
					detail("Email", "hello@example.com"),
					detail("Phone", "+91 98765 43210"),
					detail("Hours", "Mon to Fri, 10:00 to 18:00"),
				],
			),
			pill(refs, "Write to us", href="mailto:hello@example.com"),
		],
		name="Section · Contact",
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([page_header(refs, "( Contact )", "Say hello."), content]),
			component_ref("dot-footer"),
		],
	)


FAQS = [
	("How long does delivery take?", "Orders are dispatched within 48 hours and usually arrive in 3 to 5 working days."),
	(
		"Can I return a product?",
		"Yes, within 14 days of delivery, unused and in its original packaging. Ask for a return from your order page and we will arrange a pickup.",
	),
	("How do sizes run?", "True to size with a modern fit. If you are between sizes, size up for a relaxed fit."),
	("How do I pay?", "You can pay online or choose cash on delivery at checkout."),
	("How do I track my order?", "Sign in with the email you used at checkout and open Account in the navigation."),
]


def faq_blocks(refs):
	entry = lambda question, answer: block(
		"div",
		styles={
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "8px",
			"padding": "20px 0",
			"width": "100%",
		},
		children=[
			block(
				"h3",
				text=question,
				styles={"fontSize": "15px", "fontWeight": "500", "height": "fit-content", "width": "100%"},
			),
			prose(refs, answer, size="13px"),
		],
	)
	content = panel(
		refs,
		[
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "width": "100%"},
				children=[entry(question, answer) for question, answer in FAQS],
			),
			utility_row(refs, "Still stuck? Talk to support", "/contact"),
		],
		name="Section · FAQ",
	)
	return shell(
		refs,
		[
			component_ref("dot-navbar"),
			stack([page_header(refs, "( FAQ )", "Questions, answered."), content]),
			component_ref("dot-footer"),
		],
	)
