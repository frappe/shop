"""Slate: light grey monochrome storefront. White cards on a grey ground, soft 10px geometry, centered narrow PDP."""

from shop.theme_generators.blocks import (
	block,
	dv,
	repeater,
	root,
	upsert_client_script,
	upsert_page,
	upsert_variables,
)

GROUP = "slate"
HEAD = "Instrument Sans"
BODY = "Inter"

PALETTE = {
	"paper": ("#F6F6F5", "#191919"),
	"ink": ("#161616", "#EDEDEB"),
	"muted": ("#7A7A7A", "#9A9A9A"),
	"line": ("#E2E2E0", "#2C2C2C"),
	"card": ("#FFFFFF", "#202020"),
	"accent": ("#161616", "#EDEDEB"),
}


def data_script(fn: str, expose: tuple = ()) -> str:
	lines = [f'result = frappe.call("shop.storefront.page_data.{fn}")', "data.update(result)"]
	if expose:
		exposed = ", ".join(f'"{key}": result.get("{key}")' for key in expose)
		lines.append(f"data.page_data = {{{exposed}}}")
	return "\n".join(lines)


def generate():
	refs = upsert_variables(GROUP, PALETTE)
	styles = upsert_client_script("slate-styles", "CSS", theme_css(refs))
	pages = [
		("slate-home", "Home", "home", home_blocks(refs), "home", (), False),
		("slate-products", "Products", "products", products_blocks(refs), "listing", (), False),
		("slate-product", "Product", "product/:slug", product_blocks(refs), "product_page", ("product",), False),
		("slate-collection", "Collection", "collection/:slug", collection_blocks(refs), "collection_page", (), False),
		("slate-cart", "Cart", "cart", cart_blocks(refs), "cart_page", ("cart",), False),
		("slate-checkout", "Checkout", "checkout", checkout_blocks(refs), "checkout_page", ("cart",), False),
		(
			"slate-order-confirmation",
			"Order Confirmed",
			"order-confirmation/:order_id",
			confirmation_blocks(refs),
			"order_confirmation",
			(),
			False,
		),
		("slate-account-orders", "Your Orders", "account/orders", account_blocks(refs), "account_orders", (), True),
		("slate-about", "About", "about", about_blocks(refs), "basic", (), False),
		("slate-contact", "Contact", "contact", contact_blocks(refs), "basic", (), False),
		("slate-faq", "FAQ", "faq", faq_blocks(refs), "basic", (), False),
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
body {{ background: {refs["paper"]}; }}
button {{ cursor: pointer; }}
button:disabled {{ opacity: 0.45; cursor: not-allowed; }}
a, button {{ transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease, border-color 0.15s ease; }}
a:hover {{ opacity: 0.7; }}
:focus-visible {{ outline: 2px solid {refs["accent"]}; outline-offset: 2px; }}
[data-shop="variant-option"][data-selected="true"] {{
	background: {refs["ink"]};
	color: {refs["card"]};
	border-color: {refs["ink"]};
}}
[data-shop="cart-count"][data-empty="true"] {{ display: none; }}
a[data-active="true"] {{
	background: {refs["ink"]};
	color: {refs["card"]};
	border-color: {refs["ink"]};
}}
input, textarea {{ font-family: inherit; }}
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
		"maxWidth": "1120px",
		"padding": "32px",
		"width": "100%",
	}
	base.update(styles or {})
	return block("div", styles=base, mobile=mobile or {"padding": "20px 16px"}, children=children)


def card_styles(refs, padding="24px"):
	return {
		"backgroundColor": refs["card"],
		"borderRadius": "10px",
		"padding": padding,
	}


def button_styles(refs):
	return {
		"backgroundColor": refs["ink"],
		"borderRadius": "8px",
		"borderWidth": "0px",
		"color": refs["card"],
		"fontSize": "14px",
		"fontWeight": "600",
		"padding": "13px 26px",
		"textDecoration": "none",
		"width": "fit-content",
	}


def heading(refs, text, size="36px", mobile_size="26px", element="h1"):
	return block(
		element,
		text=text,
		styles={
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": size,
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "-0.02em",
			"lineHeight": "1.15",
			"width": "fit-content",
		},
		mobile={"fontSize": mobile_size},
	)


