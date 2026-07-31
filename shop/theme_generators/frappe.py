"""Frappe: crisp merch storefront. White canvas, hairline rules, serif display moments, rectangular geometry."""

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

GROUP = "frappe"
HEAD = "Source Serif 4"
BODY = "Inter"

PALETTE = {
	"paper": ("#FFFFFF", "#131316"),
	"ink": ("#18181B", "#FAFAFA"),
	"muted": ("#71717A", "#A1A1AA"),
	"line": ("#E4E4E7", "#29292E"),
	"card": ("#F4F4F5", "#1E1E22"),
	"accent": ("#18181B", "#FAFAFA"),
	"badge": ("#C2410C", "#FB923C"),
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
	styles = upsert_client_script("frappe-styles", "CSS", theme_css(refs))
	register_components(refs)
	pages = [
		("frappe-home", "Home", "home", home_blocks(refs), "home", (), False),
		("frappe-products", "Products", "products", products_blocks(refs), "listing", (), False),
		("frappe-product", "Product", "product/:slug", product_blocks(refs), "product_page", ("product",), False),
		("frappe-collection", "Collection", "collection/:slug", collection_blocks(refs), "collection_page", (), False),
		("frappe-cart", "Cart", "cart", cart_blocks(refs), "cart_page", ("cart",), False),
		("frappe-checkout", "Checkout", "checkout", checkout_blocks(refs), "checkout_page", ("cart", "addresses"), False),
		(
			"frappe-order-confirmation",
			"Order Confirmed",
			"order-confirmation/:order_id",
			confirmation_blocks(refs),
			"order_confirmation",
			(),
			False,
		),
		("frappe-account-orders", "Your Orders", "account/orders", account_blocks(refs), "account_orders", (), True),
		("frappe-about", "About", "about", about_blocks(refs), "basic", (), False),
		("frappe-contact", "Contact", "contact", contact_blocks(refs), "basic", (), False),
		("frappe-faq", "FAQ", "faq", faq_blocks(refs), "basic", (), False),
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
	"""Reusable building blocks listed in Builder's insert panel; pages reference them via component_ref."""
	for component_id, component_name, node in [
		("shop-navbar", "Shop Navbar", nav(refs)),
		("shop-footer", "Shop Footer", footer(refs)),
		("shop-cart-drawer", "Shop Cart Drawer", cart_drawer()),
		("shop-hero", "Shop Hero", hero(refs)),
		("shop-product-card", "Shop Product Card", product_card(refs)),
		("shop-collection-tile", "Shop Collection Tile", collection_tile(refs)),
		("shop-filter-bar", "Shop Filter Bar", filter_bar(refs)),
		("shop-review-card", "Shop Review Card", review_card(refs)),
		("shop-delivery-card", "Shop Delivery Promise", delivery_card(refs)),
		("shop-trust-row", "Shop Trust Row", trust_row(refs)),
	]:
		upsert_component(component_id, component_name, node)


def theme_css(refs):
	return f"""
button {{ cursor: pointer; }}
button:disabled {{ opacity: 0.45; cursor: not-allowed; }}
a, button {{ transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease, border-color 0.15s ease; }}
a:hover {{ opacity: 0.7; }}
:focus-visible {{ outline: 2px solid {refs["accent"]}; outline-offset: 2px; }}
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
[data-shop="rating-star"] {{ cursor: pointer; transition: color 0.1s ease; }}
[data-shop="rating-star"][data-selected="true"] {{ color: {refs["badge"]}; }}
input, textarea {{ font-family: inherit; }}
input::placeholder {{ color: {refs["muted"]}; }}
[data-shop="thumb"][data-selected="true"] {{ border-color: {refs["ink"]}; }}
[data-shop="thumb"]:hover {{ border-color: {refs["muted"]}; }}
[data-shop="order-progress"] .progress-stage {{
	align-items: center;
	display: flex;
	flex: 1;
	flex-direction: column;
	gap: 7px;
	position: relative;
}}
[data-shop="order-progress"] .progress-stage::before {{
	background: {refs["line"]};
	content: "";
	height: 1.5px;
	position: absolute;
	right: 50%;
	top: 5px;
	width: 100%;
}}
[data-shop="order-progress"] .progress-stage:first-child::before {{ display: none; }}
[data-shop="order-progress"] .progress-stage[data-done="true"]::before {{ background: {refs["ink"]}; }}
.progress-stage .stage-dot {{
	background: {refs["paper"]};
	border: 1.5px solid {refs["line"]};
	border-radius: 50%;
	height: 11px;
	position: relative;
	width: 11px;
	z-index: 1;
}}
.progress-stage[data-done="true"] .stage-dot {{ background: {refs["ink"]}; border-color: {refs["ink"]}; }}
.progress-stage .stage-label {{ color: {refs["muted"]}; font-size: 11px; }}
.progress-stage[data-done="true"] .stage-label {{ color: {refs["ink"]}; font-weight: 500; }}
[data-shop="cart-drawer"] {{
	position: fixed;
	inset: 0;
	z-index: 90;
	pointer-events: none;
}}
[data-shop="cart-drawer"] .drawer-backdrop {{
	position: absolute;
	inset: 0;
	background: rgba(0, 0, 0, 0.4);
	opacity: 0;
	transition: opacity 0.25s ease;
}}
[data-shop="cart-drawer"] .drawer-panel {{
	position: absolute;
	top: 0;
	right: 0;
	height: 100%;
	width: min(420px, calc(100vw - 32px));
	background: {refs["paper"]};
	color: {refs["ink"]};
	display: flex;
	flex-direction: column;
	transform: translateX(105%);
	transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
	box-shadow: -16px 0 48px rgba(0, 0, 0, 0.16);
}}
[data-shop="cart-drawer"][data-open="true"] {{ pointer-events: auto; }}
[data-shop="cart-drawer"][data-open="true"] .drawer-backdrop {{ opacity: 1; }}
[data-shop="cart-drawer"][data-open="true"] .drawer-panel {{ transform: translateX(0); }}
@media (prefers-reduced-motion: reduce) {{
	[data-shop="cart-drawer"] .drawer-backdrop,
	[data-shop="cart-drawer"] .drawer-panel {{ transition: none; }}
}}
.drawer-header {{
	align-items: center;
	border-bottom: 1px solid {refs["line"]};
	display: flex;
	flex-shrink: 0;
	justify-content: space-between;
	padding: 18px 24px;
}}
.drawer-title {{ font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }}
.drawer-close {{
	background: none;
	border: 0;
	color: {refs["ink"]};
	font-size: 22px;
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
	border-radius: 4px;
	flex-shrink: 0;
	height: 64px;
	object-fit: cover;
	width: 64px;
}}
.drawer-info {{ display: flex; flex: 1; flex-direction: column; gap: 3px; min-width: 0; }}
.drawer-name {{
	color: {refs["ink"]};
	font-size: 13px;
	font-weight: 500;
	line-height: 1.4;
	text-decoration: none;
}}
.drawer-rate {{ color: {refs["muted"]}; font-size: 12px; }}
.drawer-qty {{ align-items: center; display: flex; gap: 8px; margin-top: 8px; }}
.drawer-qty > button {{
	align-items: center;
	background: {refs["paper"]};
	border: 1px solid {refs["line"]};
	border-radius: 2px;
	color: {refs["ink"]};
	display: flex;
	font-size: 13px;
	height: 26px;
	justify-content: center;
	width: 26px;
}}
.drawer-qty > span {{ font-size: 13px; min-width: 16px; text-align: center; }}
.drawer-qty > .drawer-remove {{
	background: none;
	border: 0;
	color: {refs["muted"]};
	font-size: 11px;
	height: auto;
	margin-left: 8px;
	padding: 0;
	text-decoration: underline;
	width: auto;
}}
.drawer-amount {{ flex-shrink: 0; font-size: 13px; font-weight: 600; }}
.drawer-empty {{ color: {refs["muted"]}; font-size: 14px; padding: 40px 0; text-align: center; }}
.drawer-footer {{
	border-top: 1px solid {refs["line"]};
	display: flex;
	flex-direction: column;
	flex-shrink: 0;
	gap: 12px;
	padding: 16px 24px 20px;
}}
.drawer-total-row {{
	display: flex;
	font-size: 14px;
	font-weight: 600;
	justify-content: space-between;
}}
.drawer-note {{ color: {refs["muted"]}; font-size: 12px; margin-top: -6px; }}
.drawer-actions {{ display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }}
.drawer-view, .drawer-checkout {{
	border-radius: 2px;
	font-size: 12px;
	font-weight: 700;
	letter-spacing: 0.08em;
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
	background: {refs["paper"]};
	border-top: 1px solid {refs["line"]};
	bottom: 0;
	left: 0;
	position: fixed;
	right: 0;
	z-index: 80;
}}
.pdp-buybar-inner {{
	align-items: center;
	display: flex;
	gap: 16px;
	justify-content: space-between;
	margin: 0 auto;
	max-width: 1200px;
	padding: 10px 40px;
	width: 100%;
}}
@media (max-width: 640px) {{
	.pdp-buybar-inner {{ padding: 10px 18px; }}
[data-shop="qty-inc"], [data-shop="qty-dec"], [data-drawer-step] {{ min-height: 36px; min-width: 36px; }}
	.drawer-close {{ padding: 10px; margin: -10px; }}
	[data-shop="remove"], .drawer-remove {{ padding: 8px 6px; }}
}}
.pdp-buybar {{ transition: transform 0.25s ease; }}
.pdp-buybar[data-visible="false"] {{ transform: translateY(110%); }}
@media (prefers-reduced-motion: reduce) {{
	.pdp-buybar {{ transition: none; }}
}}
#reviews {{ scroll-margin-top: 24px; }}
"""


def shell(refs, children):
	return [
		root(
			{
				"alignItems": "center",
				"backgroundColor": refs["paper"],
				"color": refs["ink"],
				"display": "flex",
				"flexDirection": "column",
				"flexShrink": 0,
				"fontFamily": BODY,
				"minHeight": "100vh",
				"width": "100%",
			},
			children + [component_ref("shop-cart-drawer")],
		)
	]


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


def named_section(name, children, styles=None, mobile=None):
	return section(children, styles=styles, mobile=mobile, name=name)


def section(children, styles=None, mobile=None, name=None):
	base = {
		"display": "flex",
		"flexDirection": "column",
		"flexShrink": 0,
		"maxWidth": "1200px",
		"padding": "48px 40px",
		"width": "100%",
	}
	base.update(styles or {})
	return block("div", styles=base, mobile=mobile or {"padding": "28px 18px"}, children=children, name=name)


def brand(refs):
	return block(
		"a",
		name="Brand",
		attrs={"href": "/"},
		styles={
			"alignItems": "center",
			"color": refs["ink"],
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
				text="F",
				styles={
					"alignItems": "center",
					"backgroundColor": refs["ink"],
					"borderRadius": "4px",
					"color": refs["paper"],
					"display": "flex",
					"fontFamily": HEAD,
					"fontSize": "14px",
					"fontWeight": "700",
					"height": "24px",
					"justifyContent": "center",
					"width": "24px",
				},
			),
			block(
				"span",
				text="Shop",
				styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("store.name", "innerHTML")],
			),
		],
	)


