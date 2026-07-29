"""Sorbet: fresh playful light storefront. Floating pill nav, rounded cards, coral accents."""

from shop.theme_generators.blocks import (
	block,
	dv,
	repeater,
	root,
	upsert_client_script,
	upsert_page,
	upsert_variables,
)

GROUP = "sorbet"
HEAD = "Sora"
BODY = "Karla"

PALETTE = {
	"paper": ("#FFFDF8", "#1C1522"),
	"ink": ("#33223B", "#F3EBF8"),
	"muted": ("#8A7A91", "#A995B3"),
	"surface": ("#F4EDFF", "#2B2136"),
	"accent": ("#FF5D5D", "#FF7A7A"),
}

CARD_SHADOW = "0 14px 34px rgba(51, 34, 59, 0.10)"


def data_script(fn: str, expose: tuple = ()) -> str:
	lines = [f'result = frappe.call("shop.storefront.page_data.{fn}")', "data.update(result)"]
	if expose:
		exposed = ", ".join(f'"{key}": result.get("{key}")' for key in expose)
		lines.append(f"data.page_data = {{{exposed}}}")
	return "\n".join(lines)


def generate():
	refs = upsert_variables(GROUP, PALETTE)
	styles = upsert_client_script("sorbet-styles", "CSS", theme_css(refs))
	pages = [
		("sorbet-home", "Home", "home", home_blocks(refs), "home", (), False),
		("sorbet-products", "Products", "products", products_blocks(refs), "listing", (), False),
		("sorbet-product", "Product", "product/:slug", product_blocks(refs), "product_page", ("product",), False),
		("sorbet-collection", "Collection", "collection/:slug", collection_blocks(refs), "collection_page", (), False),
		("sorbet-cart", "Cart", "cart", cart_blocks(refs), "cart_page", ("cart",), False),
		("sorbet-checkout", "Checkout", "checkout", checkout_blocks(refs), "checkout_page", ("cart",), False),
		(
			"sorbet-order-confirmation",
			"Order Confirmed",
			"order-confirmation/:order_id",
			confirmation_blocks(refs),
			"order_confirmation",
			(),
			False,
		),
		("sorbet-account-orders", "Your Orders", "account/orders", account_blocks(refs), "account_orders", (), True),
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
button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
a, button {{ transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease; }}
a:hover {{ opacity: 0.75; }}
:focus-visible {{ outline: 2px solid {refs["accent"]}; outline-offset: 2px; }}
[data-shop="variant-option"][data-selected="true"] {{
	background: {refs["accent"]};
	border-color: {refs["accent"]};
	color: #FFFFFF;
}}
[data-shop="cart-count"][data-empty="true"] {{ display: none; }}
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
		"maxWidth": "1200px",
		"padding": "48px 32px",
		"width": "100%",
	}
	base.update(styles or {})
	return block("div", styles=base, mobile=mobile or {"padding": "28px 16px"}, children=children)


def heading(refs, text, size="40px", mobile_size="28px", element="h1", centered=False):
	styles = {
		"color": refs["ink"],
		"fontFamily": HEAD,
		"fontSize": size,
		"fontWeight": "700",
		"height": "fit-content",
		"lineHeight": "1.15",
		"width": "fit-content",
	}
	if centered:
		styles["textAlign"] = "center"
	return block(element, text=text, styles=styles, mobile={"fontSize": mobile_size})


def pill_button_styles(refs):
	return {
		"backgroundColor": refs["accent"],
		"borderRadius": "999px",
		"borderWidth": "0px",
		"boxShadow": "0 10px 24px rgba(255, 93, 93, 0.35)",
		"color": "#FFFFFF",
		"fontFamily": HEAD,
		"fontSize": "15px",
		"fontWeight": "700",
		"padding": "15px 32px",
		"width": "fit-content",
	}