def kicker(refs, text):
	return block(
		"p",
		text=text,
		styles={
			"color": refs["muted"],
			"fontSize": "12px",
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "0.1em",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
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


def nav(refs):
	link_style = {
		"color": refs["ink"],
		"fontSize": "14px",
		"fontWeight": "500",
		"height": "fit-content",
		"textDecoration": "none",
		"width": "fit-content",
	}
	brand = block(
		"a",
		name="Brand",
		text="Shop",
		attrs={"href": "/"},
		styles={
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": "19px",
			"fontWeight": "700",
			"height": "fit-content",
			"letterSpacing": "-0.01em",
			"textDecoration": "none",
			"width": "fit-content",
		},
		dynamicValues=[dv("store.name", "innerHTML")],
	)
	badge = block(
		"span",
		text="0",
		attrs={"data-shop": "cart-count", "data-empty": "true"},
		styles={
			"alignItems": "center",
			"backgroundColor": refs["ink"],
			"borderRadius": "6px",
			"color": refs["card"],
			"display": "flex",
			"fontSize": "11px",
			"fontWeight": "700",
			"height": "18px",
			"justifyContent": "center",
			"minWidth": "18px",
			"padding": "0 5px",
		},
	)
	cart_link = block(
		"a",
		name="Cart Link",
		attrs={"href": "/cart"},
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"gap": "8px",
			"textDecoration": "none",
			**{k: v for k, v in link_style.items() if k not in ("width",)},
			"width": "fit-content",
		},
		children=[
			block("span", text="Cart", styles={"fontSize": "14px", "fontWeight": "500", "width": "fit-content", "height": "fit-content"}),
			badge,
		],
	)
	return block(
		"div",
		name="Nav",
		styles={
			"alignItems": "center",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"flexShrink": 0,
			"justifyContent": "space-between",
			"padding": "16px 32px",
			"width": "100%",
		},
		mobile={"padding": "13px 16px"},
		children=[
			brand,
			block(
				"div",
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "26px"},
				mobile={"gap": "16px"},
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


def footer(refs):
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
			"padding": "28px 32px",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "22px", "justifyContent": "center", "marginBottom": "12px"},
				children=[
					block(
						"a",
						text=label,
						attrs={"href": href},
						styles={
							"color": refs["muted"],
							"fontSize": "13px",
							"height": "fit-content",
							"textDecoration": "none",
							"width": "fit-content",
						},
					)
					for label, href in (
						("Shop all", "/products"),
						("About", "/about"),
						("Contact", "/contact"),
						("FAQ", "/faq"),
					)
				],
			),
			block(
				"p",
				text="Shop",
				styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("store.name", "innerHTML")],
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
			"backgroundColor": "#FDECEA",
			"borderRadius": "8px",
			"color": "#B3261E",
			"display": "none",
			"fontSize": "14px",
			"marginTop": "16px",
			"padding": "12px 16px",
			"width": "100%",
		},
	)


def product_card(refs, source="products"):
	return block(
		"a",
		name=f"Card · {source}",
		attrs={"href": "#"},
		styles={
			**card_styles(refs, padding="14px"),
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["paper"],
					"borderRadius": "6px",
					"display": "block",
					"objectFit": "cover",
					"width": "100%",
				},
				dynamicValues=[dv("image", "src", "attribute"), dv("product_name", "alt", "attribute")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "gap": "3px", "padding": "0 4px 4px"},
				children=[
					block(
						"h3",
						text="Product",
						styles={
							"fontSize": "15px",
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
						styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("formatted_price", "innerHTML")],
					),
				],
			),
		],
	)