def nav(refs):
	link_style = {
		"color": refs["ink"],
		"fontSize": "13px",
		"fontWeight": "500",
		"height": "fit-content",
		"textDecoration": "none",
		"width": "fit-content",
	}
	badge = block(
		"span",
		text="0",
		attrs={"data-shop": "cart-count", "data-empty": "true"},
		styles={
			"alignItems": "center",
			"backgroundColor": refs["ink"],
			"borderRadius": "9px",
			"color": refs["paper"],
			"display": "flex",
			"fontSize": "10px",
			"fontWeight": "700",
			"height": "17px",
			"justifyContent": "center",
			"minWidth": "17px",
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
			"gap": "7px",
			"height": "fit-content",
			"textDecoration": "none",
			"width": "fit-content",
		},
		children=[
			block(
				"span",
				text="Cart",
				styles={"fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
			),
			badge,
		],
	)
	return block(
		"div",
		name="Nav",
		styles={
			"alignItems": "center",
			"backgroundColor": refs["paper"],
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"flexShrink": 0,
			"justifyContent": "center",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={
					"alignItems": "center",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"maxWidth": "1200px",
					"padding": "15px 40px",
					"width": "100%",
				},
				mobile={"padding": "12px 18px"},
				children=[
					brand(refs),
					block(
						"div",
						styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "26px"},
						mobile={"gap": "14px"},
						children=[
							block("a", text="Shop all", attrs={"href": "/products"}, styles={**link_style, "whiteSpace": "nowrap"}),
							block("a", text="About", attrs={"href": "/about"}, styles=dict(link_style), mobile={"display": "none"}),
							block("a", text="Contact", attrs={"href": "/contact"}, styles=dict(link_style), mobile={"display": "none"}),
							block(
								"a",
								text="Account",
								attrs={"href": "/account/orders"},
								styles={**link_style, "whiteSpace": "nowrap"},
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
		],
	)


def footer_column(refs, title, links):
	return block(
		"div",
		styles={"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
		children=[
			block(
				"p",
				text=title,
				styles={
					"color": refs["muted"],
					"fontSize": "11px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.1em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
			),
			*[
				block(
					"a",
					text=label,
					attrs={"href": href},
					styles={
						"color": refs["ink"],
						"fontSize": "13px",
						"height": "fit-content",
						"textDecoration": "none",
						"width": "fit-content",
					},
				)
				for label, href in links
			],
		],
	)


def footer(refs):
	brand_col = block(
		"div",
		styles={"display": "flex", "flexDirection": "column", "gap": "14px", "maxWidth": "300px", "width": "100%"},
		children=[
			brand(refs),
			block(
				"p",
				text="Engineered for comfort. Designed for builders. The official merchandise store for the community.",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "lineHeight": "1.6", "width": "100%"},
			),
		],
	)
	return block(
		"div",
		name="Footer",
		styles={
			"alignItems": "center",
			"borderTopColor": refs["line"],
			"borderTopStyle": "solid",
			"borderTopWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"flexShrink": 0,
			"marginTop": "auto",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={
					"display": "flex",
					"flexDirection": "row",
					"gap": "48px",
					"justifyContent": "space-between",
					"maxWidth": "1200px",
					"padding": "48px 40px 40px",
					"width": "100%",
				},
				mobile={"flexDirection": "column", "gap": "28px", "padding": "32px 18px"},
				children=[
					brand_col,
					block(
						"div",
						styles={
							"display": "grid",
							"gap": "48px",
							"gridTemplateColumns": "repeat(3, minmax(120px, 1fr))",
							"width": "fit-content",
						},
						mobile={
							"gap": "24px",
							"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
							"width": "100%",
						},
						children=[
							footer_column(
								refs,
								"Shop",
								[("All products", "/products"), ("Collections", "/products")],
							),
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
					"gap": "5px",
					"justifyContent": "flex-start",
					"maxWidth": "1200px",
					"padding": "18px 40px",
					"width": "100%",
				},
				children=[
					block(
						"span",
						text="© 2026",
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "width": "fit-content"},
					),
					block(
						"span",
						text="Shop",
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("store.name", "innerHTML")],
					),
					block(
						"span",
						text="· All rights reserved.",
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "width": "fit-content"},
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
			"backgroundColor": "#FEF2F2",
			"borderRadius": "4px",
			"color": "#B3261E",
			"display": "none",
			"fontSize": "14px",
			"marginTop": "16px",
			"padding": "12px 16px",
			"width": "100%",
		},
	)


def heading(refs, text, size="32px", mobile_size="24px", element="h1", serif=False):
	styles = {
		"color": refs["ink"],
		"fontSize": size,
		"fontWeight": "600",
		"height": "fit-content",
		"letterSpacing": "-0.01em",
		"lineHeight": "1.15",
		"width": "fit-content",
	}
	if serif:
		styles["fontFamily"] = HEAD
	return block(element, text=text, styles=styles, mobile={"fontSize": mobile_size})


def section_header(refs, title, link_label=None, link_href=None):
	children = [heading(refs, title, size="20px", mobile_size="18px", element="h2")]
	if link_label:
		children.append(
			block(
				"a",
				text=link_label,
				attrs={"href": link_href},
				styles={
					"color": refs["muted"],
					"fontSize": "13px",
					"fontWeight": "500",
					"height": "fit-content",
					"textDecoration": "none",
					"width": "fit-content",
				},
			)
		)
	return block(
		"div",
		styles={
			"alignItems": "baseline",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"width": "100%",
		},
		children=children,
	)


def black_button_styles(refs, full=False):
	return {
		"backgroundColor": refs["ink"],
		"borderRadius": "2px",
		"color": refs["paper"],
		"fontSize": "13px",
		"fontWeight": "600",
		"height": "fit-content",
		"letterSpacing": "0.02em",
		"padding": "13px 26px",
		"textAlign": "center",
		"textDecoration": "none",
		"width": "100%" if full else "fit-content",
	}


def stars_span(refs, key, size="13px"):
	return block(
		"span",
		text="★★★★★",
		styles={
			"color": refs["badge"],
			"fontSize": size,
			"height": "fit-content",
			"letterSpacing": "1px",
			"lineHeight": "1",
			"width": "fit-content",
		},
		dynamicValues=[dv(key, "innerHTML")],
	)


def inline_text(refs, parts, size="13px", color=None, weight="400"):
	"""Row of spans with no gap so bound values sit inside literal text."""
	spans = []
	for part in parts:
		bound, value = part
		spans.append(
			block(
				"span",
				text="" if bound else value,
				styles={
					"color": color or refs["muted"],
					"fontSize": size,
					"fontWeight": weight,
					"height": "fit-content",
					"whiteSpace": "pre",
					"width": "fit-content",
				},
				dynamicValues=[dv(value, "innerHTML")] if bound else [],
			)
		)
	return block(
		"div",
		styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "width": "fit-content"},
		children=spans,
	)


def card_rating_row(refs):
	return block(
		"div",
		name="Card Rating",
		visibilityCondition={"key": "rating_count", "comesFrom": "dataScript"},
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"gap": "6px",
			"marginTop": "-4px",
			"width": "fit-content",
		},
		children=[
			stars_span(refs, "rating_stars", size="12px"),
			inline_text(refs, [(False, "("), (True, "rating_count"), (False, ")")], size="12px"),
		],
	)


def card_price_row(refs):
	discount_tag = block(
		"div",
		visibilityCondition={"key": "discount_pct", "comesFrom": "dataScript"},
		styles={"display": "flex", "flexDirection": "row", "width": "fit-content"},
		children=[
			inline_text(refs, [(False, "-"), (True, "discount_pct"), (False, "%")], size="12px", color=refs["success"], weight="700"),
		],
	)
	return block(
		"div",
		name="Card Price",
		styles={
			"alignItems": "baseline",
			"display": "flex",
			"flexDirection": "row",
			"flexWrap": "wrap",
			"gap": "4px 8px",
			"marginTop": "-2px",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="",
				visibilityCondition={"key": "formatted_price", "comesFrom": "dataScript"},
				styles={"fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_price", "innerHTML")],
			),
			block(
				"span",
				text="",
				visibilityCondition={"key": "formatted_compare_at", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "12px",
					"height": "fit-content",
					"textDecoration": "line-through",
					"width": "fit-content",
				},
				dynamicValues=[dv("formatted_compare_at", "innerHTML")],
			),
			discount_tag,
		],
	)


def product_card(refs):
	return block(
		"a",
		name="Product Card",
		attrs={"href": "#"},
		styles={
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "10px",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "4 / 5",
					"backgroundColor": refs["card"],
					"borderRadius": "4px",
					"display": "block",
					"objectFit": "cover",
					"width": "100%",
				},
				dynamicValues=[dv("image", "src", "attribute"), dv("product_name", "alt", "attribute")],
			),
			block(
				"h3",
				text="Product",
				styles={
					"fontSize": "14px",
					"fontWeight": "500",
					"height": "fit-content",
					"lineHeight": "1.4",
					"width": "100%",
				},
				dynamicValues=[dv("product_name", "innerHTML")],
			),
			card_rating_row(refs),
			card_price_row(refs),
		],
	)


