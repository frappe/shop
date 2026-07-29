"""Linen: extremely minimal monochrome storefront. Centered container, serif display, tall product cards."""

from shop.theme_generators.blocks import (
	block,
	dv,
	repeater,
	root,
	upsert_client_script,
	upsert_page,
	upsert_variables,
)

GROUP = "linen"
HEAD = "Fraunces"
BODY = "Inter"

PALETTE = {
	"paper": ("#FFFFFF", "#121212"),
	"ink": ("#111111", "#F2F2F2"),
	"muted": ("#6F6F6F", "#9C9C9C"),
	"line": ("#E9E9E9", "#2A2A2A"),
	"accent": ("#111111", "#F2F2F2"),
}

def data_script(fn: str, expose: tuple = ()) -> str:
	lines = [f'result = frappe.call("shop.storefront.page_data.{fn}")', "data.update(result)"]
	if expose:
		exposed = ", ".join(f'"{key}": result.get("{key}")' for key in expose)
		lines.append(f"data.page_data = {{{exposed}}}")
	return "\n".join(lines)


def generate():
	refs = upsert_variables(GROUP, PALETTE)
	styles = upsert_client_script("linen-styles", "CSS", theme_css(refs))
	pages = [
		("linen-home", "Home", "home", home_blocks(refs), "home", (), False),
		("linen-products", "Products", "products", products_blocks(refs), "listing", (), False),
		("linen-product", "Product", "product/:slug", product_blocks(refs), "product_page", ("product",), False),
		("linen-collection", "Collection", "collection/:slug", collection_blocks(refs), "collection_page", (), False),
		("linen-cart", "Cart", "cart", cart_blocks(refs), "cart_page", ("cart",), False),
		("linen-checkout", "Checkout", "checkout", checkout_blocks(refs), "checkout_page", ("cart",), False),
		(
			"linen-order-confirmation",
			"Order Confirmed",
			"order-confirmation/:order_id",
			confirmation_blocks(refs),
			"order_confirmation",
			(),
			False,
		),
		("linen-account-orders", "Your Orders", "account/orders", account_blocks(refs), "account_orders", (), True),
		("linen-about", "About", "about", about_blocks(refs), "basic", (), False),
		("linen-contact", "Contact", "contact", contact_blocks(refs), "basic", (), False),
		("linen-faq", "FAQ", "faq", faq_blocks(refs), "basic", (), False),
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
a, button {{ transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease; }}
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
		"maxWidth": "1160px",
		"padding": "48px 40px",
		"width": "100%",
	}
	base.update(styles or {})
	return block("div", styles=base, mobile=mobile or {"padding": "28px 18px"}, children=children)


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
			"fontSize": "22px",
			"fontWeight": "600",
			"height": "fit-content",
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
			"backgroundColor": refs["accent"],
			"borderRadius": "2px",
			"color": refs["paper"],
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
			"width": "fit-content",
			**{k: v for k, v in link_style.items() if k not in ("width",)},
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
					"maxWidth": "1160px",
					"padding": "18px 40px",
					"width": "100%",
				},
				mobile={"padding": "14px 18px"},
				children=[
					brand,
					block(
						"div",
						styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "28px"},
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
			"padding": "32px 40px",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "gap": "24px", "marginBottom": "12px"},
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
			"borderRadius": "0px",
			"color": "#B3261E",
			"display": "none",
			"fontSize": "14px",
			"marginTop": "16px",
			"padding": "12px 16px",
			"width": "100%",
		},
	)


def heading(refs, text, size="40px", mobile_size="28px", element="h1"):
	return block(
		element,
		text=text,
		styles={
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": size,
			"fontWeight": "600",
			"height": "fit-content",
			"lineHeight": "1.15",
			"width": "fit-content",
		},
		mobile={"fontSize": mobile_size},
	)


def product_card(refs, source="featured products"):
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
					"backgroundColor": refs["line"],
					"borderRadius": "0px",
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
	)