def product_grid(refs, key, source):
	return repeater(
		key,
		product_card(refs, source),
		{
			"display": "grid",
			"gap": "16px",
			"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "repeat(1, minmax(0, 1fr))"},
		tablet={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
		name=f"Grid · {source}",
	)


def home_blocks(refs):
	hero = section(
		[
			block(
				"div",
				name="Hero Card",
				styles={
					**card_styles(refs, padding="56px"),
					"display": "flex",
					"flexDirection": "column",
					"gap": "18px",
					"width": "100%",
				},
				mobile={"padding": "28px 20px"},
				children=[
					kicker(refs, "New season, quiet objects"),
					block(
						"h1",
						text="Everyday things, made to keep",
						styles={
							"color": refs["ink"],
							"fontFamily": HEAD,
							"fontSize": "58px",
							"fontWeight": "600",
							"height": "fit-content",
							"letterSpacing": "-0.03em",
							"lineHeight": "1.05",
							"maxWidth": "640px",
							"width": "100%",
						},
						mobile={"fontSize": "34px"},
					),
					block(
						"p",
						text="Considered essentials in one calm, grey palette.",
						styles={
							"color": refs["muted"],
							"fontSize": "16px",
							"height": "fit-content",
							"lineHeight": "1.6",
							"maxWidth": "440px",
							"width": "100%",
						},
					),
					block(
						"a",
						text="Shop all products",
						attrs={"href": "/products"},
						styles={**button_styles(refs), "marginTop": "10px"},
					),
				],
			),
		],
		styles={"padding": "32px 32px 8px"},
	)
	collection_card = block(
		"a",
		name="Card · collections",
		attrs={"href": "#"},
		styles={
			**card_styles(refs, padding="24px"),
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "6px",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			block(
				"h3",
				text="Collection",
				styles={"fontFamily": HEAD, "fontSize": "18px", "fontWeight": "600", "height": "fit-content", "letterSpacing": "-0.01em", "width": "fit-content"},
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
			heading(refs, "Collections", size="24px", mobile_size="20px", element="h2"),
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
		styles={"gap": "18px", "padding": "24px 32px"},
	)
	featured = section(
		[
			heading(refs, "Featured", size="24px", mobile_size="20px", element="h2"),
			product_grid(refs, "featured_products", "featured"),
		],
		styles={"gap": "18px", "padding": "24px 32px 64px"},
	)
	return shell(refs, [nav(refs), hero, collections, featured, footer(refs)])


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
					"backgroundColor": refs["card"],
					"borderColor": refs["line"],
					"borderRadius": "8px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"fontSize": "14px",
					"padding": "10px 14px",
					"width": "240px",
				},
				mobile={"width": "100%"},
			),
			block(
				"button",
				text="Search",
				attrs={"type": "submit"},
				styles={**button_styles(refs), "padding": "10px 18px"},
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
			"backgroundColor": refs["card"],
			"borderColor": refs["line"],
			"borderRadius": "8px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "13px",
			"height": "fit-content",
			"padding": "6px 14px",
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
			"gap": "16px",
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
					"minWidth": "90px",
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
			"marginTop": "24px",
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
				children=[heading(refs, "All products", size="40px", mobile_size="28px"), search_form(refs)],
			),
			filter_bar(refs),
		],
		styles={"padding": "48px 32px 24px"},
	)
	grid = section([product_grid(refs, "products", "products")], styles={"paddingBottom": "64px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


def product_blocks(refs):
	option_button = block(
		"button",
		name="Option",
		text="Value",
		attrs={"type": "button", "data-shop": "variant-option"},
		styles={
			"backgroundColor": refs["card"],
			"borderColor": refs["line"],
			"borderRadius": "8px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "14px",
			"padding": "9px 16px",
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
					"fontSize": "12px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.08em",
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
	details = block(
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
					"fontSize": "38px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "-0.02em",
					"lineHeight": "1.15",
					"width": "100%",
				},
				mobile={"fontSize": "26px"},
				dynamicValues=[dv("product.product_name", "innerHTML")],
			),
			block(
				"p",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles={"color": refs["ink"], "fontSize": "19px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("product.formatted_price", "innerHTML")],
			),
			block(
				"p",
				text="",
				visibilityCondition={"key": "product.short_description", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "lineHeight": "1.6", "width": "100%"},
				dynamicValues=[dv("product.short_description", "innerHTML")],
			),
			repeater(
				"product.attribute_options",
				attribute_group,
				{"display": "flex", "flexDirection": "column", "gap": "18px", "width": "100%"},
				name="Variant Picker",
			),
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
				styles={**button_styles(refs), "fontSize": "15px", "marginTop": "6px", "padding": "14px 30px"},
				mobile={"width": "100%"},
				dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
			),
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
					"marginTop": "10px",
					"paddingTop": "18px",
					"width": "100%",
				},
				dynamicValues=[dv("product.description_text", "innerHTML")],
			),
		],
	)
	main = section(
		[
			block(
				"img",
				name="Main Image",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "eager"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["card"],
					"borderRadius": "10px",
					"display": "block",
					"objectFit": "cover",
					"width": "100%",
				},
				dynamicValues=[
					dv("product.image", "src", "attribute"),
					dv("product.product_name", "alt", "attribute"),
				],
			),
			details,
		],
		styles={"gap": "32px", "maxWidth": "720px", "padding": "48px 32px 64px"},
		mobile={"gap": "20px", "padding": "20px 16px 48px"},
	)
	return shell(refs, [nav(refs), main, footer(refs)])