def product_grid(refs, key, source, columns=4):
	return repeater(
		key,
		component_ref("shop-product-card"),
		{
			"display": "grid",
			"gap": "36px 24px",
			"gridTemplateColumns": f"repeat({columns}, minmax(0, 1fr))",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "24px 14px"},
		tablet={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
		name=f"Grid · {source}",
	)


def hero(refs):
	return section(
		[
			block(
				"h1",
				text="Engineered for comfort.<br>Designed for builders.",
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "52px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "-0.01em",
					"lineHeight": "1.12",
					"maxWidth": "640px",
					"width": "100%",
				},
				mobile={"fontSize": "32px"},
			),
			block(
				"p",
				text="The official merchandise collection. Premium apparel and minimal accessories tailored for the open source community.",
				styles={
					"color": refs["muted"],
					"fontSize": "15px",
					"height": "fit-content",
					"lineHeight": "1.65",
					"maxWidth": "430px",
					"width": "100%",
				},
			),
			block(
				"div",
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "22px", "marginTop": "10px"},
				children=[
					block("a", text="Shop latest drop", attrs={"href": "/products"}, styles=black_button_styles(refs)),
					block(
						"a",
						text="View collections →",
						attrs={"href": "/products"},
						styles={
							"color": refs["ink"],
							"fontSize": "13px",
							"fontWeight": "500",
							"height": "fit-content",
							"textDecoration": "none",
							"width": "fit-content",
						},
					),
				],
			),
		],
		styles={"gap": "18px", "padding": "92px 40px 76px"},
		mobile={"padding": "48px 18px 40px"},
	)


def collection_tile(refs):
	photo = block(
		"div",
		name="Tile Photo",
		styles={
			"backgroundPosition": "center",
			"backgroundSize": "cover",
			"inset": "0",
			"position": "absolute",
		},
		dynamicValues=[dv("image_css", "background-image", "style")],
	)
	fade = block(
		"div",
		name="Tile Fade",
		styles={
			"backgroundImage": f"linear-gradient(transparent 10%, {refs['paper']} 88%)",
			"inset": "0",
			"position": "absolute",
		},
	)
	return block(
		"a",
		name="Collection Tile",
		attrs={"href": "#"},
		styles={
			"backgroundColor": refs["card"],
			"borderRadius": "4px",
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "6px",
			"justifyContent": "flex-end",
			"minHeight": "190px",
			"overflow": "hidden",
			"padding": "22px 22px",
			"position": "relative",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			photo,
			fade,
			block(
				"h3",
				text="Collection",
				styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "position": "relative", "width": "fit-content"},
				dynamicValues=[dv("title", "innerHTML")],
			),
			block(
				"p",
				text="",
				visibilityCondition={"key": "description", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "lineHeight": "1.5", "position": "relative", "width": "100%"},
				dynamicValues=[dv("description", "innerHTML")],
			),
		],
	)


def home_blocks(refs):
	collections = named_section("Section · Curated Collections", 
		[
			section_header(refs, "Curated Collections", "View collections →", "/products"),
			repeater(
				"collections",
				component_ref("shop-collection-tile"),
				{
					"display": "grid",
					"gap": "16px",
					"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "repeat(1, minmax(0, 1fr))"},
				tablet={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
				name="Grid · collections",
			),
		],
		styles={"gap": "22px", "padding": "40px 40px"},
	)
	best_sellers = named_section("Section · Best Sellers", 
		[
			section_header(refs, "Best Sellers", "View all →", "/products"),
			product_grid(refs, "featured_products", "featured"),
		],
		styles={"gap": "22px", "padding": "40px 40px"},
	)
	featured_band = named_section("Section · Featured Band", 
		[
			block(
				"div",
				styles={
					"alignItems": "center",
					"backgroundColor": refs["card"],
					"borderRadius": "4px",
					"display": "flex",
					"flexDirection": "column",
					"gap": "16px",
					"padding": "72px 40px",
					"textAlign": "center",
					"width": "100%",
				},
				mobile={"padding": "44px 20px"},
				children=[
					block(
						"p",
						text="Featured",
						styles={
							"color": refs["badge"],
							"fontSize": "11px",
							"fontWeight": "700",
							"height": "fit-content",
							"letterSpacing": "0.14em",
							"textTransform": "uppercase",
							"width": "fit-content",
						},
					),
					block(
						"h2",
						text="Made for deep work and comfort.",
						styles={
							"color": refs["ink"],
							"fontFamily": HEAD,
							"fontSize": "34px",
							"fontWeight": "600",
							"height": "fit-content",
							"letterSpacing": "-0.01em",
							"lineHeight": "1.2",
							"maxWidth": "560px",
							"width": "100%",
						},
						mobile={"fontSize": "24px"},
					),
					block(
						"p",
						text="Heavyweight fabrics, minimal marks and a fit that holds its shape. Small drops, made to be kept.",
						styles={
							"color": refs["muted"],
							"fontSize": "14px",
							"height": "fit-content",
							"lineHeight": "1.6",
							"maxWidth": "440px",
							"width": "100%",
						},
					),
					block(
						"a",
						text="Shop best sellers",
						attrs={"href": "/products"},
						styles={**black_button_styles(refs), "marginTop": "6px"},
					),
				],
			)
		],
		styles={"padding": "40px 40px 88px"},
	)
	return shell(
		refs,
		[
			component_ref("shop-navbar"),
			component_ref("shop-hero"),
			collections,
			best_sellers,
			featured_band,
			component_ref("shop-footer"),
		],
	)


def search_form(refs):
	return block(
		"form",
		name="Search",
		attrs={"data-shop": "search-form", "action": "/products"},
		styles={"display": "flex", "flexDirection": "row", "gap": "8px", "width": "fit-content"},
		mobile={"width": "100%"},
		children=[
			block(
				"input",
				attrs={"type": "search", "name": "search", "placeholder": "Search products"},
				dynamicValues=[dv("search", "value", "attribute")],
				styles={
					"backgroundColor": refs["paper"],
					"borderColor": refs["line"],
					"borderRadius": "2px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"fontSize": "13px",
					"padding": "10px 14px",
					"width": "240px",
				},
				mobile={"width": "100%"},
			),
			block(
				"button",
				text="Search",
				attrs={"type": "submit"},
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"borderWidth": "0px",
					"color": refs["paper"],
					"fontSize": "13px",
					"fontWeight": "600",
					"padding": "10px 18px",
					"width": "fit-content",
				},
			),
		],
	)


def filter_bar(refs):
	option_chip = block(
		"a",
		name="Filter Option",
		text="Option",
		attrs={"href": "#", "data-active": "false"},
		styles={
			"borderColor": refs["line"],
			"borderRadius": "2px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "12px",
			"fontWeight": "500",
			"height": "fit-content",
			"padding": "6px 13px",
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
		styles={
			"alignItems": "baseline",
			"display": "flex",
			"flexDirection": "row",
			"gap": "18px",
			"width": "100%",
		},
		mobile={"flexDirection": "column", "gap": "8px"},
		children=[
			block(
				"p",
				text="Filter",
				styles={
					"color": refs["muted"],
					"flexShrink": 0,
					"fontSize": "11px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.1em",
					"minWidth": "88px",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
				dynamicValues=[dv("label", "innerHTML")],
			),
			repeater(
				"options",
				option_chip,
				{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "8px", "width": "100%"},
				name="Filter Options",
			),
		],
	)
	return repeater(
		"filters",
		filter_group,
		{
			"borderTopColor": refs["line"],
			"borderTopStyle": "solid",
			"borderTopWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"paddingTop": "20px",
			"width": "100%",
		},
		name="Filters",
	)


def products_blocks(refs):
	header = named_section("Section · Listing Header", 
		[
			block(
				"div",
				styles={
					"alignItems": "flex-end",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"width": "100%",
				},
				mobile={"alignItems": "stretch", "flexDirection": "column", "gap": "16px"},
				children=[
					block(
						"div",
						styles={"display": "flex", "flexDirection": "column", "gap": "8px", "width": "fit-content"},
						children=[
							heading(refs, "All Products", size="30px", mobile_size="24px"),
							block(
								"p",
								text="Official merchandise for the builder community.",
								styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
							),
							block(
								"div",
								name="Active Search",
								visibilityCondition={"key": "search_label", "comesFrom": "dataScript"},
								styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "gap": "10px", "width": "fit-content"},
								children=[
									block(
										"p",
										text="Results",
										styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
										dynamicValues=[dv("search_label", "innerHTML")],
									),
									block(
										"a",
										text="Clear search",
										attrs={"href": "/products"},
										styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "textDecoration": "underline", "width": "fit-content"},
									),
								],
							),
						],
					),
					search_form(refs),
				],
			),
			component_ref("shop-filter-bar"),
		],
		styles={"gap": "24px", "padding": "52px 40px 8px"},
	)
	empty = block(
		"div",
		name="No Results",
		visibilityCondition={"key": "no_results", "comesFrom": "dataScript"},
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "column",
			"gap": "10px",
			"padding": "48px 0 16px",
			"textAlign": "center",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="No products match your search or filters.",
				styles={"fontSize": "15px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"a",
				text="Clear all filters",
				attrs={"href": "/products"},
				styles={"color": refs["ink"], "fontSize": "13px", "height": "fit-content", "textDecoration": "underline", "width": "fit-content"},
			),
		],
	)
	grid = named_section("Section · Product Grid", [product_grid(refs, "products", "products", columns=3), empty], styles={"padding": "36px 40px 88px"})
	return shell(refs, [component_ref("shop-navbar"), header, grid, component_ref("shop-footer")])