def product_grid(refs, key, source):
	return repeater(
		key,
		product_card(refs, source),
		{
			"display": "grid",
			"gap": "28px 20px",
			"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "20px 12px"},
		tablet={"gridTemplateColumns": "repeat(3, minmax(0, 1fr))"},
		name=f"Grid · {source}",
	)


def home_blocks(refs):
	hero = section(
		[
			block(
				"p",
				text="New season, quiet objects",
				styles={
					"color": refs["accent"],
					"fontSize": "13px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.12em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
			),
			block(
				"h1",
				text="Everyday things, made to keep",
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "64px",
					"fontWeight": "600",
					"height": "fit-content",
					"lineHeight": "1.08",
					"maxWidth": "700px",
					"width": "100%",
				},
				mobile={"fontSize": "36px"},
			),
			block(
				"a",
				text="Shop all products",
				attrs={"href": "/products"},
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"color": refs["paper"],
					"fontSize": "15px",
					"fontWeight": "600",
					"height": "fit-content",
					"marginTop": "12px",
					"padding": "14px 28px",
					"textDecoration": "none",
					"width": "fit-content",
				},
			),
		],
		styles={"gap": "20px", "padding": "96px 40px 72px"},
		mobile={"padding": "48px 18px 40px"},
	)
	collection_card = block(
		"a",
		name="Card · collections",
		attrs={"href": "#"},
		styles={
			"backgroundColor": refs["line"],
			"borderRadius": "0px",
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "6px",
			"padding": "28px 24px",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			block(
				"h3",
				text="Collection",
				styles={"fontFamily": HEAD, "fontSize": "20px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
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
			heading(refs, "Collections", size="28px", mobile_size="22px", element="h2"),
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
		styles={"gap": "24px"},
	)
	featured = section(
		[
			heading(refs, "Featured", size="28px", mobile_size="22px", element="h2"),
			product_grid(refs, "featured_products", "featured"),
		],
		styles={"gap": "24px", "paddingBottom": "80px"},
	)
	return shell(refs, [nav(refs), hero, collections, featured, footer(refs)])


def products_blocks(refs):
	search = block(
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
					"borderRadius": "0px",
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
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "0px",
					"borderWidth": "0px",
					"color": refs["paper"],
					"fontSize": "14px",
					"fontWeight": "600",
					"padding": "10px 18px",
					"width": "fit-content",
				},
			),
		],
	)
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
				children=[heading(refs, "All products"), search],
			),
			filter_bar(refs),
		],
		styles={"gap": "24px", "padding": "56px 40px 8px"},
	)
	grid = section([product_grid(refs, "products", "products")], styles={"paddingBottom": "80px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


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
			"paddingTop": "20px",
			"width": "100%",
		},
		name="Filters",
	)


def product_blocks(refs):
	option_button = block(
		"button",
		name="Option",
		text="Value",
		attrs={"type": "button", "data-shop": "variant-option"},
		styles={
			"backgroundColor": refs["paper"],
			"borderColor": refs["line"],
			"borderRadius": "0px",
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
					"fontSize": "40px",
					"fontWeight": "600",
					"height": "fit-content",
					"lineHeight": "1.1",
					"width": "100%",
				},
				mobile={"fontSize": "28px"},
				dynamicValues=[dv("product.product_name", "innerHTML")],
			),
			block(
				"p",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles={"color": refs["accent"], "fontSize": "20px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
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
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"borderWidth": "0px",
					"color": refs["paper"],
					"fontSize": "15px",
					"fontWeight": "600",
					"marginTop": "6px",
					"padding": "15px 32px",
					"width": "fit-content",
				},
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
					"aspectRatio": "4 / 5",
					"backgroundColor": refs["line"],
					"borderRadius": "0px",
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
		styles={
			"display": "grid",
			"gap": "56px",
			"gridTemplateColumns": "minmax(0, 1fr) minmax(0, 1fr)",
			"padding": "56px 40px 80px",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)", "gap": "28px", "padding": "24px 18px 48px"},
	)
	return shell(refs, [nav(refs), main, footer(refs)])


