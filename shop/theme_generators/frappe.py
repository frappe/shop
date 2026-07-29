"""Frappe: crisp merch storefront. White canvas, hairline rules, serif display moments, rectangular geometry."""

from shop.theme_generators.blocks import (
	block,
	dv,
	repeater,
	root,
	upsert_client_script,
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
	pages = [
		("frappe-home", "Home", "home", home_blocks(refs), "home", (), False),
		("frappe-products", "Products", "products", products_blocks(refs), "listing", (), False),
		("frappe-product", "Product", "product/:slug", product_blocks(refs), "product_page", ("product",), False),
		("frappe-collection", "Collection", "collection/:slug", collection_blocks(refs), "collection_page", (), False),
		("frappe-cart", "Cart", "cart", cart_blocks(refs), "cart_page", ("cart",), False),
		("frappe-checkout", "Checkout", "checkout", checkout_blocks(refs), "checkout_page", ("cart",), False),
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
input, textarea {{ font-family: inherit; }}
input::placeholder {{ color: {refs["muted"]}; }}
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
			children,
		)
	]


def section(children, styles=None, mobile=None):
	base = {
		"display": "flex",
		"flexDirection": "column",
		"flexShrink": 0,
		"maxWidth": "1200px",
		"padding": "48px 40px",
		"width": "100%",
	}
	base.update(styles or {})
	return block("div", styles=base, mobile=mobile or {"padding": "28px 18px"}, children=children)


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
		attrs={"href": "/cart"},
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
							block("a", text="Shop all", attrs={"href": "/products"}, styles=dict(link_style)),
							block("a", text="About", attrs={"href": "/about"}, styles=dict(link_style)),
							block("a", text="Contact", attrs={"href": "/contact"}, styles=dict(link_style)),
							block("a", text="Orders", attrs={"href": "/account/orders"}, styles=dict(link_style)),
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
						mobile={"gap": "24px", "width": "100%"},
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


def product_card(refs, source="products"):
	return block(
		"a",
		name=f"Card · {source}",
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
				"div",
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
						"h3",
						text="Product",
						styles={
							"fontSize": "14px",
							"fontWeight": "500",
							"height": "fit-content",
							"lineHeight": "1.4",
							"width": "fit-content",
						},
						dynamicValues=[dv("product_name", "innerHTML")],
					),
					block(
						"p",
						text="",
						visibilityCondition={"key": "formatted_price", "comesFrom": "dataScript"},
						styles={
							"flexShrink": 0,
							"fontSize": "14px",
							"fontWeight": "600",
							"height": "fit-content",
							"width": "fit-content",
						},
						dynamicValues=[dv("formatted_price", "innerHTML")],
					),
				],
			),
			block(
				"p",
				text="",
				visibilityCondition={"key": "short_description", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "13px",
					"height": "fit-content",
					"lineHeight": "1.5",
					"marginTop": "-6px",
					"width": "100%",
				},
				dynamicValues=[dv("short_description", "innerHTML")],
			),
		],
	)