def breadcrumb(refs, trail_key):
	crumb = {
		"color": refs["muted"],
		"fontSize": "12px",
		"height": "fit-content",
		"textDecoration": "none",
		"width": "fit-content",
	}
	return block(
		"div",
		name="Breadcrumb",
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "8px", "width": "100%"},
		children=[
			block("a", text="Home", attrs={"href": "/"}, styles=dict(crumb)),
			block("span", text="/", styles=dict(crumb)),
			block("a", text="Products", attrs={"href": "/products"}, styles=dict(crumb)),
			block("span", text="/", styles=dict(crumb)),
			block(
				"span",
				text="Product",
				styles={**crumb, "color": refs["ink"], "fontWeight": "500"},
				dynamicValues=[dv(trail_key, "innerHTML")],
			),
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
			"borderColor": refs["line"],
			"borderRadius": "3px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"cursor": "pointer",
			"display": "block",
			"objectFit": "cover",
			"width": "72px",
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
				"img",
				name="Main Image",
				attrs={
					"src": "/assets/builder/images/fallback.png",
					"alt": "",
					"loading": "eager",
					"data-shop": "main-image",
				},
				styles={
					"aspectRatio": "1 / 1",
					"borderRadius": "4px",
					"display": "block",
					"objectFit": "cover",
					"width": "100%",
				},
				dynamicValues=[
					dv("product.image", "src", "attribute"),
					dv("product.product_name", "alt", "attribute"),
				],
			),
			repeater(
				"product.images",
				thumb,
				{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "10px", "width": "100%"},
				name="Thumbnails",
				classes=["pdp-thumbs"],
			),
		],
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
			"borderRadius": "2px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "13px",
			"fontWeight": "500",
			"minWidth": "44px",
			"padding": "9px 14px",
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
				styles={
					"color": refs["muted"],
					"fontSize": "11px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.1em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
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
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "6px", "width": "fit-content"},
		children=[
			block(
				"span",
				text="In stock",
				styles={"color": refs["success"], "fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"span",
				text="· Ready to dispatch",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
		],
	)
	return block(
		"div",
		name="Details",
		styles={"display": "flex", "flexDirection": "column", "gap": "16px", "width": "100%"},
		children=[
			block(
				"h1",
				text="Product",
				styles={
					"color": refs["ink"],
					"fontSize": "28px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "-0.01em",
					"lineHeight": "1.15",
					"width": "100%",
				},
				mobile={"fontSize": "24px"},
				dynamicValues=[dv("product.product_name", "innerHTML")],
			),
			pdp_rating_row(refs),
			pdp_price_block(refs),
			block(
				"a",
				name="Size Guide",
				text="Size guide",
				visibilityCondition={"key": "product.has_variants", "comesFrom": "dataScript"},
				attrs={"href": "/faq"},
				styles={
					"alignSelf": "flex-end",
					"color": refs["muted"],
					"fontSize": "12px",
					"height": "fit-content",
					"marginBottom": "-34px",
					"textDecoration": "underline",
					"width": "fit-content",
				},
			),
			repeater(
				"product.attribute_options",
				attribute_group,
				{"display": "flex", "flexDirection": "column", "gap": "16px", "marginTop": "4px", "width": "100%"},
				name="Variant Picker",
			),
			stock_line,
			pdp_highlights(refs),
			pdp_buttons(refs),
			error_banner(refs),
			component_ref("shop-delivery-card"),
			component_ref("shop-trust-row"),
			block(
				"p",
				text="",
				visibilityCondition={"key": "product.description_text", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "14px",
					"height": "fit-content",
					"lineHeight": "1.7",
					"width": "100%",
				},
				dynamicValues=[dv("product.description_text", "innerHTML")],
			),
		],
	)


def pdp_rating_row(refs):
	return block(
		"div",
		name="Rating",
		visibilityCondition={"key": "product.rating.count", "comesFrom": "dataScript"},
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"gap": "7px",
			"marginTop": "-6px",
			"width": "fit-content",
		},
		children=[
			stars_span(refs, "product.rating.stars", size="14px"),
			block(
				"span",
				text="",
				styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("product.rating.average", "innerHTML")],
			),
			inline_text(refs, [(False, "("), (True, "product.rating.count"), (False, " reviews)")], size="13px"),
			block(
				"a",
				text="See reviews",
				attrs={"href": "#reviews"},
				styles={
					"color": refs["muted"],
					"fontSize": "13px",
					"height": "fit-content",
					"textDecoration": "underline",
					"width": "fit-content",
				},
			),
		],
	)