def collection_blocks(refs):
	header = section(
		[
			heading(refs, "Collection", size="40px", mobile_size="28px"),
			block(
				"p",
				text="",
				visibilityCondition={"key": "collection.description", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "16px", "height": "fit-content", "lineHeight": "1.6", "maxWidth": "560px", "width": "100%"},
				dynamicValues=[dv("collection.description", "innerHTML")],
			),
		],
		styles={"gap": "12px", "padding": "48px 32px 12px"},
	)
	header["children"][0]["dynamicValues"] = [dv("collection.title", "innerHTML")]
	grid = section([product_grid(refs, "products", "collection")], styles={"paddingBottom": "64px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


def cart_blocks(refs):
	qty_button = {
		"alignItems": "center",
		"backgroundColor": refs["paper"],
		"borderColor": refs["line"],
		"borderRadius": "8px",
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["ink"],
		"display": "flex",
		"fontSize": "15px",
		"height": "30px",
		"justifyContent": "center",
		"width": "30px",
	}
	line_item = block(
		"div",
		name="Line Item",
		styles={
			**card_styles(refs, padding="16px"),
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"gap": "18px",
			"width": "100%",
		},
		mobile={"flexWrap": "wrap", "gap": "12px"},
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["paper"],
					"borderRadius": "6px",
					"display": "block",
					"objectFit": "cover",
					"width": "64px",
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
						styles={"fontSize": "15px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("product_name", "innerHTML")],
					),
					block(
						"p",
						text="",
						styles={"color": refs["muted"], "fontSize": "13px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("formatted_rate", "innerHTML")],
					),
				],
			),
			block(
				"div",
				name="Qty",
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "10px"},
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
						styles={"fontSize": "14px", "minWidth": "20px", "textAlign": "center", "width": "fit-content"},
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
				styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "minWidth": "90px", "textAlign": "right", "width": "fit-content"},
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
					"fontSize": "13px",
					"textDecoration": "underline",
					"width": "fit-content",
				},
				dynamicValues=[dv("item_code", "data-item-code", "attribute")],
			),
		],
	)
	content = section(
		[
			heading(refs, "Your cart"),
			error_banner(refs),
			block(
				"p",
				text="Your cart is empty.",
				visibilityCondition={"key": "cart.is_empty", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "marginTop": "16px", "width": "fit-content"},
			),
			repeater(
				"cart.items",
				line_item,
				{"display": "flex", "flexDirection": "column", "gap": "12px", "marginTop": "20px", "width": "100%"},
				name="Line Items",
			),
			block(
				"div",
				name="Summary",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				styles={
					"alignItems": "center",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"marginTop": "20px",
					"width": "100%",
				},
				children=[
					block("p", text="Total", styles={"fontSize": "16px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
					block(
						"p",
						text="",
						styles={"fontFamily": HEAD, "fontSize": "24px", "fontWeight": "600", "height": "fit-content", "letterSpacing": "-0.01em", "width": "fit-content"},
						dynamicValues=[dv("cart.formatted_total", "innerHTML")],
					),
				],
			),
			block(
				"a",
				text="Checkout",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				attrs={"href": "/checkout"},
				styles={
					**button_styles(refs),
					"alignSelf": "flex-end",
					"fontSize": "15px",
					"height": "fit-content",
					"marginTop": "14px",
					"padding": "13px 30px",
				},
				mobile={"alignSelf": "stretch", "textAlign": "center", "width": "100%"},
			),
		],
		styles={"gap": "4px", "maxWidth": "760px", "padding": "48px 32px 64px"},
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
			"borderRadius": "8px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "14px",
			"gridColumn": "span 1" if half else "span 2",
			"padding": "12px 14px",
			"width": "100%",
		},
	)


def checkout_blocks(refs):
	payment_option = block(
		"label",
		name="Payment Method",
		styles={
			"alignItems": "center",
			"backgroundColor": refs["paper"],
			"borderColor": refs["line"],
			"borderRadius": "8px",
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
				styles={"accentColor": refs["accent"], "height": "16px", "width": "16px"},
				dynamicValues=[dv("method", "value", "attribute")],
			),
			block(
				"span",
				text="Payment",
				styles={"fontSize": "14px", "width": "fit-content", "height": "fit-content"},
				dynamicValues=[dv("label", "innerHTML")],
			),
		],
	)
	summary_row = block(
		"div",
		name="Summary Row",
		styles={
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="Item",
				styles={"color": refs["ink"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("product_name", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
		],
	)
	summary = block(
		"div",
		name="Order Summary",
		styles={
			**card_styles(refs, padding="24px"),
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"width": "100%",
		},
		children=[
			block("h2", text="Order summary", styles={"fontFamily": HEAD, "fontSize": "18px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
			repeater(
				"cart.items",
				summary_row,
				{"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
				name="Summary Items",
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
					"paddingTop": "12px",
					"width": "100%",
				},
				children=[
					block("p", text="Total", styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
					block(
						"p",
						text="",
						styles={"fontSize": "18px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("cart.formatted_total", "innerHTML")],
					),
				],
			),
		],
	)
	form_card = block(
		"div",
		name="Form Card",
		styles={
			**card_styles(refs, padding="24px"),
			"display": "flex",
			"flexDirection": "column",
			"gap": "14px",
			"width": "100%",
		},
		children=[
			block("h2", text="Delivery details", styles={"fontFamily": HEAD, "fontSize": "18px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
			block(
				"form",
				name="Checkout Form",
				attrs={"data-shop": "checkout-form"},
				styles={"display": "grid", "gap": "12px", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "width": "100%"},
				children=[
					input_block(refs, "email", "Email", "email", required=True),
					input_block(refs, "full_name", "Full name", required=True),
					input_block(refs, "phone", "Phone", "tel"),
					input_block(refs, "address_line1", "Address", required=True),
					input_block(refs, "address_line2", "Apartment, floor (optional)"),
					input_block(refs, "city", "City", required=True, half=True),
					input_block(refs, "state", "State", half=True),
					input_block(refs, "pincode", "Pincode", half=True),
					input_block(refs, "country", "Country", half=True),
					repeater(
						"payment_methods",
						payment_option,
						{"display": "flex", "flexDirection": "column", "gap": "8px", "gridColumn": "span 2", "width": "100%"},
						name="Payment Methods",
					),
					block(
						"button",
						text="Place order",
						attrs={"type": "submit"},
						styles={
							**button_styles(refs),
							"fontSize": "15px",
							"gridColumn": "span 2",
							"marginTop": "6px",
							"padding": "14px 30px",
							"width": "100%",
						},
					),
				],
			),
		],
	)
	content = section(
		[
			heading(refs, "Checkout"),
			error_banner(refs),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "gap": "16px", "marginTop": "20px", "width": "100%"},
				children=[summary, form_card],
			),
		],
		styles={"maxWidth": "680px", "padding": "48px 32px 64px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def confirmation_blocks(refs):
	item_row = block(
		"div",
		name="Order Item",
		styles={
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
				styles={"display": "flex", "flexDirection": "row", "gap": "8px"},
				children=[
					block(
						"p",
						text="Item",
						styles={"fontSize": "14px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("item_name", "innerHTML")],
					),
					block(
						"p",
						text="",
						styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("qty", "innerHTML")],
					),
				],
			),
			block(
				"p",
				text="",
				styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
		],
	)
	card = block(
		"div",
		name="Confirmation Card",
		styles={
			**card_styles(refs, padding="32px"),
			"display": "flex",
			"flexDirection": "column",
			"gap": "10px",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="✓",
				styles={
					"alignItems": "center",
					"backgroundColor": refs["ink"],
					"borderRadius": "10px",
					"color": refs["card"],
					"display": "flex",
					"fontSize": "22px",
					"height": "48px",
					"justifyContent": "center",
					"marginBottom": "8px",
					"width": "48px",
				},
			),
			heading(refs, "Thank you for your order", size="30px", mobile_size="24px"),
			block(
				"p",
				text="Order",
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("order.name", "innerHTML")],
			),
			repeater(
				"order.items",
				item_row,
				{"display": "flex", "flexDirection": "column", "marginTop": "16px", "width": "100%"},
				name="Order Items",
			),
			block(
				"div",
				styles={
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"marginTop": "12px",
					"width": "100%",
				},
				children=[
					block("p", text="Grand total", styles={"fontSize": "15px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
					block(
						"p",
						text="",
						styles={"fontFamily": HEAD, "fontSize": "22px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
						dynamicValues=[dv("order.formatted_grand_total", "innerHTML")],
					),
				],
			),
			block(
				"a",
				text="Continue shopping",
				attrs={"href": "/products"},
				styles={
					"color": refs["ink"],
					"fontSize": "15px",
					"fontWeight": "600",
					"height": "fit-content",
					"marginTop": "14px",
					"textDecoration": "underline",
					"width": "fit-content",
				},
			),
		],
	)
	content = section([card], styles={"maxWidth": "640px", "padding": "56px 32px 80px"})
	return shell(refs, [nav(refs), content, footer(refs)])


def account_blocks(refs):
	order_row = block(
		"div",
		name="Order Row",
		styles={
			**card_styles(refs, padding="16px 20px"),
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="Order",
				styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("name", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("transaction_date", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"color": refs["muted"], "fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("status", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"fontSize": "14px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_total", "innerHTML")],
			),
		],
	)
	content = section(
		[
			heading(refs, "Your orders"),
			repeater(
				"orders",
				order_row,
				{"display": "flex", "flexDirection": "column", "gap": "10px", "marginTop": "20px", "width": "100%"},
				name="Orders",
			),
		],
		styles={"maxWidth": "760px", "padding": "48px 32px 64px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def content_card(refs, children):
	return section(
		[
			block(
				"div",
				name="Content Card",
				styles={
					**card_styles(refs, padding="40px"),
					"display": "flex",
					"flexDirection": "column",
					"gap": "18px",
					"width": "100%",
				},
				mobile={"padding": "24px 18px"},
				children=children,
			),
		],
		styles={"maxWidth": "760px", "padding": "48px 32px 80px"},
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
					"letterSpacing": "-0.01em",
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
	return shell(
		refs,
		[
			nav(refs),
			content_card(
				refs,
				[
					kicker(refs, "About"),
					heading(refs, "A small shop for considered objects", size="34px", mobile_size="26px"),
					paragraph(
						refs,
						"We started with a simple idea: fewer, better things. Every product in this "
						"store is chosen for how it is made, how long it lasts and how it feels to "
						"use every day.",
					),
					paragraph(
						refs,
						"We work directly with small workshops, keep our margins honest and stand "
						"behind everything we sell. If something is not right, write to us and we "
						"will fix it.",
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
							"marginTop": "12px",
							"paddingTop": "24px",
							"width": "100%",
						},
						mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
						children=[
							stat("2020", "Founded"),
							stat("120+", "Products curated"),
							stat("48h", "Dispatch time"),
						],
					),
				],
			),
			footer(refs),
		],
	)


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
			"padding": "14px 0",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text=label,
				styles={"color": refs["muted"], "fontSize": "14px", "height": "fit-content", "width": "fit-content"},
			),
			block(
				"p",
				text=value,
				styles={"fontSize": "14px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
			),
		],
	)
	return shell(
		refs,
		[
			nav(refs),
			content_card(
				refs,
				[
					kicker(refs, "Contact"),
					heading(refs, "Get in touch", size="34px", mobile_size="26px"),
					paragraph(refs, "Questions about an order, a product or anything else. We reply within a day."),
					block(
						"div",
						styles={"display": "flex", "flexDirection": "column", "marginTop": "8px", "width": "100%"},
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
						styles={**button_styles(refs), "height": "fit-content", "marginTop": "14px"},
					),
				],
			),
			footer(refs),
		],
	)


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
		"Do you ship internationally?",
		"Not yet. We currently ship across India and are working on international shipping.",
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
			"gap": "8px",
			"padding": "18px 0",
			"width": "100%",
		},
		children=[
			block(
				"h3",
				text=question,
				styles={"fontSize": "16px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
			),
			paragraph(refs, answer, size="14px"),
		],
	)
	return shell(
		refs,
		[
			nav(refs),
			content_card(
				refs,
				[
					kicker(refs, "FAQ"),
					heading(refs, "Frequently asked questions", size="34px", mobile_size="26px"),
					block(
						"div",
						styles={"display": "flex", "flexDirection": "column", "marginTop": "8px", "width": "100%"},
						children=[entry(question, answer) for question, answer in FAQS],
					),
				],
			),
			footer(refs),
		],
	)