def product_grid(refs, key, source, columns=4):
	return repeater(
		key,
		product_card(refs, source),
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


def home_blocks(refs):
	hero = section(
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
	collection_card = block(
		"a",
		name="Card · collections",
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
			"padding": "22px 22px",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			block(
				"h3",
				text="Collection",
				styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("title", "innerHTML")],
			),
			block(
				"p",
				text="",
				visibilityCondition={"key": "description", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "lineHeight": "1.5", "width": "100%"},
				dynamicValues=[dv("description", "innerHTML")],
			),
		],
	)
	collections = section(
		[
			section_header(refs, "Curated Collections", "View collections →", "/products"),
			repeater(
				"collections",
				collection_card,
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
	best_sellers = section(
		[
			section_header(refs, "Best Sellers", "View all →", "/products"),
			product_grid(refs, "featured_products", "featured"),
		],
		styles={"gap": "22px", "padding": "40px 40px"},
	)
	featured_band = section(
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
	return shell(refs, [nav(refs), hero, collections, best_sellers, featured_band, footer(refs)])


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
	header = section(
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
						],
					),
					search_form(refs),
				],
			),
			filter_bar(refs),
		],
		styles={"gap": "24px", "padding": "52px 40px 8px"},
	)
	grid = section([product_grid(refs, "products", "products", columns=3)], styles={"padding": "36px 40px 88px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


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
		attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
		styles={
			"aspectRatio": "1 / 1",
			"backgroundColor": refs["card"],
			"borderColor": refs["line"],
			"borderRadius": "2px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"display": "block",
			"objectFit": "cover",
			"width": "64px",
		},
		dynamicValues=[dv("image", "src", "attribute"), dv("alt_text", "alt", "attribute")],
	)
	return block(
		"div",
		name="Gallery",
		styles={"display": "flex", "flexDirection": "column", "gap": "12px", "width": "100%"},
		children=[
			block(
				"img",
				name="Main Image",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "eager"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["card"],
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
				text="· Ships in 48 hours · 14-day easy returns",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
			),
		],
	)
	buttons = block(
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
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"borderWidth": "0px",
					"color": refs["paper"],
					"flexGrow": "1",
					"fontSize": "12px",
					"fontWeight": "700",
					"letterSpacing": "0.08em",
					"padding": "14px 24px",
					"textTransform": "uppercase",
					"width": "100%",
				},
				dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
			),
			block(
				"a",
				text="Go to checkout",
				attrs={"href": "/checkout"},
				styles={
					"backgroundColor": refs["paper"],
					"borderColor": refs["ink"],
					"borderRadius": "2px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"flexGrow": "1",
					"fontSize": "12px",
					"fontWeight": "700",
					"height": "fit-content",
					"letterSpacing": "0.08em",
					"padding": "13px 24px",
					"textAlign": "center",
					"textDecoration": "none",
					"textTransform": "uppercase",
					"width": "100%",
				},
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
			block(
				"p",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles={"color": refs["ink"], "fontSize": "24px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("product.formatted_price", "innerHTML")],
			),
			buttons,
			error_banner(refs),
			block(
				"p",
				text="",
				visibilityCondition={"key": "product.description_text", "comesFrom": "dataScript"},
				styles={
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"color": refs["muted"],
					"fontSize": "14px",
					"height": "fit-content",
					"lineHeight": "1.7",
					"marginTop": "8px",
					"paddingTop": "18px",
					"width": "100%",
				},
				dynamicValues=[dv("product.description_text", "innerHTML")],
			),
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
	return section(
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
		styles={"gap": "28px", "padding": "24px 40px 88px"},
	)


def product_blocks(refs):
	crumbs = section([breadcrumb(refs, "product.product_name")], styles={"padding": "24px 40px 0"})
	main = section(
		[pdp_gallery(refs), pdp_details(refs)],
		styles={
			"display": "grid",
			"gap": "56px",
			"gridTemplateColumns": "minmax(0, 1fr) minmax(0, 1fr)",
			"padding": "28px 40px 48px",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)", "gap": "28px", "padding": "20px 18px 40px"},
	)
	return shell(refs, [nav(refs), crumbs, main, fabric_band(refs), footer(refs)])


def collection_blocks(refs):
	title = heading(refs, "Collection", size="30px", mobile_size="24px")
	title["dynamicValues"] = [dv("collection.title", "innerHTML")]
	header = section(
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
	grid = section([product_grid(refs, "products", "collection", columns=3)], styles={"padding": "28px 40px 88px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


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
		mobile={"flexWrap": "wrap", "gap": "10px"},
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
				name="Total Row",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				styles={
					"alignItems": "center",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"paddingTop": "4px",
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
			block(
				"a",
				text="Checkout",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				attrs={"href": "/checkout"},
				styles=black_button_styles(refs, full=True),
			),
		],
	)
	content = section(
		[heading(refs, "Your cart", size="26px", mobile_size="22px"), error_banner(refs), card],
		styles={"gap": "18px", "maxWidth": "720px", "padding": "56px 40px 88px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def input_block(refs, name, label, input_type="text", required=False, half=False):
	attrs = {"type": input_type, "name": name, "placeholder": label}
	if required:
		attrs["required"] = "required"
	return block(
		"input",
		name=f"Input · {name}",
		attrs=attrs,
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
			input_block(refs, "email", "Email address", "email", required=True),
			form_section_label(refs, "Shipping address"),
			input_block(refs, "full_name", "Full name", required=True),
			input_block(refs, "phone", "Phone", "tel"),
			input_block(refs, "address_line1", "Address", required=True),
			input_block(refs, "address_line2", "Apartment, suite, etc. (optional)"),
			input_block(refs, "city", "City", required=True, half=True),
			input_block(refs, "state", "State", half=True),
			input_block(refs, "pincode", "Pincode", half=True),
			input_block(refs, "country", "Country", half=True),
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
				text="Pay now",
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
	money_row = lambda label, bound_key=None, static_value=None, strong=False: block(
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
					money_row("Subtotal", bound_key="cart.formatted_total"),
					money_row("Shipping", static_value="Free"),
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
				children=[money_row("Total", bound_key="cart.formatted_total", strong=True)],
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
	content = section(
		[
			heading(refs, "Checkout", size="26px", mobile_size="22px"),
			error_banner(refs),
			block(
				"div",
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
	return shell(refs, [nav(refs), content, footer(refs)])


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
	info_tile = lambda title, body: block(
		"div",
		styles={
			"backgroundColor": refs["card"],
			"borderRadius": "4px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "5px",
			"padding": "16px 18px",
			"textAlign": "left",
			"width": "100%",
		},
		children=[
			block("p", text=title, styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
			block(
				"p",
				text=body,
				styles={"color": refs["muted"], "fontSize": "12px", "height": "fit-content", "lineHeight": "1.5", "width": "100%"},
			),
		],
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
					block(
						"div",
						styles={"display": "flex", "flexDirection": "row", "justifyContent": "space-between", "width": "100%"},
						children=[
							block("p", text="Shipping", styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"}),
							block("p", text="Free", styles={"color": refs["success"], "fontSize": "13px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"}),
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
	content = section(
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
					info_tile("Shipping info", "Your order ships in 48 hours. We will email you the tracking number."),
					info_tile("Order confirmation", "A receipt for this order has been sent to your email address."),
				],
			),
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
	return shell(refs, [nav(refs), content, footer(refs)])


def account_blocks(refs):
	order_row = block(
		"div",
		name="Order Row",
		styles={
			"alignItems": "center",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "grid",
			"gap": "16px",
			"gridTemplateColumns": "2fr 1fr 1fr 1fr",
			"padding": "15px 0",
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
				dynamicValues=[dv("transaction_date", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"color": refs["success"], "fontSize": "12px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("status", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"fontSize": "13px", "fontWeight": "600", "height": "fit-content", "justifySelf": "end", "width": "fit-content"},
				dynamicValues=[dv("formatted_total", "innerHTML")],
			),
		],
	)
	content = section(
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
	return shell(refs, [nav(refs), content, footer(refs)])


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
	content = section(
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
	return shell(refs, [nav(refs), content, footer(refs)])


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
	content = section(
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
	return shell(refs, [nav(refs), content, footer(refs)])


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
	content = section(
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
	return shell(refs, [nav(refs), content, footer(refs)])