def pdp_price_block(refs):
	price_row = block(
		"div",
		styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "gap": "10px", "width": "100%"},
		children=[
			block(
				"p",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles={"color": refs["ink"], "fontSize": "26px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("product.formatted_price", "innerHTML")],
			),
			block(
				"span",
				text="",
				visibilityCondition={"key": "product.formatted_compare_at", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "15px",
					"height": "fit-content",
					"textDecoration": "line-through",
					"width": "fit-content",
				},
				dynamicValues=[dv("product.formatted_compare_at", "innerHTML")],
			),
			block(
				"div",
				attrs={"data-shop": "pdp-discount"},
				visibilityCondition={"key": "product.discount_pct", "comesFrom": "dataScript"},
				styles={
					"borderColor": refs["success"],
					"borderRadius": "2px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"display": "flex",
					"flexDirection": "row",
					"padding": "2px 7px",
					"width": "fit-content",
				},
				children=[
					inline_text(refs, [(True, "product.discount_pct"), (False, "% OFF")], size="11px", color=refs["success"], weight="700"),
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
			inline_text(refs, [(False, "You save "), (True, "product.formatted_savings")], size="13px", color=refs["success"], weight="600"),
		],
	)
	return block(
		"div",
		name="Price",
		styles={"display": "flex", "flexDirection": "column", "gap": "6px", "width": "100%"},
		children=[price_row, savings],
	)


def pdp_highlights(refs):
	chip = block(
		"span",
		name="Highlight",
		text="Highlight",
		styles={
			"borderColor": refs["line"],
			"borderRadius": "2px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "12px",
			"fontWeight": "500",
			"height": "fit-content",
			"padding": "5px 11px",
			"width": "fit-content",
		},
		dynamicValues=[dv("label", "innerHTML")],
	)
	return repeater(
		"product.highlights",
		chip,
		{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "8px", "width": "100%"},
		name="Highlights",
	)


def buy_button_styles(refs, outline=False):
	styles = {
		"backgroundColor": refs["paper"] if outline else refs["ink"],
		"borderColor": refs["ink"],
		"borderRadius": "2px",
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["ink"] if outline else refs["paper"],
		"flexGrow": "1",
		"fontSize": "12px",
		"fontWeight": "700",
		"letterSpacing": "0.08em",
		"padding": "13px 24px",
		"textAlign": "center",
		"textTransform": "uppercase",
		"width": "100%",
	}
	return styles


def pdp_buttons(refs):
	return block(
		"div",
		name="Actions",
		styles={"display": "flex", "flexDirection": "row", "gap": "10px", "marginTop": "4px", "width": "100%"},
		mobile={"flexDirection": "column"},
		children=[
			block(
				"button",
				name="Add to cart",
				text="Add to cart",
				attrs={
					"type": "button",
					"data-shop": "add-to-cart",
					"data-label": "Add to cart",
					"data-added-label": "Added ✓",
					"data-out-of-stock-label": "Out of stock",
				},
				styles=buy_button_styles(refs, outline=True),
				dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
			),
			block(
				"button",
				name="Buy now",
				text="Buy now",
				attrs={
					"type": "button",
					"data-shop": "buy-now",
					"data-label": "Buy now",
					"data-out-of-stock-label": "Out of stock",
				},
				styles=buy_button_styles(refs),
				dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
			),
		],
	)


def delivery_card(refs):
	return block(
		"div",
		name="Delivery",
		styles={
			"borderColor": refs["line"],
			"borderRadius": "3px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "5px",
			"padding": "14px 16px",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="Free delivery",
				styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"p",
				text="Ships in 48 hours · 14-day easy returns",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"p",
				text="Cash on Delivery available",
				visibilityCondition={"key": "store.enable_cod", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
		],
	)


def trust_row(refs):
	item = lambda label: block(
		"div",
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "6px", "width": "fit-content"},
		children=[
			block(
				"span",
				text="✓",
				styles={"color": refs["muted"], "fontSize": "11px", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"span",
				text=label,
				styles={"color": refs["muted"], "fontSize": "12px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
			),
		],
	)
	return block(
		"div",
		name="Trust",
		styles={
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"borderTopColor": refs["line"],
			"borderTopStyle": "solid",
			"borderTopWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"flexWrap": "wrap",
			"gap": "8px 18px",
			"padding": "12px 0",
			"width": "100%",
		},
		children=[
			item("Secure payments"),
			item("Easy returns"),
			item("Quality checked"),
			item("Support that replies"),
		],
	)


def fabric_band(refs):
	tile = lambda title, caption: block(
		"div",
		styles={
			"backgroundColor": refs["card"],
			"borderRadius": "4px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "4px",
			"justifyContent": "flex-end",
			"minHeight": "150px",
			"padding": "18px 20px",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text=title,
				styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"p",
				text=caption,
				styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.5", "width": "100%"},
			),
		],
	)
	return named_section(
		"Section · The Frappe Fabric",
		[
			block(
				"h2",
				text="The Frappe fabric.",
				styles={
					"alignSelf": "center",
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "28px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "-0.01em",
					"width": "fit-content",
				},
				mobile={"fontSize": "22px"},
			),
			block(
				"div",
				styles={
					"display": "grid",
					"gap": "16px",
					"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					tile("Heavyweight cotton", "Dense, soft handfeel that keeps its structure wash after wash."),
					tile("Pre-shrunk fit", "Cut for the modern builder. What fits on day one fits on day hundred."),
					tile("Printed in small batches", "Minimal marks, made in short runs and never overproduced."),
				],
			),
		],
		styles={"gap": "28px", "padding": "24px 40px 48px"},
	)


def related_band(refs):
	return named_section(
		"Section · You May Also Like",
		[
			section_header(refs, "You may also like", "View all →", "/products"),
			product_grid(refs, "related_products", "related"),
		],
		styles={"gap": "22px", "padding": "24px 40px 88px"},
	)


def rating_summary(refs):
	histogram_row = block(
		"div",
		name="Histogram Row",
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "12px", "width": "100%"},
		children=[
			block(
				"div",
				styles={
					"alignItems": "baseline",
					"display": "flex",
					"flexDirection": "row",
					"flexShrink": 0,
					"gap": "3px",
					"width": "30px",
				},
				children=[
					block(
						"span",
						text="5",
						styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("stars", "innerHTML")],
					),
					block(
						"span",
						text="★",
						styles={"color": refs["badge"], "fontSize": "11px", "height": "fit-content", "width": "fit-content"},
					),
				],
			),
			block(
				"div",
				styles={
					"backgroundColor": refs["line"],
					"borderRadius": "2px",
					"flexGrow": "1",
					"height": "5px",
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
					"flexShrink": 0,
					"fontSize": "13px",
					"fontWeight": "600",
					"height": "fit-content",
					"minWidth": "18px",
					"textAlign": "right",
					"width": "fit-content",
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
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "56px",
					"fontWeight": "600",
					"height": "fit-content",
					"lineHeight": "1",
					"width": "fit-content",
				},
				mobile={"fontSize": "44px"},
				dynamicValues=[dv("reviews.average", "innerHTML")],
			),
			stars_span(refs, "product.rating.stars", size="16px"),
			inline_text(refs, [(False, "Based on "), (True, "reviews.count"), (False, " reviews")], size="13px"),
			repeater(
				"reviews.histogram",
				histogram_row,
				{"display": "flex", "flexDirection": "column", "gap": "9px", "marginTop": "10px", "width": "100%"},
				name="Histogram",
			),
		],
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
			"gap": "7px",
			"padding": "20px 0",
			"width": "100%",
		},
		children=[
			stars_span(refs, "stars", size="13px"),
			block(
				"h3",
				text="Review title",
				styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "100%"},
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
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "8px", "marginTop": "2px", "width": "100%"},
				children=[
					inline_text(refs, [(True, "reviewer_name"), (False, " · "), (True, "posted_on")], size="12px"),
					block(
						"span",
						text="✓ Verified buyer",
						visibilityCondition={"key": "verified", "comesFrom": "dataScript"},
						styles={
							"color": refs["success"],
							"fontSize": "11px",
							"fontWeight": "600",
							"height": "fit-content",
							"width": "fit-content",
						},
					),
				],
			),
		],
	)


def reviews_section(refs):
	return block(
		"div",
		name="Reviews",
		attrs={"id": "reviews"},
		visibilityCondition={"key": "reviews.count", "comesFrom": "dataScript"},
		styles={
			"display": "flex",
			"flexDirection": "column",
			"flexShrink": 0,
			"gap": "24px",
			"maxWidth": "1200px",
			"padding": "8px 40px 56px",
			"width": "100%",
		},
		mobile={"padding": "0 18px 40px"},
		children=[
			heading(refs, "Ratings and reviews", size="24px", mobile_size="20px", element="h2", serif=True),
			block(
				"div",
				styles={
					"display": "grid",
					"gap": "88px",
					"gridTemplateColumns": "minmax(0, 320px) minmax(0, 1fr)",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)", "gap": "28px"},
				children=[
					rating_summary(refs),
					repeater(
						"reviews.reviews",
						component_ref("shop-review-card"),
						{"display": "flex", "flexDirection": "column", "marginTop": "-20px", "width": "100%"},
						name="Review List",
					),
				],
			),
		],
	)


def review_form_section(refs):
	star = lambda value: block(
		"button",
		text="\u2605",
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
			"fontSize": "26px",
			"lineHeight": "1",
			"padding": "0",
			"width": "fit-content",
		},
	)
	form = block(
		"form",
		name="Review Form",
		attrs={"data-shop": "review-form"},
		styles={
			"display": "none",
			"flexDirection": "column",
			"gap": "10px",
			"maxWidth": "560px",
			"width": "100%",
		},
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
				styles={
					"backgroundColor": refs["paper"],
					"borderColor": refs["line"],
					"borderRadius": "2px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"fontSize": "13px",
					"padding": "11px 13px",
					"width": "100%",
				},
			),
			block(
				"button",
				text="SUBMIT REVIEW",
				attrs={"type": "submit"},
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"borderWidth": "0px",
					"color": refs["paper"],
					"fontSize": "12px",
					"fontWeight": "700",
					"letterSpacing": "0.08em",
					"padding": "12px 24px",
					"width": "fit-content",
				},
			),
		],
	)
	signin = block(
		"a",
		name="Review Sign-in",
		text="Sign in to write a review",
		attrs={"data-shop": "review-signin", "href": "/login"},
		styles={
			"color": refs["ink"],
			"fontSize": "14px",
			"height": "fit-content",
			"textDecoration": "underline",
			"width": "fit-content",
		},
	)
	return named_section(
		"Section \u00b7 Write a Review",
		[
			heading(refs, "Share your experience", size="20px", mobile_size="18px", element="h3", serif=True),
			error_banner(refs),
			signin,
			form,
		],
		styles={"gap": "14px", "padding": "0 40px 64px"},
	)


def buy_bar(refs):
	price = block(
		"div",
		styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "gap": "8px", "width": "fit-content"},
		children=[
			block(
				"span",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles={"fontSize": "17px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("product.formatted_price", "innerHTML")],
			),
			block(
				"span",
				text="",
				visibilityCondition={"key": "product.formatted_compare_at", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "13px",
					"height": "fit-content",
					"textDecoration": "line-through",
					"width": "fit-content",
				},
				dynamicValues=[dv("product.formatted_compare_at", "innerHTML")],
			),
		],
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
		styles={**buy_button_styles(refs), "flexGrow": "0", "padding": "11px 32px", "width": "fit-content"},
		dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
	)
	return block(
		"div",
		name="Buy Bar",
		classes=["pdp-buybar"],
		children=[block("div", classes=["pdp-buybar-inner"], children=[price, buy])],
	)