def kicker(refs, text):
	return block(
		"p",
		text=text,
		styles={
			"backgroundColor": refs["surface"],
			"borderRadius": "999px",
			"color": refs["accent"],
			"fontSize": "13px",
			"fontWeight": "700",
			"height": "fit-content",
			"letterSpacing": "0.04em",
			"padding": "7px 16px",
			"width": "fit-content",
		},
	)


def nav(refs):
	link_style = {
		"color": refs["ink"],
		"fontSize": "14px",
		"fontWeight": "700",
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
			"fontWeight": "800",
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
			"borderRadius": "999px",
			"color": "#FFFFFF",
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
			**{k: v for k, v in link_style.items() if k != "width"},
			"width": "fit-content",
		},
		children=[
			block(
				"span",
				text="Cart",
				styles={"fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
			),
			badge,
		],
	)
	return block(
		"div",
		name="Nav",
		styles={
			"display": "flex",
			"flexDirection": "column",
			"flexShrink": 0,
			"maxWidth": "1040px",
			"padding": "20px 32px 0",
			"position": "sticky",
			"top": "12px",
			"width": "100%",
			"zIndex": "50",
		},
		mobile={"padding": "12px 16px 0"},
		children=[
			block(
				"div",
				styles={
					"alignItems": "center",
					"backgroundColor": refs["surface"],
					"borderRadius": "999px",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"padding": "13px 28px",
					"width": "100%",
				},
				mobile={"padding": "11px 18px"},
				children=[
					brand,
					block(
						"div",
						styles={"alignItems": "center", "display": "flex", "flexDirection": "row", "gap": "24px"},
						mobile={"gap": "14px"},
						children=[
							block("a", text="Shop all", attrs={"href": "/products"}, styles=dict(link_style)),
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
			"display": "flex",
			"flexDirection": "column",
			"flexShrink": 0,
			"marginTop": "auto",
			"padding": "40px 32px",
			"width": "100%",
		},
		children=[
			block(
				"p",
				text="Shop",
				styles={
					"backgroundColor": refs["surface"],
					"borderRadius": "999px",
					"color": refs["muted"],
					"fontSize": "13px",
					"fontWeight": "700",
					"height": "fit-content",
					"padding": "8px 20px",
					"width": "fit-content",
				},
				dynamicValues=[dv("store.name", "innerHTML")],
			)
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
			"borderRadius": "14px",
			"color": "#B3261E",
			"display": "none",
			"fontSize": "14px",
			"marginTop": "16px",
			"padding": "12px 18px",
			"width": "100%",
		},
	)


def product_card(refs, source="products"):
	return block(
		"a",
		name=f"Card · {source}",
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
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["surface"],
					"borderRadius": "24px",
					"boxShadow": CARD_SHADOW,
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
					"fontFamily": HEAD,
					"fontSize": "15px",
					"fontWeight": "700",
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
					"backgroundColor": refs["surface"],
					"borderRadius": "999px",
					"color": refs["accent"],
					"fontSize": "13px",
					"fontWeight": "700",
					"height": "fit-content",
					"padding": "5px 14px",
					"width": "fit-content",
				},
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
			"gap": "36px 24px",
			"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "24px 14px"},
		tablet={"gridTemplateColumns": "repeat(3, minmax(0, 1fr))"},
		name=f"Grid · {source}",
	)


def home_blocks(refs):
	hero = section(
		[
			block(
				"div",
				name="Hero Panel",
				styles={
					"alignItems": "center",
					"background": f"linear-gradient(160deg, {refs['surface']} 0%, {refs['paper']} 78%)",
					"borderRadius": "36px",
					"display": "flex",
					"flexDirection": "column",
					"gap": "22px",
					"padding": "88px 48px",
					"textAlign": "center",
					"width": "100%",
				},
				mobile={"borderRadius": "24px", "padding": "48px 20px"},
				children=[
					kicker(refs, "Fresh drop · picked with love"),
					block(
						"h1",
						text="Little things that make your day sweeter",
						styles={
							"color": refs["ink"],
							"fontFamily": HEAD,
							"fontSize": "54px",
							"fontWeight": "800",
							"height": "fit-content",
							"lineHeight": "1.1",
							"maxWidth": "720px",
							"textAlign": "center",
							"width": "100%",
						},
						mobile={"fontSize": "32px"},
					),
					block(
						"p",
						text="Cheerful everyday goods, small-batch and big on personality.",
						styles={
							"color": refs["muted"],
							"fontSize": "17px",
							"height": "fit-content",
							"lineHeight": "1.5",
							"maxWidth": "460px",
							"textAlign": "center",
							"width": "100%",
						},
					),
					block(
						"a",
						text="Shop all products",
						attrs={"href": "/products"},
						styles={**pill_button_styles(refs), "height": "fit-content", "marginTop": "8px", "textDecoration": "none"},
					),
				],
			)
		],
		styles={"padding": "36px 32px 24px"},
		mobile={"padding": "20px 16px 12px"},
	)
	collection_tile = block(
		"a",
		name="Tile · collections",
		attrs={"href": "#"},
		styles={
			"alignItems": "center",
			"backgroundColor": refs["surface"],
			"borderRadius": "24px",
			"color": refs["ink"],
			"display": "flex",
			"flexDirection": "column",
			"gap": "8px",
			"padding": "36px 24px",
			"textAlign": "center",
			"textDecoration": "none",
			"width": "100%",
		},
		dynamicValues=[dv("route", "href", "attribute")],
		children=[
			block(
				"h3",
				text="Collection",
				styles={
					"fontFamily": HEAD,
					"fontSize": "18px",
					"fontWeight": "700",
					"height": "fit-content",
					"textAlign": "center",
					"width": "fit-content",
				},
				dynamicValues=[dv("title", "innerHTML")],
			),
			block(
				"p",
				text="",
				visibilityCondition={"key": "description", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "13px",
					"height": "fit-content",
					"lineHeight": "1.5",
					"textAlign": "center",
					"width": "100%",
				},
				dynamicValues=[dv("description", "innerHTML")],
			),
		],
	)
	collections = section(
		[
			heading(refs, "Shop by mood", size="28px", mobile_size="22px", element="h2", centered=True),
			repeater(
				"collections",
				collection_tile,
				{
					"display": "grid",
					"gap": "20px",
					"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
					"width": "100%",
				},
				mobile={"gridTemplateColumns": "repeat(1, minmax(0, 1fr))"},
				tablet={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
				name="Grid · collections",
			),
		],
		styles={"alignItems": "center", "gap": "28px"},
	)
	featured = section(
		[
			heading(refs, "Fan favourites", size="28px", mobile_size="22px", element="h2", centered=True),
			product_grid(refs, "featured_products", "featured"),
		],
		styles={"alignItems": "center", "gap": "28px", "paddingBottom": "80px"},
	)
	return shell(refs, [nav(refs), hero, collections, featured, footer(refs)])


def search_form(refs):
	return block(
		"form",
		name="Search",
		attrs={"data-shop": "search-form", "action": "/products"},
		styles={
			"backgroundColor": "#FFFFFF",
			"borderRadius": "999px",
			"boxShadow": CARD_SHADOW,
			"display": "flex",
			"flexDirection": "row",
			"gap": "6px",
			"padding": "6px",
			"width": "fit-content",
		},
		mobile={"width": "100%"},
		children=[
			block(
				"input",
				attrs={"type": "search", "name": "search", "placeholder": "Search products"},
				styles={
					"backgroundColor": "transparent",
					"borderRadius": "999px",
					"borderWidth": "0px",
					"color": refs["ink"],
					"fontSize": "14px",
					"padding": "8px 16px",
					"width": "230px",
				},
				mobile={"width": "100%"},
			),
			block(
				"button",
				text="Search",
				attrs={"type": "submit"},
				styles={**pill_button_styles(refs), "boxShadow": "none", "fontSize": "14px", "padding": "9px 20px"},
			),
		],
	)


def products_blocks(refs):
	chip = block(
		"a",
		name="Chip",
		text="Collection",
		attrs={"href": "#"},
		styles={
			"backgroundColor": refs["surface"],
			"borderRadius": "999px",
			"color": refs["ink"],
			"fontSize": "13px",
			"fontWeight": "700",
			"height": "fit-content",
			"padding": "8px 18px",
			"textDecoration": "none",
			"width": "fit-content",
		},
		dynamicValues=[dv("route", "href", "attribute"), dv("title", "innerHTML")],
	)
	header = section(
		[
			kicker(refs, "The whole shelf"),
			heading(refs, "All products", size="44px", mobile_size="30px", centered=True),
			search_form(refs),
			repeater(
				"collections",
				chip,
				{
					"display": "flex",
					"flexDirection": "row",
					"flexWrap": "wrap",
					"gap": "10px",
					"justifyContent": "center",
					"width": "fit-content",
				},
				name="Chips · collections",
			),
		],
		styles={"alignItems": "center", "gap": "18px", "padding": "56px 32px 12px"},
		mobile={"padding": "32px 16px 8px"},
	)
	grid = section([product_grid(refs, "products", "products")], styles={"paddingBottom": "80px", "paddingTop": "32px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


def option_button(refs):
	return block(
		"button",
		name="Option",
		text="Value",
		attrs={"type": "button", "data-shop": "variant-option"},
		styles={
			"backgroundColor": "#FFFFFF",
			"borderColor": refs["surface"],
			"borderRadius": "999px",
			"borderStyle": "solid",
			"borderWidth": "2px",
			"color": refs["ink"],
			"fontSize": "14px",
			"fontWeight": "700",
			"padding": "9px 20px",
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
		styles={"alignItems": "center", "display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
		children=[
			block(
				"p",
				text="Attribute",
				styles={
					"color": refs["muted"],
					"fontSize": "12px",
					"fontWeight": "700",
					"height": "fit-content",
					"letterSpacing": "0.08em",
					"textAlign": "center",
					"textTransform": "uppercase",
					"width": "fit-content",
				},
				dynamicValues=[dv("attribute", "innerHTML")],
			),
			repeater(
				"values",
				option_button(refs),
				{
					"display": "flex",
					"flexDirection": "row",
					"flexWrap": "wrap",
					"gap": "8px",
					"justifyContent": "center",
					"width": "fit-content",
				},
				name="Options",
			),
		],
	)
	content = section(
		[
			block(
				"img",
				name="Main Image",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "eager"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": refs["surface"],
					"borderRadius": "32px",
					"boxShadow": CARD_SHADOW,
					"display": "block",
					"objectFit": "cover",
					"width": "100%",
				},
				mobile={"borderRadius": "20px"},
				dynamicValues=[
					dv("product.image", "src", "attribute"),
					dv("product.product_name", "alt", "attribute"),
				],
			),
			block(
				"h1",
				text="Product",
				styles={
					"color": refs["ink"],
					"fontFamily": HEAD,
					"fontSize": "36px",
					"fontWeight": "800",
					"height": "fit-content",
					"lineHeight": "1.15",
					"marginTop": "16px",
					"textAlign": "center",
					"width": "100%",
				},
				mobile={"fontSize": "26px"},
				dynamicValues=[dv("product.product_name", "innerHTML")],
			),
			block(
				"p",
				text="",
				attrs={"data-shop": "pdp-price"},
				styles={
					"backgroundColor": refs["surface"],
					"borderRadius": "999px",
					"color": refs["accent"],
					"fontSize": "17px",
					"fontWeight": "700",
					"height": "fit-content",
					"padding": "8px 22px",
					"width": "fit-content",
				},
				dynamicValues=[dv("product.formatted_price", "innerHTML")],
			),
			block(
				"p",
				text="",
				visibilityCondition={"key": "product.short_description", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "16px",
					"height": "fit-content",
					"lineHeight": "1.6",
					"maxWidth": "540px",
					"textAlign": "center",
					"width": "100%",
				},
				dynamicValues=[dv("product.short_description", "innerHTML")],
			),
			repeater(
				"product.attribute_options",
				attribute_group,
				{"display": "flex", "flexDirection": "column", "gap": "20px", "marginTop": "8px", "width": "100%"},
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
				styles={**pill_button_styles(refs), "marginTop": "10px", "padding": "16px 44px"},
				mobile={"width": "100%"},
				dynamicValues=[dv("product.buy_item_code", "data-item-code", "attribute")],
			),
			error_banner(refs),
			block(
				"p",
				text="",
				visibilityCondition={"key": "product.description_text", "comesFrom": "dataScript"},
				styles={
					"backgroundColor": refs["surface"],
					"borderRadius": "20px",
					"color": refs["muted"],
					"fontSize": "14px",
					"height": "fit-content",
					"lineHeight": "1.7",
					"marginTop": "18px",
					"padding": "22px 26px",
					"width": "100%",
				},
				dynamicValues=[dv("product.description_text", "innerHTML")],
			),
		],
		styles={"alignItems": "center", "gap": "14px", "maxWidth": "720px", "padding": "48px 32px 80px"},
		mobile={"padding": "24px 16px 48px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def collection_blocks(refs):
	header = section(
		[
			kicker(refs, "Collection"),
			heading(refs, "Collection", size="44px", mobile_size="30px", centered=True),
			block(
				"p",
				text="",
				visibilityCondition={"key": "collection.description", "comesFrom": "dataScript"},
				styles={
					"color": refs["muted"],
					"fontSize": "16px",
					"height": "fit-content",
					"lineHeight": "1.6",
					"maxWidth": "520px",
					"textAlign": "center",
					"width": "100%",
				},
				dynamicValues=[dv("collection.description", "innerHTML")],
			),
		],
		styles={"alignItems": "center", "gap": "16px", "padding": "56px 32px 16px"},
		mobile={"padding": "32px 16px 8px"},
	)
	header["children"][1]["dynamicValues"] = [dv("collection.title", "innerHTML")]
	grid = section([product_grid(refs, "products", "collection")], styles={"paddingBottom": "80px", "paddingTop": "32px"})
	return shell(refs, [nav(refs), header, grid, footer(refs)])


def cart_blocks(refs):
	qty_button = {
		"alignItems": "center",
		"backgroundColor": "#FFFFFF",
		"borderRadius": "999px",
		"borderWidth": "0px",
		"boxShadow": "0 4px 12px rgba(51, 34, 59, 0.12)",
		"color": refs["ink"],
		"display": "flex",
		"fontSize": "15px",
		"fontWeight": "700",
		"height": "32px",
		"justifyContent": "center",
		"width": "32px",
	}
	line_item = block(
		"div",
		name="Line Item",
		styles={
			"alignItems": "center",
			"backgroundColor": refs["surface"],
			"borderRadius": "20px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "18px",
			"padding": "16px 22px 16px 16px",
			"width": "100%",
		},
		mobile={"flexWrap": "wrap", "gap": "12px", "padding": "14px"},
		children=[
			block(
				"img",
				attrs={"src": "/assets/builder/images/fallback.png", "alt": "", "loading": "lazy"},
				styles={
					"aspectRatio": "1 / 1",
					"backgroundColor": "#FFFFFF",
					"borderRadius": "14px",
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
						styles={
							"fontFamily": HEAD,
							"fontSize": "15px",
							"fontWeight": "700",
							"height": "fit-content",
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
						styles={"fontSize": "14px", "fontWeight": "700", "minWidth": "22px", "textAlign": "center", "width": "fit-content"},
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
					"fontSize": "15px",
					"fontWeight": "700",
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
			kicker(refs, "Your basket"),
			heading(refs, "Cart", centered=True),
			error_banner(refs),
			block(
				"p",
				text="Your cart is empty.",
				visibilityCondition={"key": "cart.is_empty", "comesFrom": "dataScript"},
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "marginTop": "12px", "width": "fit-content"},
			),
			repeater(
				"cart.items",
				line_item,
				{"display": "flex", "flexDirection": "column", "gap": "14px", "marginTop": "20px", "width": "100%"},
				name="Line Items",
			),
			block(
				"div",
				name="Summary",
				visibilityCondition={"key": "cart.item_count", "comesFrom": "dataScript"},
				styles={
					"alignItems": "center",
					"backgroundColor": "#FFFFFF",
					"borderRadius": "20px",
					"boxShadow": CARD_SHADOW,
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"marginTop": "20px",
					"padding": "18px 24px",
					"width": "100%",
				},
				children=[
					block(
						"p",
						text="Total",
						styles={"fontSize": "16px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
					),
					block(
						"p",
						text="",
						styles={
							"fontFamily": HEAD,
							"fontSize": "24px",
							"fontWeight": "800",
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
					**pill_button_styles(refs),
					"height": "fit-content",
					"marginTop": "20px",
					"padding": "16px 44px",
					"textAlign": "center",
					"textDecoration": "none",
				},
				mobile={"width": "100%"},
			),
		],
		styles={"alignItems": "center", "gap": "10px", "maxWidth": "820px", "padding": "48px 32px 80px"},
		mobile={"padding": "28px 16px 48px"},
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
			"backgroundColor": "#FFFFFF",
			"borderColor": refs["surface"],
			"borderRadius": "14px",
			"borderStyle": "solid",
			"borderWidth": "2px",
			"color": refs["ink"],
			"fontSize": "14px",
			"gridColumn": "span 1" if half else "span 2",
			"padding": "12px 16px",
			"width": "100%",
		},
	)


def checkout_blocks(refs):
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
				styles={"color": refs["ink"], "fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
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
			"backgroundColor": refs["surface"],
			"borderRadius": "24px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"padding": "26px 28px",
			"width": "100%",
		},
		children=[
			block(
				"h2",
				text="Order summary",
				styles={"fontFamily": HEAD, "fontSize": "18px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
			),
			repeater(
				"cart.items",
				summary_row,
				{"display": "flex", "flexDirection": "column", "gap": "10px", "width": "100%"},
				name="Summary Items",
			),
			block(
				"div",
				styles={
					"alignItems": "center",
					"backgroundColor": "#FFFFFF",
					"borderRadius": "14px",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"marginTop": "6px",
					"padding": "12px 18px",
					"width": "100%",
				},
				children=[
					block(
						"p",
						text="Total",
						styles={"fontSize": "15px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
					),
					block(
						"p",
						text="",
						styles={
							"fontFamily": HEAD,
							"fontSize": "19px",
							"fontWeight": "800",
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
			"backgroundColor": "#FFFFFF",
			"borderColor": refs["surface"],
			"borderRadius": "14px",
			"borderStyle": "solid",
			"borderWidth": "2px",
			"display": "flex",
			"flexDirection": "row",
			"gap": "12px",
			"padding": "13px 16px",
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
				styles={"fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
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
				{"display": "flex", "flexDirection": "column", "gap": "10px", "gridColumn": "span 2", "width": "100%"},
				name="Payment Methods",
			),
			block(
				"button",
				text="Place order",
				attrs={"type": "submit"},
				styles={**pill_button_styles(refs), "gridColumn": "span 2", "marginTop": "8px", "padding": "16px 32px", "width": "100%"},
			),
		],
	)
	content = section(
		[
			kicker(refs, "Nearly there"),
			heading(refs, "Checkout", centered=True),
			error_banner(refs),
			summary,
			form,
		],
		styles={"alignItems": "center", "gap": "20px", "maxWidth": "760px", "padding": "48px 32px 80px"},
		mobile={"padding": "28px 16px 48px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def confirmation_blocks(refs):
	item_row = block(
		"div",
		name="Order Item",
		styles={
			"backgroundColor": "#FFFFFF",
			"borderRadius": "14px",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "12px 18px",
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
						styles={"fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
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
				styles={"fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_amount", "innerHTML")],
			),
		],
	)
	card = block(
		"div",
		name="Confirmation Card",
		styles={
			"alignItems": "center",
			"backgroundColor": refs["surface"],
			"borderRadius": "32px",
			"display": "flex",
			"flexDirection": "column",
			"gap": "12px",
			"padding": "48px 40px",
			"width": "100%",
		},
		mobile={"borderRadius": "20px", "padding": "28px 18px"},
		children=[
			block(
				"p",
				text="✓",
				styles={
					"alignItems": "center",
					"backgroundColor": refs["accent"],
					"borderRadius": "999px",
					"boxShadow": "0 10px 24px rgba(255, 93, 93, 0.35)",
					"color": "#FFFFFF",
					"display": "flex",
					"fontSize": "22px",
					"height": "52px",
					"justifyContent": "center",
					"width": "52px",
				},
			),
			heading(refs, "Yay, order placed!", size="34px", mobile_size="26px", centered=True),
			block(
				"p",
				text="Order",
				styles={"color": refs["muted"], "fontSize": "15px", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("order.name", "innerHTML")],
			),
			repeater(
				"order.items",
				item_row,
				{"display": "flex", "flexDirection": "column", "gap": "10px", "marginTop": "14px", "width": "100%"},
				name="Order Items",
			),
			block(
				"div",
				styles={
					"alignItems": "center",
					"display": "flex",
					"flexDirection": "row",
					"justifyContent": "space-between",
					"marginTop": "8px",
					"padding": "0 18px",
					"width": "100%",
				},
				children=[
					block(
						"p",
						text="Grand total",
						styles={"fontSize": "15px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
					),
					block(
						"p",
						text="",
						styles={
							"fontFamily": HEAD,
							"fontSize": "22px",
							"fontWeight": "800",
							"height": "fit-content",
							"width": "fit-content",
						},
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
					"fontWeight": "700",
					"height": "fit-content",
					"marginTop": "14px",
					"textDecoration": "none",
					"width": "fit-content",
				},
			),
		],
	)
	content = section(
		[card],
		styles={"maxWidth": "620px", "padding": "64px 32px 96px"},
		mobile={"padding": "28px 16px 56px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])


def account_blocks(refs):
	order_row = block(
		"div",
		name="Order Row",
		styles={
			"alignItems": "center",
			"backgroundColor": refs["surface"],
			"borderRadius": "18px",
			"display": "flex",
			"flexDirection": "row",
			"justifyContent": "space-between",
			"padding": "16px 22px",
			"width": "100%",
		},
		mobile={"flexWrap": "wrap", "gap": "8px"},
		children=[
			block(
				"p",
				text="Order",
				styles={"fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
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
					"backgroundColor": "#FFFFFF",
					"borderRadius": "999px",
					"color": refs["accent"],
					"fontSize": "12px",
					"fontWeight": "700",
					"height": "fit-content",
					"padding": "5px 14px",
					"width": "fit-content",
				},
				dynamicValues=[dv("status", "innerHTML")],
			),
			block(
				"p",
				text="",
				styles={"fontSize": "14px", "fontWeight": "700", "height": "fit-content", "width": "fit-content"},
				dynamicValues=[dv("formatted_total", "innerHTML")],
			),
		],
	)
	content = section(
		[
			kicker(refs, "Order history"),
			heading(refs, "Your orders", centered=True),
			repeater(
				"orders",
				order_row,
				{"display": "flex", "flexDirection": "column", "gap": "12px", "marginTop": "16px", "width": "100%"},
				name="Orders",
			),
		],
		styles={"alignItems": "center", "gap": "12px", "maxWidth": "820px", "padding": "48px 32px 80px"},
		mobile={"padding": "28px 16px 48px"},
	)
	return shell(refs, [nav(refs), content, footer(refs)])