def collection_blocks(refs):
	header = section(
		[
			heading(refs, "Collection", size="44px", mobile_size="30px"),
			block(
				"p",
				text="",
				visibilityCondition={"key": "collection.description", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "16px", "height": "fit-content", "lineHeight": "1.6", "maxWidth": "560px", "width": "100%"},
				dynamicValues=[dv("collection.description", "innerHTML")],
			),
		],
		styles={"gap": "14px", "padding": "64px 40px 16px"},
	)
	header["children"][0]["dynamicValues"] = [dv("collection.title", "innerHTML")]
	grid = section([product_grid(refs, "products", "collection")], styles={"paddingBottom": "80px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


def cart_blocks(refs):
	qty_button = {
		"alignItems": "center",
		"backgroundColor": refs["paper"],
		"borderColor": refs["line"],
		"borderRadius": "0px",
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
			"alignItems": "center",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "18px",
			"padding": "18px 0",
			"width": "100%",
		},
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["line"],
					"borderRadius": "0px",
					"display": "block",
					"objectFit": "cover",
					"width": "72px",
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
				{"display": "flex", "flexDirection": "column", "marginTop": "8px", "width": "100%"},
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
					"marginTop": "24px",
					"width": "100%",
				},
				children=[
					block("p", text="Total", styles={"fontSize": "16px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
					block(
						"p",
						text="",
						styles={"fontFamily": HEAD, "fontSize": "24px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
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
					"alignSelf": "flex-end",
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"color": refs["paper"],
					"fontSize": "15px",
					"fontWeight": "600",
					"height": "fit-content",
					"marginTop": "16px",
					"padding": "14px 32px",
					"textDecoration": "none",
					"width": "fit-content",
				},
				mobile={"alignSelf": "stretch", "textAlign": "center", "width": "100%"},
			),
		],
		styles={"gap": "4px", "maxWidth": "860px", "padding": "56px 40px 80px"},
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
			"borderRadius": "0px",
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
			"borderColor": refs["line"],
			"borderRadius": "0px",
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
	form = block(
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
					"backgroundColor": refs["accent"],
					"borderRadius": "2px",
					"borderWidth": "0px",
					"color": refs["paper"],
					"fontSize": "15px",
					"fontWeight": "600",
					"gridColumn": "span 2",
					"marginTop": "8px",
					"padding": "15px 32px",
					"width": "100%",
				},
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
			"backgroundColor": refs["line"],
			"borderRadius": "0px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"height": "fit-content",
			"padding": "24px",
			"width": "100%",
		},
		children=[
			block("h2", text="Order summary", styles={"fontFamily": HEAD, "fontSize": "20px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"}),
			repeater(
				"cart.items",
				summary_row,
				{"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
				name="Summary Items",
			),
			block(
				"div",
				styles={
					"borderTopColor": refs["muted"],
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
	content = section(
		[
			heading(refs, "Checkout"),
			error_banner(refs),
			block(
				"div",
				styles={
					"display": "grid",
					"gap": "40px",
					"gridTemplateColumns": "minmax(0, 3fr) minmax(0, 2fr)",
					"marginTop": "24px",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)", "gap": "24px"},
				children=[form, summary],
			),
		],
		styles={"padding": "56px 40px 80px"},
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
	content = section(
		[
			block(
				"p",
				text="✓",
				styles={
					"alignItems": "center",
					"backgroundColor": refs["accent"],
					"borderRadius": "2px",
					"color": refs["paper"],
					"display": "flex",
					"fontSize": "22px",
					"height": "48px",
					"justifyContent": "center",
					"width": "48px",
				},
			),
			heading(refs, "Thank you for your order"),
			block(
				"p",
				text="Order",
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("order.name", "innerHTML")],
			),
			repeater(
				"order.items",
				item_row,
				{"display": "flex", "flexDirection": "column", "marginTop": "20px", "width": "100%"},
				name="Order Items",
			),
			block(
				"div",
				styles={
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"marginTop": "16px",
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
					"color": refs["accent"],
					"fontSize": "15px",
					"fontWeight": "600",
					"height": "fit-content",
					"marginTop": "20px",
					"textDecoration": "none",
					"width": "fit-content",
				},
			),
		],
		styles={"gap": "10px", "maxWidth": "640px", "padding": "72px 40px 96px"},
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
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "16px 0",
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
				styles={"color": refs["accent"], "fontSize": "13px", "fontWeight": "600", "height": "fit-content", "width": "fit-content"},
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
				{"display": "flex", "flexDirection": "column", "marginTop": "16px", "width": "100%"},
				name="Orders",
			),
		],
		styles={"maxWidth": "860px", "padding": "56px 40px 80px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def kicker(refs, text):
	return block(
		"p",
		text=text,
		styles={
			"color": refs["muted"],
			"fontSize": "12px",
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "0.12em",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
	)


def paragraph(refs, text, size="16px"):
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
					"fontSize": "28px",
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
			heading(refs, "A small shop for considered objects", size="44px", mobile_size="30px"),
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
					"marginTop": "16px",
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
		styles={"gap": "18px", "maxWidth": "760px", "padding": "72px 40px 96px"},
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
			"padding": "16px 0",
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
	content = section(
		[
			kicker(refs, "Contact"),
			heading(refs, "Get in touch", size="44px", mobile_size="30px"),
			paragraph(refs, "Questions about an order, a product or anything else. We reply within a day."),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "marginTop": "12px", "width": "100%"},
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
				styles={
					"backgroundColor": refs["ink"],
					"borderRadius": "2px",
					"color": refs["paper"],
					"fontSize": "15px",
					"fontWeight": "600",
					"height": "fit-content",
					"marginTop": "20px",
					"padding": "14px 28px",
					"textDecoration": "none",
					"width": "fit-content",
				},
			),
		],
		styles={"gap": "18px", "maxWidth": "760px", "padding": "72px 40px 96px"},
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
			"padding": "20px 0",
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
	content = section(
		[
			kicker(refs, "FAQ"),
			heading(refs, "Frequently asked questions", size="44px", mobile_size="30px"),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "column", "marginTop": "12px", "width": "100%"},
				children=[entry(question, answer) for question, answer in FAQS],
			),
		],
		styles={"gap": "18px", "maxWidth": "760px", "padding": "72px 40px 96px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])