def apparel_band(refs):
	band = fabric_band(refs)
	band["visibilityCondition"] = {"key": "product.show_fabric_band", "comesFrom": "dataScript"}
	return band


def product_blocks(refs):
	crumbs = named_section("Section · Breadcrumb", [breadcrumb(refs, "product.product_name")], styles={"padding": "24px 40px 0"})
	main = named_section("Section · Product Details", 
		[pdp_gallery(refs), pdp_details(refs)],
		styles={
			"display": "grid",
			"gap": "56px",
			"gridTemplateColumns": "minmax(0, 1fr) minmax(0, 1fr)",
			"padding": "28px 40px 48px",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)", "gap": "28px", "padding": "20px 18px 40px"},
	)
	blocks = shell(
		refs,
		[
			component_ref("shop-navbar"),
			crumbs,
			main,
			reviews_section(refs),
			review_form_section(refs),
			apparel_band(refs),
			related_band(refs),
			component_ref("shop-footer"),
			buy_bar(refs),
		],
	)
	blocks[0]["baseStyles"]["paddingBottom"] = "64px"
	return blocks


def collection_blocks(refs):
	title = heading(refs, "Collection", size="30px", mobile_size="24px")
	title["dynamicValues"] = [dv("collection.title", "innerHTML")]
	header = named_section("Section · Collection Header", 
		[
			title,
			block(
				"p",
				text="",
				visibilityCondition={"key": "collection.description", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "lineHeight": "1.6", "maxWidth": "560px", "width": "100%"},
				dynamicValues=[dv("collection.description", "innerHTML")],
			),
		],
		styles={"gap": "8px", "padding": "52px 40px 8px"},
	)
	grid = named_section("Section · Collection Grid", [product_grid(refs, "products", "collection", columns=3)], styles={"padding": "28px 40px 88px"})
	return shell(refs, [component_ref("shop-navbar"), header, grid, component_ref("shop-footer")])


def summary_card(refs, children):
	return block(
		"div",
		name="Summary Card",
		styles={
			"backgroundColor": refs["paper"],
			"borderColor": refs["line"],
			"borderRadius": "4px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "14px",
			"height": "fit-content",
			"padding": "22px",
			"width": "100%",
		},
		children=children,
	)


def money_row(refs, label, bound_key=None, static_value=None, strong=False):
	return block(
		"div",
		styles={
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text=label,
				styles={
					"color": refs["ink"] if strong else refs["muted"],
					"fontSize": "14px" if strong else "13px",
					"fontWeight": "600" if strong else "400",
					"height": "fit-content",
					"width": "fit-content",
				},
			),
			block(
				"p",
				text=static_value or "",
				styles={
					"color": refs["success"] if static_value == "Free" else refs["ink"],
					"fontSize": "15px" if strong else "13px",
					"fontWeight": "700" if strong else "500",
					"height": "fit-content",
					"width": "fit-content",
				},
				dynamicValues=[dv(bound_key, "innerHTML")] if bound_key else [],
			),
		],
	)


def discount_amount(refs, bound_key):
	amount = {
		"color": refs["success"],
		"fontSize": "13px",
		"fontWeight": "500",
		"height": "fit-content",
		"width": "fit-content",
	}
	return block(
		"div",
		styles={"display": "flex", "flexDirection": "row", "gap": "2px"},
		children=[
			block("p", text="−", styles=dict(amount)),
			block("p", text="", styles=dict(amount), dynamicValues=[dv(bound_key, "innerHTML")]),
		],
	)


