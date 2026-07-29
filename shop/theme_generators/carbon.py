"""Carbon: monochrome dark technical storefront. Edge-to-edge hairline grid, uppercase display type."""

from shop.theme_generators.blocks import (
	block,
	dv,
	repeater,
	root,
	upsert_client_script,
	upsert_page,
	upsert_variables,
)

GROUP = "carbon"
HEAD = "Space Grotesk"
BODY = "Inter"

PALETTE = {
	"bg": ("#101010", "#0B0B0B"),
	"ink": ("#F2F2F0", "#ECECEA"),
	"muted": ("#8C8C89", "#7F7F7C"),
	"line": ("#262626", "#202020"),
	"accent": ("#F2F2F0", "#ECECEA"),
}


def data_script(fn: str, expose: tuple = ()) -> str:
	lines = [f'result = frappe.call("shop.storefront.page_data.{fn}")', "data.update(result)"]
	if expose:
		exposed = ", ".join(f'"{key}": result.get("{key}")' for key in expose)
		lines.append(f"data.page_data = {{{exposed}}}")
	return "\n".join(lines)


def generate():
	refs = upsert_variables(GROUP, PALETTE)
	styles = upsert_client_script("carbon-styles", "CSS", theme_css(refs))
	pages = [
		("carbon-home", "Home", "home", home_blocks(refs), "home", (), False),
		("carbon-products", "Products", "products", products_blocks(refs), "listing", (), False),
		("carbon-product", "Product", "product/:slug", product_blocks(refs), "product_page", ("product",), False),
		("carbon-collection", "Collection", "collection/:slug", collection_blocks(refs), "collection_page", (), False),
		("carbon-cart", "Cart", "cart", cart_blocks(refs), "cart_page", ("cart",), False),
		("carbon-checkout", "Checkout", "checkout", checkout_blocks(refs), "checkout_page", ("cart",), False),
		(
			"carbon-order-confirmation",
			"Order Confirmed",
			"order-confirmation/:order_id",
			confirmation_blocks(refs),
			"order_confirmation",
			(),
			False,
		),
		("carbon-account-orders", "Your Orders", "account/orders", account_blocks(refs), "account_orders", (), True),
		("carbon-about", "About", "about", about_blocks(refs), "basic", (), False),
		("carbon-contact", "Contact", "contact", contact_blocks(refs), "basic", (), False),
		("carbon-faq", "FAQ", "faq", faq_blocks(refs), "basic", (), False),
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
html {{ color-scheme: dark; }}
body {{ background: {refs["bg"]}; }}
button {{ cursor: pointer; }}
button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
a, button {{ transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease, border-color 0.15s ease; }}
a:hover {{ opacity: 0.65; }}
:focus-visible {{ outline: 2px solid {refs["accent"]}; outline-offset: 2px; }}
[data-shop="variant-option"][data-selected="true"] {{
	background: {refs["accent"]};
	color: {refs["bg"]};
	border-color: {refs["accent"]};
}}
[data-shop="cart-count"][data-empty="true"] {{ display: none; }}
a[data-active="true"] {{
	background: {refs["ink"]};
	color: {refs["bg"]};
	border-color: {refs["ink"]};
}}
input, textarea {{ font-family: inherit; }}
::selection {{ background: {refs["accent"]}; color: {refs["bg"]}; }}
"""


def shell(refs, children):
	return [
		root(
			{
				"backgroundColor": refs["bg"],
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
		"padding": "48px",
		"width": "100%",
	}
	base.update(styles or {})
	return block("div", styles=base, mobile=mobile or {"padding": "28px 18px"}, children=children)


def label(refs, text, color=None):
	return block(
		"p",
		text=text,
		styles={
			"color": color or refs["muted"],
			"fontFamily": HEAD,
			"fontSize": "12px",
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "0.14em",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
	)


def rule(refs, margin="0"):
	return block("div", styles={"backgroundColor": refs["line"], "height": "1px", "margin": margin, "width": "100%"})


def display_heading(refs, text, size="56px", mobile_size="32px", element="h1"):
	return block(
		element,
		text=text,
		styles={
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": size,
			"fontWeight": "700",
			"height": "fit-content",
			"letterSpacing": "-0.02em",
			"lineHeight": "1",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
		mobile={"fontSize": mobile_size},
	)


def accent_button_styles(refs):
	return {
		"backgroundColor": refs["ink"],
		"borderRadius": "0px",
		"borderWidth": "0px",
		"color": refs["bg"],
		"fontFamily": HEAD,
		"fontSize": "13px",
		"fontWeight": "700",
		"letterSpacing": "0.1em",
		"padding": "16px 32px",
		"textTransform": "uppercase",
		"width": "fit-content",
	}


def nav(refs):
	link_style = {
		"color": refs["ink"],
		"fontFamily": HEAD,
		"fontSize": "12px",
		"fontWeight": "600",
		"height": "fit-content",
		"letterSpacing": "0.12em",
		"textDecoration": "none",
		"textTransform": "uppercase",
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
			"fontSize": "18px",
			"fontWeight": "700",
			"height": "fit-content",
			"letterSpacing": "0.04em",
			"textDecoration": "none",
			"textTransform": "uppercase",
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
			"borderRadius": "0px",
			"color": refs["bg"],
			"display": "flex",
			"fontSize": "11px",
			"fontWeight": "700",
			"height": "18px",
			"justifyContent": "center",
			"minWidth": "18px",
			"padding": "0 4px",
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
			**{k: v for k, v in link_style.items() if k != "width"},
			"width": "fit-content",
		},
		children=[
			block(
				"span",
				text="Cart",
				styles={
					"fontFamily": HEAD,
					"fontSize": "12px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.12em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
			),
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
			"padding": "18px 48px",
			"width": "100%",
		},
		mobile={"padding": "14px 18px"},
		children=[
			brand,
			block(
				"div",
				styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "32px"},
				mobile={"gap": "18px"},
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
	footer_link = lambda text, href: block(
		"a",
		text=text,
		attrs={"href": href},
		styles={
			"color": refs["muted"],
			"fontFamily": HEAD,
			"fontSize": "12px",
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "0.1em",
			"textDecoration": "none",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
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
			"flexDirection": "row",
			"flexShrink": 0,
			"justifyContent": "space-between",
			"marginTop": "auto",
			"padding": "28px 48px",
			"width": "100%",
		},
		mobile={"alignItems": "flex-start", "flexDirection": "column", "gap": "16px", "padding": "20px 18px"},
		children=[
			block(
				"p",
				text="Shop",
				styles={
					"color": refs["muted"],
					"fontFamily": HEAD,
					"fontSize": "12px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.12em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
				dynamicValues=[dv("store.name", "innerHTML")],
			),
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "24px"},
				children=[
					footer_link("Shop all", "/products"),
					footer_link("About", "/about"),
					footer_link("Contact", "/contact"),
					footer_link("FAQ", "/faq"),
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
			"backgroundColor": "#2B1214",
			"borderColor": "#B3261E",
			"borderRadius": "0px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": "#FF8A80",
			"display": "none",
			"fontSize": "14px",
			"marginTop": "16px",
			"padding": "12px 16px",
			"width": "100%",
		},
	)


def collection_strip(refs):
	chip = block(
		"a",
		name="Chip",
		text="Collection",
		attrs={"href": "#"},
		styles={
			"borderRightColor": refs["line"],
			"borderRightStyle": "solid",
			"borderRightWidth": "1px",
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": "12px",
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "0.12em",
			"padding": "16px 28px",
			"textDecoration": "none",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
		dynamicValues=[dv("route", "href", "attribute"), dv("title", "innerHTML")],
	)
	return repeater(
		"collections",
		chip,
		{
			"alignItems": "center",
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"flexWrap": "wrap",
			"width": "100%",
		},
		name="Strip · collections",
	)


def product_card(refs, source="products"):
	return block(
		"a",
		name=f"Card · {source}",
		attrs={"href": "#"},
		styles={
			"backgroundColor": refs["bg"],
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"borderRightColor": refs["line"],
			"borderRightStyle": "solid",
			"borderRightWidth": "1px",
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "14px",
			"padding": "20px",
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
					"backgroundColor": refs["line"],
					"borderRadius": "0px",
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
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "row",
					"gap": "12px",
					"justifyContent": "space-between",
					"paddingTop": "12px",
					"width": "100%",
				},
				children=[
					block(
						"h3",
						text="Product",
						styles={
							"fontFamily": HEAD,
							"fontSize": "14px",
							"fontWeight": "600",
							"height": "fit-content",
							"letterSpacing": "0.02em",
							"lineHeight": "1.3",
							"textTransform": "uppercase",
							"width": "fit-content",
						},
						dynamicValues=[dv("product_name", "innerHTML")],
					),
					block(
						"p",
						text="",
						visibilityCondition={"key": "formatted_price", "comesFrom": "dataScript"},
						styles={
							"color": refs["accent"],
							"fontSize": "13px",
							"fontWeight": "600",
							"height": "fit-content",
							"width": "fit-content",
						},
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
			label(refs, "New season / Industrial objects", color=refs["accent"]),
			block(
				"h1",
				text="Hard goods for daily use",
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "104px",
					"fontWeight": "700",
					"height": "fit-content",
					"letterSpacing": "-0.03em",
					"lineHeight": "0.95",
					"textTransform": "uppercase",
					"width": "100%",
				},
				mobile={"fontSize": "44px"},
			),
			block(
				"div",
				styles={
					"alignItems": "center",
					"display": "flex",
					"flexDirection": "row",
					"gap": "24px",
					"justifyContent": "space-between",
					"marginTop": "24px",
					"width": "100%",
				},
				mobile={"alignItems": "flex-start", "flexDirection": "column", "gap": "16px"},
				children=[
					block(
						"p",
						text="Precision-made essentials. No ornament, no waste.",
						styles={
							"color": refs["muted"],
							"fontSize": "15px",
							"height": "fit-content",
							"lineHeight": "1.5",
							"maxWidth": "380px",
							"width": "100%",
						},
					),
					block("a", text="Shop all products", attrs={"href": "/products"}, styles={**accent_button_styles(refs), "textDecoration": "none"}),
				],
			),
		],
		styles={"gap": "20px", "padding": "72px 48px 56px"},
		mobile={"padding": "40px 18px 32px"},
	)
	featured_header = block(
		"div",
		styles={
			"alignItems": "center",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "20px 48px",
			"width": "100%",
		},
		mobile={"padding": "16px 18px"},
		children=[
			label(refs, "Featured", color=refs["ink"]),
			block(
				"a",
				text="View all →",
				attrs={"href": "/products"},
				styles={
					"color": refs["muted"],
					"fontFamily": HEAD,
					"fontSize": "12px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.1em",
					"textDecoration": "none",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
			),
		],
	)
	return shell(
		refs,
		[
			nav(refs),
			hero,
			rule(refs),
			collection_strip(refs),
			featured_header,
			product_grid(refs, "featured_products", "featured"),
			footer(refs),
		],
	)


def search_form(refs):
	return block(
		"form",
		name="Search",
		attrs={"data-shop": "search-form", "action": "/products"},
		styles={"display": "flex", "flexDirection": "row", "gap": "0px", "width": "fit-content"},
		mobile={"width": "100%"},
		children=[
			block(
				"input",
				attrs={"type": "search", "name": "search", "placeholder": "SEARCH"},
				styles={
					"backgroundColor": refs["bg"],
					"borderColor": refs["line"],
					"borderRadius": "0px",
					"borderStyle": "solid",
					"borderWidth": "1px",
					"color": refs["ink"],
					"fontSize": "13px",
					"letterSpacing": "0.06em",
					"padding": "12px 16px",
					"width": "240px",
				},
				mobile={"width": "100%"},
			),
			block(
				"button",
				text="Go",
				attrs={"type": "submit"},
				styles={**accent_button_styles(refs), "padding": "12px 20px"},
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
			"borderRadius": "0px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": "12px",
			"fontWeight": "600",
			"height": "fit-content",
			"letterSpacing": "0.08em",
			"padding": "7px 16px",
			"textDecoration": "none",
			"textTransform": "uppercase",
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
			"gap": "20px",
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
					"fontFamily": HEAD,
					"fontSize": "11px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.14em",
					"minWidth": "100px",
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
			"gap": "14px",
			"marginTop": "32px",
			"paddingTop": "24px",
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
				mobile={"alignItems": "stretch", "flexDirection": "column", "gap": "18px"},
				children=[display_heading(refs, "All products", size="64px", mobile_size="36px"), search_form(refs)],
			),
			filter_bar(refs),
		],
		styles={"padding": "56px 48px 40px"},
		mobile={"padding": "32px 18px 24px"},
	)
	return shell(
		refs,
		[
			nav(refs),
			header,
			rule(refs),
			product_grid(refs, "products", "products"),
			footer(refs),
		],
	)


def option_button(refs):
	return block(
		"button",
		name="Option",
		text="Value",
		attrs={"type": "button", "data-shop": "variant-option"},
		styles={
			"backgroundColor": refs["bg"],
			"borderColor": refs["line"],
			"borderRadius": "0px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontFamily": HEAD,
			"fontSize": "12px",
			"fontWeight": "600",
			"letterSpacing": "0.08em",
			"padding": "10px 18px",
			"textTransform": "uppercase",
			"width": "fit-content",
		},
		dynamicValues=[
			dv("value", "innerHTML"),
			dv("attribute", "data-attribute", "attribute"),
			dv("value", "data-value", "attribute"),
		],
	)


def product_blocks(refs):
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
					"fontFamily": HEAD,
					"fontSize": "11px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.14em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
				dynamicValues=[dv("attribute", "innerHTML")],
			),
			repeater(
				"values",
				option_button(refs),
				{"display": "flex", "flexDirection": "row", "flexWrap": "wrap", "gap": "8px", "width": "100%"},
				name="Options",
			),
		],
	)
	details = block(
		"div",
		name="Details",
		styles={
			"borderRightColor": refs["line"],
			"borderRightStyle": "solid",
			"borderRightWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "20px",
			"justifyContent": "center",
			"padding": "64px 48px",
			"width": "100%",
		},
		mobile={"borderRightWidth": "0px", "padding": "28px 18px"},
		children=[
			block(
				"h1",
				text="Product",
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "48px",
					"fontWeight": "700",
					"height": "fit-content",
					"letterSpacing": "-0.02em",
					"lineHeight": "1",
					"textTransform": "uppercase",
					"width": "100%",
				},
				mobile={"fontSize": "30px"},
				dynamicValues=[dv("product.product_name", "innerHTML")],
			),
			block(
				"p",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles={
					"color": refs["accent"],
					"fontFamily": HEAD,
					"fontSize": "22px",
					"fontWeight": "700",
					"height": "fit-content",
					"width": "fit-content",
				},
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
				styles={**accent_button_styles(refs), "marginTop": "8px", "padding": "17px 40px"},
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
					"marginTop": "8px",
					"paddingTop": "20px",
					"width": "100%",
				},
				dynamicValues=[dv("product.description_text", "innerHTML")],
			),
		],
	)
	image = block(
		"img",
		name="Main Image",
		attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "eager"},
		styles={
			"backgroundColor": refs["line"],
			"borderRadius": "0px",
			"display": "block",
			"height": "100%",
			"minHeight": "560px",
			"objectFit": "cover",
			"width": "100%",
		},
		mobile={"aspectRatio": "1 / 1", "height": "auto", "minHeight": "0px"},
		dynamicValues=[
			dv("product.image", "src", "attribute"),
			dv("product.product_name", "alt", "attribute"),
		],
	)
	split = block(
		"div",
		name="Split",
		styles={
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "grid",
			"flexGrow": "1",
			"gridTemplateColumns": "minmax(0, 1fr) minmax(0, 1fr)",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
		children=[details, image],
	)
	return shell(refs, [nav(refs), split, footer(refs)])


def collection_blocks(refs):
	header = section(
		[
			display_heading(refs, "Collection", size="64px", mobile_size="36px"),
			block(
				"p",
				text="",
				visibilityCondition={"key": "collection.description", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "15px",
					"height": "fit-content",
					"lineHeight": "1.6",
					"maxWidth": "560px",
					"width": "100%",
				},
				dynamicValues=[dv("collection.description", "innerHTML")],
			),
		],
		styles={"gap": "16px", "padding": "56px 48px 40px"},
		mobile={"padding": "32px 18px 24px"},
	)
	header["children"][0]["dynamicValues"] = [dv("collection.title", "innerHTML")]
	return shell(refs, [nav(refs), header, rule(refs), product_grid(refs, "products", "collection"), footer(refs)])


def cart_blocks(refs):
	qty_button = {
		"alignItems": "center",
		"backgroundColor": refs["bg"],
		"borderColor": refs["line"],
		"borderRadius": "0px",
		"borderStyle": "solid",
		"borderWidth": "1px",
		"color": refs["ink"],
		"display": "flex",
		"fontSize": "15px",
		"height": "32px",
		"justifyContent": "center",
		"width": "32px",
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
			"gap": "20px",
			"padding": "20px 0",
			"width": "100%",
		},
		mobile={"flexWrap": "wrap", "gap": "12px"},
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
				styles={"display": "flex", "flexDirection": "column", "flexGrow": "1", "gap": "5px"},
				children=[
					block(
						"h3",
						text="Product",
						styles={
							"fontFamily": HEAD,
							"fontSize": "14px",
							"fontWeight": "600",
							"height": "fit-content",
							"letterSpacing": "0.02em",
							"textTransform": "uppercase",
							"width": "fit-content",
						},
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
						styles={"fontSize": "14px", "minWidth": "22px", "textAlign": "center", "width": "fit-content"},
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
					"color": refs["accent"],
					"fontSize": "15px",
					"fontWeight": "600",
					"height": "fit-content",
					"minWidth": "90px",
					"textAlign": "right",
					"width": "fit-content",
				},
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
					"letterSpacing": "0.06em",
					"textDecoration": "underline",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
				dynamicValues=[dv("item_code", "data-item-code", "attribute")],
			),
		],
	)
	content = section(
		[
			display_heading(refs, "Cart", size="64px", mobile_size="36px"),
			error_banner(refs),
			block(
				"p",
				text="Your cart is empty.",
				visibilityCondition={"key": "cart.is_empty", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "marginTop": "20px", "width": "fit-content"},
			),
			repeater(
				"cart.items",
				line_item,
				{
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"marginTop": "28px",
					"width": "100%",
				},
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
					"marginTop": "28px",
					"width": "100%",
				},
				children=[
					label(refs, "Total", color=refs["ink"]),
					block(
						"p",
						text="",
						styles={
							"fontFamily": HEAD,
							"fontSize": "28px",
							"fontWeight": "700",
							"height": "fit-content",
							"width": "fit-content",
						},
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
					**accent_button_styles(refs),
					"alignSelf": "flex-end",
					"height": "fit-content",
					"marginTop": "20px",
					"textDecoration": "none",
				},
				mobile={"alignSelf": "stretch", "textAlign": "center", "width": "100%"},
			),
		],
		styles={"alignSelf": "center", "maxWidth": "880px", "padding": "56px 48px 80px"},
		mobile={"padding": "32px 18px 48px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def input_block(refs, name, label_text, input_type="text", required=False):
	attrs = {"type": input_type, "name": name, "placeholder": label_text}
	if required:
		attrs["required"] = "required"
	return block(
		"input",
		name=f"Input · {name}",
		attrs=attrs,
		styles={
			"backgroundColor": refs["bg"],
			"borderColor": refs["line"],
			"borderRadius": "0px",
			"borderStyle": "solid",
			"borderWidth": "1px",
			"color": refs["ink"],
			"fontSize": "14px",
			"padding": "13px 16px",
			"width": "100%",
		},
	)


def checkout_blocks(refs):
	summary_row = block(
		"div",
		name="Summary Row",
		styles={
			"borderBottomColor": refs["line"],
			"borderBottomStyle": "solid",
			"borderBottomWidth": "1px",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "13px 0",
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
		styles={"display": "flex", "flexDirection": "column", "marginTop": "28px", "width": "100%"},
		children=[
			label(refs, "Order summary", color=refs["ink"]),
			repeater(
				"cart.items",
				summary_row,
				{
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"marginTop": "14px",
					"width": "100%",
				},
				name="Summary Items",
			),
			block(
				"div",
				styles={
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"paddingTop": "14px",
					"width": "100%",
				},
				children=[
					label(refs, "Total", color=refs["ink"]),
					block(
						"p",
						text="",
						styles={
							"fontFamily": HEAD,
							"fontSize": "22px",
							"fontWeight": "700",
							"height": "fit-content",
							"width": "fit-content",
						},
						dynamicValues=[dv("cart.formatted_total", "innerHTML")],
					),
				],
			),
		],
	)
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
			"gap": "12px",
			"padding": "14px 16px",
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
				styles={"fontSize": "14px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("label", "innerHTML")],
			),
		],
	)
	form = block(
		"form",
		name="Checkout Form",
		attrs={"data-shop": "checkout-form"},
		styles={"display": "flex", "flexDirection": "column", "gap": "12px", "marginTop": "28px", "width": "100%"},
		children=[
			label(refs, "Delivery details", color=refs["ink"]),
			input_block(refs, "email", "Email", "email", required=True),
			input_block(refs, "full_name", "Full name", required=True),
			input_block(refs, "phone", "Phone", "tel"),
			input_block(refs, "address_line1", "Address", required=True),
			input_block(refs, "address_line2", "Apartment, floor (optional)"),
			block(
				"div",
				styles={"display": "grid", "gap": "12px", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "width": "100%"},
				mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
				children=[
					input_block(refs, "city", "City", required=True),
					input_block(refs, "state", "State"),
					input_block(refs, "pincode", "Pincode"),
					input_block(refs, "country", "Country"),
				],
			),
			repeater(
				"payment_methods",
				payment_option,
				{"display": "flex", "flexDirection": "column", "gap": "8px", "marginTop": "8px", "width": "100%"},
				name="Payment Methods",
			),
			block(
				"button",
				text="Place order",
				attrs={"type": "submit"},
				styles={**accent_button_styles(refs), "marginTop": "12px", "padding": "17px 32px", "width": "100%"},
			),
		],
	)
	content = section(
		[display_heading(refs, "Checkout", size="64px", mobile_size="36px"), error_banner(refs), summary, form],
		styles={"alignSelf": "center", "maxWidth": "720px", "padding": "56px 48px 80px"},
		mobile={"padding": "32px 18px 48px"},
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
			"padding": "13px 0",
			"width": "100%",
		},
		children=[
			block(
				"div",
				styles={"display": "flex", "flexDirection": "row", "gap": "10px"},
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
					"borderRadius": "0px",
					"color": refs["bg"],
					"display": "flex",
					"fontSize": "22px",
					"fontWeight": "700",
					"height": "48px",
					"justifyContent": "center",
					"width": "48px",
				},
			),
			display_heading(refs, "Order confirmed", size="48px", mobile_size="30px"),
			block(
				"p",
				text="Order",
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("order.name", "innerHTML")],
			),
			repeater(
				"order.items",
				item_row,
				{
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"marginTop": "24px",
					"width": "100%",
				},
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
					label(refs, "Grand total", color=refs["ink"]),
					block(
						"p",
						text="",
						styles={
							"fontFamily": HEAD,
							"fontSize": "24px",
							"fontWeight": "700",
							"height": "fit-content",
							"width": "fit-content",
						},
						dynamicValues=[dv("order.formatted_grand_total", "innerHTML")],
					),
				],
			),
			block(
				"a",
				text="Continue shopping →",
				attrs={"href": "/products"},
				styles={
					"color": refs["accent"],
					"fontFamily": HEAD,
					"fontSize": "13px",
					"fontWeight": "700",
					"height": "fit-content",
					"letterSpacing": "0.1em",
					"marginTop": "24px",
					"textDecoration": "none",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
			),
		],
		styles={"alignSelf": "center", "gap": "14px", "maxWidth": "640px", "padding": "72px 48px 96px"},
		mobile={"padding": "40px 18px 56px"},
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
				styles={
					"fontFamily": HEAD,
					"fontSize": "13px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.04em",
					"width": "fit-content",
				},
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
				styles={
					"color": refs["accent"],
					"fontSize": "12px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.08em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
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
			display_heading(refs, "Your orders", size="56px", mobile_size="32px"),
			repeater(
				"orders",
				order_row,
				{
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"marginTop": "28px",
					"width": "100%",
				},
				name="Orders",
			),
		],
		styles={"alignSelf": "center", "maxWidth": "880px", "padding": "56px 48px 80px"},
		mobile={"padding": "32px 18px 48px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


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


def content_section(refs, children):
	return section(
		children,
		styles={"alignSelf": "center", "gap": "18px", "maxWidth": "800px", "padding": "72px 48px 96px"},
		mobile={"padding": "40px 18px 56px"},
	)


def about_blocks(refs):
	stat = lambda value, stat_label: block(
		"div",
		styles={
			"borderTopColor": refs["line"],
			"borderTopStyle": "solid",
			"borderTopWidth": "1px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "6px",
			"paddingTop": "16px",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text=value,
				styles={
					"fontFamily": HEAD,
					"fontSize": "30px",
					"fontWeight": "700",
					"height": "fit-content",
					"letterSpacing": "-0.02em",
					"width": "fit-content",
				},
			),
			label(refs, stat_label),
		],
	)
	content = content_section(
		refs,
		[
			label(refs, "About"),
			display_heading(refs, "Fewer, better things", size="56px", mobile_size="32px"),
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
					"display": "grid",
					"gap": "24px",
					"gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
					"marginTop": "24px",
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
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def contact_blocks(refs):
	detail = lambda detail_label, value: block(
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
			label(refs, detail_label),
			block(
				"p",
				text=value,
				styles={"fontSize": "14px", "fontWeight": "500", "height": "fit-content", "width": "fit-content"},
			),
		],
	)
	content = content_section(
		refs,
		[
			label(refs, "Contact"),
			display_heading(refs, "Get in touch", size="56px", mobile_size="32px"),
			paragraph(refs, "Questions about an order, a product or anything else. We reply within a day."),
			block(
				"div",
				styles={
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"marginTop": "16px",
					"width": "100%",
				},
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
					**accent_button_styles(refs),
					"height": "fit-content",
					"marginTop": "24px",
					"textDecoration": "none",
				},
			),
		],
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
				styles={
					"fontFamily": HEAD,
					"fontSize": "15px",
					"fontWeight": "600",
					"height": "fit-content",
					"letterSpacing": "0.04em",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
			),
			paragraph(refs, answer, size="14px"),
		],
	)
	content = content_section(
		refs,
		[
			label(refs, "FAQ"),
			display_heading(refs, "Questions, answered", size="56px", mobile_size="32px"),
			block(
				"div",
				styles={
					"borderTopColor": refs["line"],
					"borderTopStyle": "solid",
					"borderTopWidth": "1px",
					"display": "flex",
					"flexDirection": "column",
					"marginTop": "16px",
					"width": "100%",
				},
				children=[entry(question, answer) for question, answer in FAQS],
			),
		],
	)
	return shell(refs, [nav(refs), content, footer(refs)])