def discount_row(refs, bound_key, condition_key):
	return block(
		"div",
		name="Discount Row",
		visibilityCondition={"key": condition_key, "comesFrom": "dataScript"},
		styles={
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="Discount",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
			discount_amount(refs, bound_key),
		],
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
				styles={
					"backgroundColor": refs["paper"],
					"borderColor": refs["line"],
					"borderRadius": "2px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"flexGrow": "1",
					"fontSize": "13px",
					"minWidth": "0px",
					"padding": "10px 12px",
					"width": "100%",
				},
			),
			block(
				"button",
				text="Apply",
				attrs={"type": "submit"},
				styles={
					"backgroundColor": refs["paper"],
					"borderColor": refs["ink"],
					"borderRadius": "2px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"flexShrink": "0",
					"fontSize": "11px",
					"fontWeight": "700",
					"letterSpacing": "0.08em",
					"padding": "0 16px",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
			),
		],
	)
	applied = block(
		"div",
		name="Coupon Applied",
		visibilityCondition={"key": "cart.coupon.code", "comesFrom": "dataScript"},
		styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "8px", "width": "100%"},
		children=[
			block(
				"p",
				text="Coupon",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"p",
				text="",
				styles={
					"backgroundColor": refs["card"],
					"borderRadius": "2px",
					"fontSize": "12px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.04em",
					"padding": "2px 7px",
					"width": "fit-content",
				},
				dynamicValues=[dv("cart.coupon.code", "innerHTML")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "flexGrow": "1", "justifyContent": "flex-end"},
				children=[discount_amount(refs, "cart.coupon.formatted_discount")],
			),
			block(
				"button",
				text="Remove",
				attrs={"type": "button", "data-shop": "coupon-remove"},
				styles={
					"backgroundColor": "transparent",
					"borderWidth": "0px",
					"color": refs["muted"],
					"fontSize": "12px",
					"textDecoration": "underline",
					"width": "fit-content",
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
			"gap": "10px",
			"paddingTop": "14px",
			"width": "100%",
		},
		children=[form, applied],
	)


def cart_blocks(refs):
	qty_button = {
		"alignItems": "center",
		"backgroundColor": refs["paper"],
		"borderColor": refs["line"],
		"borderRadius": "2px",
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["ink"],
		"display": "flex",
		"fontSize": "14px",
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
			"padding": "16px 0",
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
					"borderRadius": "2px",
					"display": "block",
					"objectFit": "cover",
					"width": "60px",
				},
				dynamicValues=[dv("image", "src", "attribute"), dv("product_name", "alt", "attribute")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "flexGrow": "1", "gap": "3px"},
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
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "width": "fit-content"},
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
						styles={"fontSize": "13px", "minWidth": "18px", "textAlign": "center", "width": "fit-content"},
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
				styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "minWidth": "80px", "textAlign": "right", "width": "fit-content"},
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
			block(
				"button",
				text="Remove",
				attrs={"type": "button", "data-shop": "remove"},
				styles={
					"backgroundColor": "transparent",
					"borderWidth": "0px",
					"color": refs["muted"],
					"fontSize": "12px",
					"textDecoration": "underline",
					"width": "fit-content",
				},
				dynamicValues=[dv("item_code", "data-item-code", "attribute")],
			),
		],
	)
	card = summary_card(
		refs,
		[
			block(
				"p",
				text="Your cart is empty.",
				visibilityCondition={"key": "cart.is_empty", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
			),
			repeater(
				"cart.items",
				line_item,
				{"display": "flex", "flexDirection": "column", "marginTop": "-14px", "width": "100%"},
				name="Line Items",
			),
			block(
				"div",
				name="Totals",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				styles={
					"display": "flex",
					"flexDirection": "column",
					"gap": "8px",
					"paddingTop": "4px",
					"width": "100%",
				},
				children=[
					money_row(refs, "Subtotal", bound_key="cart.formatted_subtotal"),
					discount_row(refs, "cart.formatted_discount", "cart.coupon.code"),
					block(
						"div",
						name="Total Row",
						styles={
							"alignItems": "center",
							"display": "flex",
							"flexDirection": "row",
							"justifyContent": "space-between",
							"marginTop": "2px",
							"width": "100%",
						},
						children=[
							block("p", text="Total", styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
							block(
								"p",
								text="",
								styles={"fontSize": "18px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
								dynamicValues=[dv("cart.formatted_total", "innerHTML")],
							),
						],
					),
				],
			),
			block(
				"a",
				text="Checkout",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				attrs={"href": "/checkout"},
				styles=black_button_styles(refs, full=True),
			),
		],
	)
	content = named_section("Section · Cart", 
		[heading(refs, "Your cart", size="26px", mobile_size="22px"), error_banner(refs), card],
		styles={"gap": "18px", "maxWidth": "720px", "padding": "56px 40px 88px"},
	)
	return shell(refs, [component_ref("shop-navbar"), content, component_ref("shop-footer")])


def input_block(refs, name, label, input_type="text", required=False, half=False, prefill=False):
	attrs = {"type": input_type, "name": name, "placeholder": label}
	if required:
		attrs["required"] = "required"
	return block(
		"input",
		name=f"Input · {name}",
		attrs=attrs,
		dynamicValues=[dv(f"prefill.{name}", "value", "attribute")] if prefill else [],
		styles={
			"backgroundColor": refs["paper"],
			"borderColor": refs["line"],
			"borderRadius": "2px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "13px",
			"gridColumn": "span 1" if half else "span 2",
			"padding": "11px 13px",
			"width": "100%",
		},
	)


def form_section_label(refs, text):
	return block(
		"p",
		text=text,
		styles={
			"fontSize": "14px",
			"fontWeight": "600",
			"gridColumn": "span 2",
			"height": "fit-content",
			"marginTop": "10px",
			"width": "fit-content",
		},
	)


def checkout_blocks(refs):
	payment_option = block(
		"label",
		name="Payment Method",
		styles={
			"alignItems": "center",
			"borderColor": refs["line"],
			"borderRadius": "2px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "10px",
			"padding": "12px 14px",
			"width": "100%",
		},
		children=[
			block(
				"input",
				attrs={"type": "radio", "name": "payment_method"},
				styles={"accentColor": refs["ink"], "height": "15px", "width": "15px"},
				dynamicValues=[dv("method", "value", "attribute")],
			),
			block(
				"span",
				text="Payment",
				styles={"fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
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
			block(
				"p",
				text="Contact",
				styles={"fontSize": "14px", "fontWeight": "600", "gridColumn": "span 2", "height": "fit-content", "width": "fit-content"},
			),
			input_block(refs, "email", "Email address", "email", required=True, prefill=True),
			form_section_label(refs, "Shipping address"),
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
						{
							"backgroundColor": refs["paper"],
							"borderColor": refs["line"],
							"borderRadius": "2px",
							"borderStyle": "solid",
							"borderWidth": "1px",
							"color": refs["ink"],
							"fontSize": "13px",
							"padding": "11px 13px",
							"width": "100%",
						},
						element="select",
						attrs={"data-shop": "address-picker", "aria-label": "Saved addresses"},
					),
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
			form_section_label(refs, "Payment"),
			repeater(
				"payment_methods",
				payment_option,
				{"display": "flex", "flexDirection": "column", "gap": "8px", "gridColumn": "span 2", "width": "100%"},
				name="Payment Methods",
			),
			block(
				"p",
				text="You'll be redirected to a secure payment gateway to complete your purchase.",
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
			block(
				"button",
				text="Place order",
				attrs={"type": "submit"},
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"borderWidth": "0px",
					"color": refs["paper"],
					"fontSize": "13px",
					"fontWeight": "600",
					"gridColumn": "span 2",
					"marginTop": "8px",
					"padding": "14px 32px",
					"width": "100%",
				},
			),
		],
	)
	summary_row = block(
		"div",
		name="Summary Row",
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"gap": "12px",
			"width": "100%",
		},
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["card"],
					"borderRadius": "2px",
					"display": "block",
					"objectFit": "cover",
					"width": "44px",
				},
				dynamicValues=[dv("image", "src", "attribute"), dv("product_name", "alt", "attribute")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "flexGrow": "1", "gap": "2px"},
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
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("qty", "innerHTML")],
					),
				],
			),
			block(
				"p",
				text="",
				styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
		],
	)
	summary = summary_card(
		refs,
		[
			block("h2", text="Order summary", styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
			repeater(
				"cart.items",
				summary_row,
				{"display": "flex", "flexDirection": "column", "gap": "12px", "width": "100%"},
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
					"gap": "8px",
					"paddingTop": "14px",
					"width": "100%",
				},
				children=[
					money_row(refs, "Subtotal", bound_key="cart.formatted_subtotal"),
					discount_row(refs, "cart.formatted_discount", "cart.coupon.code"),
					money_row(refs, "Shipping", bound_key="cart.formatted_shipping", static_value="Free"),
				],
			),
			block(
				"div",
				styles={
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"paddingTop": "12px",
					"width": "100%",
				},
				children=[money_row(refs, "Total", bound_key="cart.formatted_total", strong=True)],
			),
			block(
				"p",
				text="Secure checkout · SSL encrypted · 14-day easy returns",
				styles={
					"color": refs["muted"],
					"fontSize": "11px",
					"height": "fit-content",
					"textAlign": "center",
					"width": "100%",
				},
			),
		],
	)
	content = named_section("Section · Checkout", 
		[
			heading(refs, "Checkout", size="26px", mobile_size="22px"),
			error_banner(refs),
			block(
				"div",
				name="Empty Checkout",
				visibilityCondition={"key": "cart.is_empty", "comesFrom": "dataScript"},
				styles={
					"alignItems": "center",
					"display": "flex",
					"flexDirection": "column",
					"gap": "10px",
					"padding": "56px 0",
					"textAlign": "center",
					"width": "100%",
				},
				children=[
					block(
						"p",
						text="Your cart is empty.",
						styles={"fontSize": "15px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
					),
					block(
						"a",
						text="Continue shopping",
						attrs={"href": "/products"},
						styles={"color": refs["ink"], "fontSize": "13px", "height": "fit-content", "textDecoration": "underline", "width": "fit-content"},
					),
				],
			),
			block(
				"div",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				styles={
					"display": "grid",
					"gap": "48px",
					"gridTemplateColumns": "minmax(0, 3fr) minmax(0, 2fr)",
					"marginTop": "20px",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)", "gap": "24px"},
				children=[form, summary],
			),
		],
		styles={"maxWidth": "1040px", "padding": "52px 40px 88px"},
	)
	return shell(refs, [component_ref("shop-navbar"), content, component_ref("shop-footer")])


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
			"padding": "11px 0",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={"alignItems": "baseline", "display": "flex", "flexDirection": "row", "gap": "8px"},
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
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("qty", "innerHTML")],
					),
				],
			),
			block(
				"p",
				text="",
				styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
		],
	)
	tile_styles = {
		"backgroundColor": refs["card"],
		"borderRadius": "4px",
		"display": "flex",
		"flexDirection": "column",
		"gap": "5px",
		"padding": "16px 18px",
		"textAlign": "left",
		"width": "100%",
	}
	tile_title = lambda title: block(
		"p", text=title, styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}
	)
	tile_body_styles = {"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.5", "width": "100%"}
	info_tile = lambda title, body, **extra: block(
		"div",
		styles=dict(tile_styles),
		children=[tile_title(title), block("p", text=body, styles=dict(tile_body_styles))],
		**extra,
	)
	delivery_tile = block(
		"div",
		name="Delivery Tile",
		styles=dict(tile_styles),
		visibilityCondition={"key": "order.shipment", "comesFrom": "dataScript"},
		children=[
			tile_title("Delivery"),
			block(
				"p",
				text="Your order is with the courier.",
				styles=dict(tile_body_styles),
				dynamicValues=[dv("order.shipment.line", "innerHTML")],
				visibilityCondition={"key": "order.shipment.line", "comesFrom": "dataScript"},
			),
			block(
				"a",
				text="Track shipment",
				attrs={"target": "_blank", "rel": "noopener"},
				styles={
					"color": refs["ink"],
					"fontSize": "12px",
					"fontWeight": "500",
					"height": "fit-content",
					"textDecoration": "underline",
					"width": "fit-content",
				},
				dynamicValues=[dv("order.shipment.tracking_url", "href", "attribute")],
				visibilityCondition={"key": "order.shipment.tracking_url", "comesFrom": "dataScript"},
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
		{"display": "flex", "flexDirection": "row", "marginTop": "4px", "width": "100%"},
		name="Order Progress",
		attrs={"data-shop": "order-progress"},
	)
	order_card = summary_card(
		refs,
		[
			block(
				"div",
				styles={
					"alignItems": "baseline",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"width": "100%",
				},
				children=[
					block("h2", text="Order summary", styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
					block(
						"p",
						text="Order",
						styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("order.name", "innerHTML")],
					),
				],
			),
			repeater(
				"order.items",
				item_row,
				{"display": "flex", "flexDirection": "column", "marginTop": "-8px", "width": "100%"},
				name="Order Items",
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "gap": "7px", "paddingTop": "2px", "width": "100%"},
				children=[
					block(
						"div",
						styles={"display": "flex", "flexDirection": "row", "justifyContent": "space-between", "width": "100%"},
						children=[
							block("p", text="Subtotal", styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"}),
							block(
								"p",
								text="",
								styles={"fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
								dynamicValues=[dv("order.formatted_total", "innerHTML")],
							),
						],
					),
					discount_row(refs, "order.formatted_discount", "order.formatted_discount"),
					block(
						"div",
						styles={"display": "flex", "flexDirection": "row", "justifyContent": "space-between", "width": "100%"},
						children=[
							block("p", text="Shipping", styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"}),
							block("p", text="Free", styles={"color": refs["success"], "fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"}, dynamicValues=[dv("order.formatted_shipping", "innerHTML")]),
						],
					),
					block(
						"div",
						styles={
							"borderTopColor": refs["line"],
							"borderTopStyle": "solid",
							"borderTopWidth": "1px",
							"display": "flex",
							"flexDirection": "row",
							"justifyContent": "space-between",
							"marginTop": "3px",
							"paddingTop": "10px",
							"width": "100%",
						},
						children=[
							block("p", text="Total", styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
							block(
								"p",
								text="",
								styles={"fontSize": "16px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
								dynamicValues=[dv("order.formatted_grand_total", "innerHTML")],
							),
						],
					),
				],
			),
		],
	)
	content = named_section("Section · Order Confirmation", 
		[
			block(
				"p",
				text="✓",
				styles={
					"alignItems": "center",
					"backgroundColor": refs["ink"],
					"borderRadius": "50%",
					"color": refs["paper"],
					"display": "flex",
					"fontSize": "22px",
					"height": "52px",
					"justifyContent": "center",
					"width": "52px",
				},
			),
			block(
				"h1",
				text="Thank you for your order!",
				styles={
					"color": refs["ink"],
					"fontSize": "28px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "-0.01em",
					"textAlign": "center",
					"width": "fit-content",
				},
				mobile={"fontSize": "22px"},
			),
			block(
				"p",
				text="Your order is confirmed. A confirmation with tracking details is on its way to your email.",
				styles={
					"color": refs["muted"],
					"fontSize": "14px",
					"height": "fit-content",
					"lineHeight": "1.6",
					"maxWidth": "400px",
					"textAlign": "center",
					"width": "100%",
				},
			),
			block("div", styles={"height": "8px", "width": "100%"}),
			progress,
			block("div", styles={"height": "2px", "width": "100%"}),
			order_card,
			block(
				"div",
				styles={
					"display": "grid",
					"gap": "12px",
					"gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					info_tile(
						"Shipping info",
						"Your order ships in 48 hours. We will email you the tracking number.",
						name="Shipping Tile",
						visibilityCondition={"key": "order.awaiting_shipment", "comesFrom": "dataScript"},
					),
					delivery_tile,
					info_tile("Order confirmation", "A receipt for this order has been sent to your email address."),
				],
			),
			returns_section(refs),
			block(
				"a",
				text="Track my order",
				attrs={"href": "/account/orders"},
				styles={**black_button_styles(refs, full=True), "marginTop": "6px"},
			),
			block(
				"a",
				text="Continue shopping",
				attrs={"href": "/products"},
				styles={
					"color": refs["ink"],
					"fontSize": "13px",
					"fontWeight": "500",
					"height": "fit-content",
					"textDecoration": "underline",
					"width": "fit-content",
				},
			),
			block(
				"a",
				text="Need help with your order? Contact support.",
				attrs={"href": "/contact"},
				styles={
					"color": refs["muted"],
					"fontSize": "12px",
					"height": "fit-content",
					"marginTop": "10px",
					"textDecoration": "none",
					"width": "fit-content",
				},
			),
		],
		styles={"alignItems": "center", "gap": "14px", "maxWidth": "560px", "padding": "64px 40px 96px"},
	)
	return shell(refs, [component_ref("shop-navbar"), content, component_ref("shop-footer")])


def returns_section(refs):
	field_styles = {
		"backgroundColor": refs["paper"],
		"borderColor": refs["line"],
		"borderRadius": "2px",
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["ink"],
		"fontSize": "13px",
		"padding": "10px 12px",
		"width": "100%",
	}
	request_row = block(
		"div",
		name="Return Request",
		styles={
			"alignItems": "baseline",
			"display": "flex",
			"flexDirection": "row",
			"gap": "12px",
			"justifyContent": "space-between",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "gap": "2px"},
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
				styles={"color": refs["muted"], "fontSize": "12px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
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
				text="Need to return or replace something? You have 14 days from shipping.",
				styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.5", "width": "100%"},
			),
			block(
				"div",
				styles={"display": "grid", "gap": "10px", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "width": "100%"},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					repeater("order.items", item_option, dict(field_styles), element="select", name="Item Select", attrs={"name": "item_code"}),
					block(
						"select",
						attrs={"name": "request_type"},
						styles=dict(field_styles),
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
				styles=dict(field_styles),
			),
			block(
				"button",
				text="Submit request",
				attrs={"type": "submit"},
				styles={
					"backgroundColor": refs["paper"],
					"borderColor": refs["ink"],
					"borderRadius": "2px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"fontSize": "13px",
					"fontWeight": "600",
					"padding": "10px 24px",
					"width": "fit-content",
				},
			),
		],
	)
	requests = repeater(
		"order.returns.requests",
		request_row,
		{"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
		name="Return Requests",
		visibilityCondition={"key": "order.returns.has_requests", "comesFrom": "dataScript"},
	)
	card = summary_card(
		refs,
		[
			block("h2", text="Returns & replacements", styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
			requests,
			form,
		],
	)
	card["visibilityCondition"] = {"key": "order.returns.show", "comesFrom": "dataScript"}
	card["blockName"] = "Returns Card"
	return card


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
			"padding": "15px 0",
			"textDecoration": "none",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "1fr 1fr"},
		children=[
			block(
				"p",
				text="Order",
				styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("name", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_date", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"color": refs["success"], "fontSize": "12px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("display_status", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "justifySelf": "end", "width": "fit-content"},
				dynamicValues=[dv("formatted_total", "innerHTML")],
			),
		],
	)
	content = named_section("Section · Your Orders", 
		[
			heading(refs, "Your orders", size="26px", mobile_size="22px"),
			repeater(
				"orders",
				order_row,
				{
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"marginTop": "18px",
					"width": "100%",
				},
				name="Orders",
			),
		],
		styles={"maxWidth": "860px", "padding": "56px 40px 88px"},
	)
	return shell(refs, [component_ref("shop-navbar"), content, component_ref("shop-footer")])


def kicker(refs, text):
	return block(
		"p",
		text=text,
		styles={
			"color": refs["badge"],
			"fontSize": "11px",
			"fontWeight": "700",
			"height": "fit-content",
			"letterSpacing": "0.14em",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
	)


def serif_page_heading(refs, text):
	return block(
		"h1",
		text=text,
		styles={
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": "40px",
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "-0.01em",
			"lineHeight": "1.15",
			"width": "fit-content",
		},
		mobile={"fontSize": "28px"},
	)


def paragraph(refs, text, size="15px"):
	return block(
		"p",
		text=text,
		styles={
			"color": refs["muted"],
			"fontSize": size,
			"height": "fit-content",
			"lineHeight": "1.7",
			"width": "100%",
		},
	)


def about_blocks(refs):
	stat = lambda value, label: block(
		"div",
		styles={"display": "flex", "flexDirection": "column", "gap": "4px", "width": "100%"},
		children=[
			block(
				"p",
				text=value,
				styles={
					"fontFamily": HEAD,
					"fontSize": "26px",
					"fontWeight": "600",
					"height": "fit-content",
					"width": "fit-content",
				},
			),
			block(
				"p",
				text=label,
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
		],
	)
	content = named_section("Section · About", 
		[
			kicker(refs, "About"),
			serif_page_heading(refs, "Made by builders, for builders."),
			paragraph(
				refs,
				"This store exists for one reason: merchandise worth keeping. Heavyweight "
				"fabrics, minimal marks and a fit that survives real work. Everything here "
				"is made in small runs and never overproduced.",
			),
			paragraph(
				refs,
				"We keep our margins honest and stand behind everything we sell. If "
				"something is not right, write to us and we will fix it.",
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
					"marginTop": "16px",
					"paddingTop": "24px",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					stat("2020", "Founded"),
					stat("120+", "Products shipped"),
					stat("48h", "Dispatch time"),
				],
			),
		],
		styles={"gap": "16px", "maxWidth": "760px", "padding": "72px 40px 96px"},
	)
	return shell(refs, [component_ref("shop-navbar"), content, component_ref("shop-footer")])


def contact_blocks(refs):
	detail = lambda label, value: block(
		"div",
		styles={
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "15px 0",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text=label,
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"p",
				text=value,
				styles={"fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
			),
		],
	)
	content = named_section("Section · Contact", 
		[
			kicker(refs, "Contact"),
			serif_page_heading(refs, "Get in touch."),
			paragraph(refs, "Questions about an order, a product or anything else. We reply within a day."),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "marginTop": "10px", "width": "100%"},
				children=[
					detail("Email", "hello@example.com"),
					detail("Phone", "+91 98765 43210"),
					detail("Hours", "Mon to Fri, 10:00 to 18:00"),
				],
			),
			block(
				"a",
				text="Write to us",
				attrs={"href": "mailto:hello@example.com"},
				styles={**black_button_styles(refs), "marginTop": "16px"},
			),
		],
		styles={"gap": "16px", "maxWidth": "760px", "padding": "72px 40px 96px"},
	)
	return shell(refs, [component_ref("shop-navbar"), content, component_ref("shop-footer")])


FAQS = [
	(
		"How long does delivery take?",
		"Orders are dispatched within 48 hours and usually arrive in 3 to 5 working days.",
	),
	(
		"Can I return a product?",
		"Yes, within 14 days of delivery, unused and in its original packaging. Write to us and we will arrange a pickup.",
	),
	(
		"How do sizes run?",
		"True to size with a modern fit. If you are between sizes, size up for a relaxed fit.",
	),
	(
		"How do I pay?",
		"You can pay online or choose cash on delivery at checkout.",
	),
	(
		"How do I track my order?",
		"Sign in with the email you used at checkout and open Orders in the top navigation.",
	),
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
			"gap": "7px",
			"padding": "18px 0",
			"width": "100%",
		},
		children=[
			block(
				"h3",
				text=question,
				styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
			),
			paragraph(refs, answer, size="14px"),
		],
	)
	content = named_section("Section · FAQ", 
		[
			kicker(refs, "FAQ"),
			serif_page_heading(refs, "Frequently asked questions."),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "marginTop": "10px", "width": "100%"},
				children=[entry(question, answer) for question, answer in FAQS],
			),
		],
		styles={"gap": "16px", "maxWidth": "760px", "padding": "72px 40px 96px"},
	)
	return shell(refs, [component_ref("shop-navbar"), content, component_ref("shop-footer")])
