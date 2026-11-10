"""Store pieces both themes share: the store's own CSS (checkout, orders, accounts, quotes, terms)
and the form blocks the store's endpoints read."""

from shop.theme_generators.blocks import block, dv, repeater


def store_css(refs, radius: str = "2px"):
	"""Styles for what the store's script and server render: checkout lines and options, the
	order's payment box and totals, account rows and forms, quote and terms pages."""
	ink, muted, line, card, paper, ok = (
		refs["ink"],
		refs["muted"],
		refs["line"],
		refs["card"],
		refs["paper"],
		refs["success"],
	)
	warn = refs.get("badge") or refs.get("accent") or refs["ink"]
	return f"""
[hidden] {{ display: none !important; }}
.product-description p, .product-description ul, .product-description ol, .product-description table {{ margin:0 0 12px; }}
.product-description ul, .product-description ol {{ padding-left:20px; }}
.product-description li {{ margin:4px 0; }}
.product-description a {{ color:{ink}; text-decoration:underline; }}
.product-description table {{ border-collapse:collapse; width:100%; }}
.product-description td, .product-description th {{ border-bottom:1px solid {line}; padding:6px 8px; text-align:left; }}
@media (max-width: 640px) {{ input, select, textarea {{ font-size:16px !important; }} }}
.visually-hidden {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }}
.store-currency:empty {{ display:none; }}
.shop-select-list {{ position:absolute; z-index:1000; box-sizing:border-box; max-width:min(420px, calc(100vw - 16px)); padding:4px; background:{paper}; color:{ink}; border:1px solid {line}; border-radius:min({radius}, 10px); box-shadow:0 14px 34px rgba(0,0,0,.12); font-size:14px; }}
.shop-select-list [role="listbox"] {{ max-height:300px; overflow-y:auto; outline:none; }}
.shop-select-list [role="option"] {{ display:flex; align-items:center; justify-content:space-between; gap:16px; padding:8px 10px; border-radius:min({radius}, 6px); cursor:pointer; white-space:nowrap; }}
.shop-select-list [role="option"][data-active="true"] {{ background:{card}; }}
.shop-select-list [role="option"][aria-selected="true"] {{ font-weight:600; }}
.shop-select-list [role="option"][aria-selected="true"]::after {{ content:""; width:5px; height:9px; border-right:2px solid currentColor; border-bottom:2px solid currentColor; transform:rotate(45deg) translate(-2px, -2px); flex-shrink:0; }}
.shop-select-list [role="option"][aria-disabled="true"] {{ color:{muted}; cursor:default; }}
.shop-select-search {{ display:block; width:100%; box-sizing:border-box; margin:0 0 4px; padding:8px 10px; font:inherit; color:{ink}; background:{paper}; border:1px solid {line}; border-radius:min({radius}, 6px); outline:none; }}
.shop-select-search:focus {{ border-color:{ink}; }}
.shop-select-empty {{ margin:0; padding:8px 10px; color:{muted}; }}
.shop-search-list [role="option"] {{ text-decoration:none; color:{ink}; white-space:normal; }}
.shop-search-list img {{ width:36px; height:36px; object-fit:contain; background:{card}; border-radius:min({radius}, 6px); flex-shrink:0; }}
.shop-search-list [role="option"] span {{ flex:1; }}
.shop-search-list small {{ color:{muted}; font-size:12px; white-space:nowrap; }}
.shop-search-list .shop-search-all {{ justify-content:center; font-weight:600; border-top:1px solid {line}; border-radius:0; margin-top:4px; }}
.stock-alert {{ display:flex; flex-direction:column; gap:8px; width:100%; padding:12px 14px; border:1px solid {line}; border-radius:min({radius}, 10px); }}
.stock-alert-intro, .stock-alert-done {{ margin:0; font-size:13px; color:{ink}; }}
.stock-alert-row {{ display:flex; gap:8px; }}
.stock-alert-row input {{ flex:1; min-width:0; font:inherit; font-size:14px; padding:8px 10px; color:{ink}; background:{paper}; border:1px solid {line}; border-radius:min({radius}, 6px); }}
.stock-alert-row button {{ font:inherit; font-size:14px; font-weight:600; padding:8px 14px; color:{paper}; background:{ink}; border:0; border-radius:min({radius}, 6px); cursor:pointer; white-space:nowrap; }}
.shop-address-list [role="option"] {{ flex-direction:column; align-items:flex-start; gap:2px; white-space:normal; }}
.shop-address-list [role="option"][aria-selected="true"] {{ font-weight:inherit; }}
.shop-address-list [role="option"][aria-selected="true"]::after {{ content:none; }}
.shop-address-list small {{ color:{muted}; font-size:12px; }}
.shop-address-credit {{ margin:4px 10px 2px; font-size:11px; color:{muted}; }}
[data-shop="stock-status"] {{ color:{ok}; }}
[data-shop="stock-status"] .stock-dot {{ background:{ok}; }}
[data-shop="stock-status"][data-stock-state="out"], [data-shop="stock-status"][data-stock-state="unavailable"] {{ color:{muted}; }}
[data-shop="stock-status"][data-stock-state="out"] .stock-dot, [data-shop="stock-status"][data-stock-state="unavailable"] .stock-dot {{ background:{muted}; }}
.stock-locations {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:4px; font-size:13px; }}
.stock-locations li {{ display:flex; justify-content:space-between; gap:12px; color:{ink}; }}
.stock-locations li span:last-child {{ color:{ok}; }}
.stock-locations li[data-stock-state="out"] span:last-child {{ color:{muted}; }}
.buying-for {{ display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin:0 0 12px; font-size:14px; color:{ink}; }}
.buying-for select {{ font:inherit; padding:6px 10px; border:1px solid {line}; border-radius:4px; background:transparent; color:{ink}; }}
.shipping-note {{ margin:0; font-size:13px; color:{muted}; }}
.currency-picker {{ position:relative; display:inline-flex; align-items:center; }}
.currency-picker select {{ appearance:none; -webkit-appearance:none; font:inherit; letter-spacing:inherit; text-transform:inherit; color:inherit; background:transparent; border:0; padding:2px 16px 2px 0; cursor:pointer; }}
.currency-picker::after {{ content:""; position:absolute; right:2px; top:50%; width:5px; height:5px; border-right:1.5px solid currentColor; border-bottom:1.5px solid currentColor; transform:translateY(-70%) rotate(45deg); pointer-events:none; }}
.currency-picker select:focus-visible {{ outline:2px solid currentColor; outline-offset:3px; border-radius:2px; }}
.checkout-option {{ display:flex; align-items:center; gap:10px; padding:12px 14px; border:1px solid {line}; border-radius:{radius}; cursor:pointer; width:100%; font-size:13px; }}
.checkout-option input {{ accent-color:{ink}; width:15px; height:15px; flex-shrink:0; }}
.checkout-option-label {{ flex-grow:1; }}
.checkout-option-label small {{ color:{muted}; margin-left:6px; }}
.checkout-option-price {{ font-weight:600; white-space:nowrap; }}
small.checkout-option-price {{ font-weight:400; color:{muted}; font-size:12px; }}
.checkout-option:has(input:checked) {{ border-color:{ink}; box-shadow:0 0 0 1px {ink}; }}
.checkout-hint {{ color:{muted}; font-size:12px; line-height:1.5; margin:0; }}
.checkout-hint a, .account-note a, .checkout-check a {{ color:{ink}; text-decoration:underline; }}
.checkout-warning {{ border:1px solid {warn}; border-radius:{radius}; padding:12px 14px; font-size:13px; line-height:1.5; }}
.checkout-warning p {{ margin:0; }}
.checkout-error {{ border:1px solid {warn}; color:{warn}; border-radius:{radius}; padding:12px 14px; font-size:13px; }}
.checkout-check {{ display:flex; gap:10px; align-items:flex-start; font-size:13px; line-height:1.5; cursor:pointer; }}
.checkout-check input {{ margin-top:3px; accent-color:{ink}; width:15px; height:15px; flex-shrink:0; }}
.terms-note::before {{ content:", "; }}
.checkout-totals[aria-busy="true"] {{ opacity:.55; }}
.checkout-line, .order-line {{ display:flex; justify-content:space-between; gap:12px; font-size:13px; padding:2px 0; }}
.checkout-total, .order-line.total {{ border-top:1px solid {line}; margin-top:6px; padding-top:10px; font-size:15px; font-weight:700; }}
.checkout-note, .order-note {{ color:{muted}; font-size:12px; margin:2px 0 0; }}
.order-item {{ display:grid; grid-template-columns:1fr auto auto; gap:14px; padding:10px 0; border-bottom:1px solid {line}; font-size:13px; }}
.order-qty {{ color:{muted}; }}
.order-qty::before {{ content:"× "; }}
.order-amount {{ font-weight:600; }}
.order-totals {{ display:flex; flex-direction:column; gap:6px; }}
.order-payment {{ border:1px solid {line}; border-radius:{radius}; padding:16px 18px; font-size:13px; line-height:1.6; }}
.order-payment h3 {{ margin:0 0 8px; font-size:15px; }}
.order-payment p {{ margin:0 0 8px; }}
.order-payment.bank, .order-payment.card {{ border-color:{warn}; }}
.order-payment.card {{ display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }}
.order-payment.paid {{ border-color:{ok}; }}
.order-payment.cancelled {{ background:{card}; }}
.bank-details {{ background:{card}; border-radius:{radius}; padding:10px 12px; margin:8px 0; font-family: ui-monospace, Menlo, monospace; font-size:13px; }}
.order-pay-button {{ display:inline-block; background:{ink}; color:{paper}; border-radius:{radius}; padding:10px 18px; font-weight:600; text-decoration:none; }}
.account-form {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px; width:100%; }}
.account-form textarea, .account-form select {{ grid-column: span 2; }}
.account-form select[name="country"], .account-form select[name="industry"] {{ grid-column: span 1; }}
.form-submit, .quote-button {{ grid-column: span 2; cursor:pointer; }}
.quote-button {{ background:{paper}; color:{ink}; border:1px solid {ink}; border-radius:{radius}; margin-top:8px; padding:12px 20px; font-size:13px; font-weight:600; }}
.quote-request summary {{ cursor:pointer; font-size:13px; text-decoration:underline; }}
.quote-request textarea {{ margin-top:8px; }}
.form-done {{ border:1px solid {ok}; border-radius:{radius}; padding:14px 16px; font-size:13px; width:100%; }}
.account-note {{ background:{card}; border-radius:{radius}; padding:14px 16px; font-size:13px; margin-bottom:12px; }}
.account-details h2 {{ font-size:18px; font-weight:600; margin:24px 0 8px; }}
.account-actions {{ display:flex; gap:12px; align-items:baseline; flex-wrap:wrap; margin:6px 0; font-size:13px; color:{muted}; }}
.account-actions a {{ color:{ink}; font-weight:600; }}
.account-table {{ display:flex; flex-direction:column; width:100%; }}
.account-row {{ display:grid; grid-template-columns:1.4fr 1fr 1fr 1.6fr auto; gap:12px; padding:12px 0; border-bottom:1px solid {line}; font-size:13px; color:{ink}; text-decoration:none; align-items:center; }}
.account-row a {{ color:{ink}; text-decoration:underline; }}
.account-links {{ display:flex; gap:10px; align-items:center; justify-content:flex-end; white-space:nowrap; }}
.account-row a.account-pay {{ font-weight:600; text-decoration:none; padding:3px 12px; color:{paper}; background:{ink}; border-radius:min({radius}, 6px); }}
.account-owing {{ margin:0 0 6px; font-size:14px; color:{ink}; }}
.account-overdue {{ color:{warn}; }}
.order-pay-button.secondary {{ background:transparent; color:{ink}; border:1px solid {ink}; }}
.terms-text h2 {{ font-size:20px; margin:28px 0 10px; }}
.terms-text ol {{ padding-left:22px; }}
@media (max-width: 640px) {{
	.account-row {{ grid-template-columns:1fr 1fr; }}
	.account-links {{ grid-column:span 2; justify-content:flex-start; }}
	.account-form {{ grid-template-columns:minmax(0,1fr); }}
	.account-form > * {{ grid-column: span 1 !important; }}
}}
"""


def hint(refs, text="", **extra):
	return block(
		"p",
		text=text,
		classes=["checkout-hint"],
		styles={
			"color": refs["muted"],
			"fontSize": "12px",
			"gridColumn": "span 2",
			"lineHeight": "1.5",
			"width": "100%",
		},
		**extra,
	)


def form_error():
	"""Where storefront.js shows a form's errors."""
	return block(
		"div",
		attrs={"data-shop": "error", "role": "alert"},
		classes=["checkout-error"],
		styles={"display": "none", "gridColumn": "span 2"},
	)


def terms_box(lead="I accept the", span=2, margin="6px", business=True):
	"""The terms checkbox, with the store's Terms and Conditions link and note (terms.*), and, for
	purchases, the store's business buyer statement."""
	children = [
		block(
			"label",
			classes=["checkout-check"],
			children=[
				block("input", attrs={"type": "checkbox", "name": "accept_terms", "required": "required"}),
				block(
					"span",
					children=[
						block("span", text=f"{lead} "),
						block(
							"a",
							text="Terms and Conditions",
							attrs={"href": "/terms", "target": "_blank", "data-shop": "terms-link"},
							dynamicValues=[dv("terms.url", "href", "attribute")],
						),
						block(
							"span",
							text="",
							classes=["terms-note"],
							visibilityCondition={"key": "terms.note", "comesFrom": "dataScript"},
							dynamicValues=[dv("terms.note", "innerHTML")],
						),
					],
				),
			],
		),
	]
	if business:
		children.append(
			block(
				"label",
				classes=["checkout-check"],
				visibilityCondition={"key": "terms.business_label", "comesFrom": "dataScript"},
				children=[
					block("input", attrs={"type": "checkbox", "name": "business_buyer"}),
					block("span", text="", dynamicValues=[dv("terms.business_label", "innerHTML")]),
				],
			)
		)
	return block(
		"div",
		name="Terms",
		visibilityCondition={"key": "terms", "comesFrom": "dataScript"},
		styles={
			"display": "flex",
			"flexDirection": "column",
			"gap": "10px",
			"gridColumn": f"span {span}",
			"marginTop": margin,
			"width": "100%",
		},
		children=children,
	)


def pager(refs):
	"""Previous and next page links under a product grid."""
	link = {"color": refs["ink"], "fontSize": "13px", "textDecoration": "underline", "width": "fit-content"}
	return block(
		"nav",
		name="Pager",
		attrs={"aria-label": "Pages"},
		classes=["store-pager"],
		visibilityCondition={"key": "pager", "comesFrom": "dataScript"},
		styles={
			"display": "flex",
			"flexDirection": "row",
			"gap": "24px",
			"justifyContent": "center",
			"marginTop": "32px",
			"width": "100%",
		},
		children=[
			block(
				"a",
				text="← Previous",
				visibilityCondition={"key": "pager.prev_url", "comesFrom": "dataScript"},
				styles=link,
				dynamicValues=[dv("pager.prev_url", "href", "attribute")],
			),
			block(
				"a",
				text="Next →",
				visibilityCondition={"key": "pager.next_url", "comesFrom": "dataScript"},
				styles=link,
				dynamicValues=[dv("pager.next_url", "href", "attribute")],
			),
		],
	)


def breadcrumbs(refs, size="13px"):
	"""The collections a collection is inside (page data key `breadcrumbs`), each a link and a separator."""
	crumb = block(
		"div",
		styles={"alignItems": "center", "display": "flex", "gap": "6px"},
		children=[
			block(
				"a",
				text="Collection",
				attrs={"href": "#"},
				styles={"color": refs["muted"], "fontSize": size, "textDecoration": "none"},
				dynamicValues=[dv("title", "innerHTML"), dv("route", "href", "attribute")],
			),
			block("span", text="\u203a", styles={"color": refs["muted"], "fontSize": size}),
		],
	)
	return repeater(
		"breadcrumbs",
		crumb,
		{"display": "flex", "flexWrap": "wrap", "gap": "6px", "width": "100%"},
		name="Breadcrumbs",
		visibilityCondition={"key": "breadcrumbs", "comesFrom": "dataScript"},
	)


def sub_collections(tile: dict) -> dict:
	"""The collections inside this one (page data key `sub_collections`), as tiles."""
	return repeater(
		"sub_collections",
		tile,
		{
			"display": "grid",
			"gap": "16px",
			"gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"},
		tablet={"gridTemplateColumns": "repeat(3, minmax(0, 1fr))"},
		name="Grid · sub-collections",
		visibilityCondition={"key": "sub_collections", "comesFrom": "dataScript"},
	)


def forgot_password(refs):
	"""Sends Frappe's password reset email to the address in the sign-in form."""
	return block(
		"button",
		text="Forgot your password?",
		attrs={"type": "button", "data-shop": "forgot-password"},
		styles={
			"backgroundColor": "transparent",
			"borderWidth": "0px",
			"color": refs["muted"],
			"cursor": "pointer",
			"fontSize": "12px",
			"gridColumn": "span 2",
			"justifySelf": "start",
			"padding": "0px",
			"textDecoration": "underline",
			"width": "fit-content",
		},
	)


def notice(refs):
	"""A message a page shows instead of its form (page data key `notice`)."""
	return block(
		"p",
		text="",
		classes=["form-done"],
		visibilityCondition={"key": "notice", "comesFrom": "dataScript"},
		dynamicValues=[dv("notice", "innerHTML")],
	)


def shown_with_form(form: dict) -> dict:
	"""The form, shown only when the page data says so (key `show_form`)."""
	form["visibilityCondition"] = {"key": "show_form", "comesFrom": "dataScript"}
	return form


# --- browsing: the catalogue menu, filters and the product listing --------------------------------


def catalog_menu_button(refs, size="13px"):
	"""Opens the catalogue menu, which the store's script fills from its collections and ends with
	all products; while the store has no collections it opens all products. Its label is the
	store's (page data key `store.menu_label`)."""
	return block(
		"button",
		text="Products",
		name="Catalogue Menu",
		attrs={
			"type": "button",
			"data-shop": "catalog-menu-toggle",
			"aria-expanded": "false",
			"aria-controls": "store-catalog-menu",
		},
		classes=["catalog-menu-toggle"],
		styles={"color": refs["ink"], "fontSize": size, "fontWeight": "500"},
		dynamicValues=[dv("store.menu_label", "innerHTML")],
	)


def stock_alert_form():
	"""Shown while what the shopper chose is out of stock: they leave an email to be told when it's
	back (storefront.js, shop.storefront.product.alert_when_in_stock)."""
	return block(
		"form",
		name="Stock Alert",
		attrs={"data-shop": "stock-alert", "hidden": "", "novalidate": ""},
		classes=["stock-alert"],
		children=[
			block("p", text="Out of stock for now. We can email you when it's back.", classes=["stock-alert-intro"]),
			block(
				"div",
				classes=["stock-alert-row"],
				children=[
					block(
						"input",
						attrs={
							"type": "email",
							"name": "email",
							"required": "",
							"autocomplete": "email",
							"placeholder": "Your email",
							"aria-label": "Your email",
						},
					),
					block("button", text="Email me", attrs={"type": "submit"}),
				],
			),
			block("p", text="", attrs={"data-shop": "stock-alert-done", "hidden": "", "role": "status"}, classes=["stock-alert-done"]),
		],
	)


def structured_data():
	"""The product for search engines (page data key `product.structured_data`, schema.org JSON)."""
	return block(
		"script",
		name="Structured Data",
		attrs={"type": "application/ld+json"},
		dynamicValues=[dv("product.structured_data", "innerHTML")],
	)


def currency_picker(styles: dict | None = None):
	"""The currencies prices can be shown in (store.currency_picker_html), looking like the links
	beside it (styles); empty with one currency."""
	return block(
		"div",
		text="",
		name="Currency Picker",
		classes=["store-currency"],
		styles=styles or {},
		dynamicValues=[dv("store.currency_picker_html", "innerHTML")],
	)


def catalog_menu_panel():
	return block(
		"div",
		name="Catalogue Menu Panel",
		attrs={"id": "store-catalog-menu", "data-shop": "catalog-menu", "hidden": ""},
		classes=["catalog-menu"],
	)


def filter_sidebar():
	"""What the products can be narrowed by (page data key `filter_groups`): each group's values as
	links with how many products have them."""
	option = block(
		"a",
		name="Filter Value",
		attrs={"href": "#", "data-active": "false"},
		classes=["filter-value"],
		dynamicValues=[dv("url", "href", "attribute"), dv("active", "data-active", "attribute")],
		children=[
			block("span", text="Value", classes=["filter-value-label"], dynamicValues=[dv("label", "innerHTML")]),
			block(
				"span",
				text="",
				classes=["filter-value-count"],
				visibilityCondition={"key": "count", "comesFrom": "dataScript"},
				dynamicValues=[dv("count", "innerHTML")],
			),
		],
	)
	group = block(
		"div",
		name="Filter Group",
		classes=["filter-group"],
		dynamicValues=[dv("multiple", "data-multiple", "attribute"), dv("single", "data-single", "attribute")],
		children=[
			block("p", text="Filter", classes=["filter-group-label"], dynamicValues=[dv("label", "innerHTML")]),
			repeater("options", option, {"display": "flex", "flexDirection": "column", "gap": "2px"}, name="Filter Values"),
		],
	)
	return block(
		"aside",
		name="Filters",
		attrs={"data-shop": "filter-panel", "aria-label": "Filters"},
		classes=["listing-filters"],
		children=[
			block(
				"div",
				classes=["listing-filters-head"],
				children=[
					block("strong", text="Filters"),
					block("button", text="Done", attrs={"type": "button", "data-shop": "filter-close"}),
				],
			),
			repeater("filter_groups", group, {"display": "flex", "flexDirection": "column", "gap": "22px"}, name="Filter Groups"),
		],
	)


def link_select(label: str, key: str):
	"""A select whose options are links (page data key `key`: label, url, active); choosing one
	opens it."""
	option = block("option", text="Option", dynamicValues=[dv("label", "innerHTML"), dv("url", "value", "attribute"), dv("active", "data-active", "attribute")])
	return block(
		"label",
		name=label,
		classes=["listing-select"],
		children=[
			block("span", text=label),
			repeater(key, option, {}, element="select", attrs={"data-shop": "link-select"}, name=f"{label} Options"),
		],
	)


def listing_toolbar():
	"""How many products there are, the filters button on small screens, sort, products per page and
	grid or list."""
	return block(
		"div",
		name="Listing Toolbar",
		classes=["listing-toolbar"],
		children=[
			block(
				"div",
				classes=["listing-count"],
				children=[
					block("strong", text="0 products", dynamicValues=[dv("total_label", "innerHTML")]),
					block("span", text="", dynamicValues=[dv("page_label", "innerHTML")]),
				],
			),
			block(
				"div",
				classes=["listing-controls"],
				children=[
					block(
						"button",
						name="Show Filters",
						attrs={"type": "button", "data-shop": "filter-toggle", "aria-expanded": "false"},
						classes=["filter-toggle"],
						children=[
							block("span", text="Filters"),
							block(
								"span",
								text="",
								classes=["filter-toggle-count"],
								visibilityCondition={"key": "filter_count", "comesFrom": "dataScript"},
								dynamicValues=[dv("filter_count", "innerHTML")],
							),
						],
					),
					link_select("Sort by", "sort_options"),
					link_select("Per page", "per_page_options"),
					block(
						"div",
						classes=["view-toggle"],
						attrs={"role": "group", "aria-label": "View"},
						children=[
							block(
								"a",
								text="▦",
								attrs={"href": "#", "aria-label": "Grid", "title": "Grid"},
								dynamicValues=[dv("grid_url", "href", "attribute"), dv("grid_active", "data-active", "attribute")],
							),
							block(
								"a",
								text="☰",
								attrs={"href": "#", "aria-label": "List", "title": "List"},
								dynamicValues=[dv("list_url", "href", "attribute"), dv("list_active", "data-active", "attribute")],
							),
						],
					),
				],
			),
		],
	)


def applied_filters():
	"""The filters chosen, each removable, and one link clearing them all."""
	chip = block(
		"a",
		text="Filter",
		attrs={"href": "#"},
		classes=["applied-filter"],
		dynamicValues=[dv("label", "innerHTML"), dv("url", "href", "attribute")],
	)
	return block(
		"div",
		name="Applied Filters",
		classes=["applied-filters"],
		visibilityCondition={"key": "applied", "comesFrom": "dataScript"},
		children=[
			repeater("applied", chip, {"display": "flex", "flexWrap": "wrap", "gap": "8px"}, name="Applied"),
			block(
				"a",
				text="Clear filters",
				attrs={"href": "#"},
				classes=["clear-filters"],
				dynamicValues=[dv("clear_url", "href", "attribute")],
			),
		],
	)


def card_summary():
	"""The product's short description, shown when products are listed rather than in a grid."""
	return block(
		"p",
		text="",
		classes=["product-card-summary"],
		visibilityCondition={"key": "short_description", "comesFrom": "dataScript"},
		dynamicValues=[dv("short_description", "innerHTML")],
	)


def card_buy():
	"""Whether it is in stock, and Add to cart for a product of one version or Choose options."""
	return block(
		"div",
		classes=["product-card-buy"],
		children=[
			block(
				"span",
				text="",
				classes=["product-card-stock"],
				dynamicValues=[dv("stock_label", "innerHTML"), dv("stock_state", "data-stock-state", "attribute")],
			),
			block(
				"button",
				text="Add to cart",
				attrs={"type": "button", "data-shop": "add-to-cart", "data-label": "Add to cart", "data-added-label": "Added ✓"},
				classes=["product-card-action"],
				visibilityCondition={"key": "can_add", "comesFrom": "dataScript"},
				dynamicValues=[dv("item", "data-item-code", "attribute")],
			),
			block(
				"a",
				text="Choose options",
				attrs={"href": "#"},
				classes=["product-card-action"],
				visibilityCondition={"key": "choose_options", "comesFrom": "dataScript"},
				dynamicValues=[dv("route", "href", "attribute")],
			),
		],
	)


def spec_table(heading: dict):
	"""The product's specifications (page data key `product.specifications`) under a heading."""
	row = block(
		"div",
		classes=["spec-row"],
		children=[
			block("dt", text="Specification", dynamicValues=[dv("label", "innerHTML")]),
			block("dd", text="Value", dynamicValues=[dv("value", "innerHTML")]),
		],
	)
	return block(
		"div",
		name="Specifications",
		classes=["spec-table"],
		visibilityCondition={"key": "product.specifications", "comesFrom": "dataScript"},
		children=[heading, repeater("product.specifications", row, {}, element="dl", name="Specification Rows")],
	)


def listing(grid: dict, empty: dict, pager_block: dict):
	"""Filters beside the products: the toolbar, the filters chosen, the products (as a grid or a
	list, page data key `view`) and the pages."""
	grid.setdefault("classes", []).append("product-grid")
	grid.setdefault("dynamicValues", []).append(dv("view", "data-view", "attribute"))
	return block(
		"div",
		name="Listing",
		classes=["listing"],
		children=[
			filter_sidebar(),
			block(
				"div",
				name="Listing Results",
				classes=["listing-results"],
				children=[listing_toolbar(), applied_filters(), grid, empty, pager_block],
			),
		],
	)


def browse_css(refs, radius: str = "2px"):
	"""Styles for the catalogue menu, the listing's filters, toolbar and list view, and product
	cards' buying row."""
	ink, muted, line, card, paper, ok = (
		refs["ink"],
		refs["muted"],
		refs["line"],
		refs["card"],
		refs["paper"],
		refs["success"],
	)
	return f"""
.catalog-menu-toggle {{ background:none; border:0; padding:0; cursor:pointer; display:inline-flex; align-items:center; gap:6px; white-space:nowrap; }}
.catalog-menu-toggle::before {{ content:"\\2630"; font-size:15px; line-height:1; }}
.catalog-menu {{ position:absolute; left:0; right:0; top:100%; z-index:40; max-height:calc(100dvh - 120px); overflow-y:auto; overscroll-behavior:contain; background:{paper}; border-bottom:1px solid {line}; box-shadow:0 18px 40px rgba(0,0,0,.08); }}
.catalog-menu-inner {{ display:grid; grid-template-columns:260px 1fr; max-width:1200px; margin:0 auto; min-height:320px; }}
.catalog-menu-list {{ list-style:none; margin:0; padding:12px 0; border-right:1px solid {line}; }}
.catalog-menu-list button, .catalog-menu-list a {{ display:flex; justify-content:space-between; width:100%; padding:10px 20px; background:none; border:0; font:inherit; font-size:14px; color:{ink}; text-align:left; text-decoration:none; cursor:pointer; }}
.catalog-menu-list [aria-expanded="true"] {{ background:{card}; font-weight:600; }}
.catalog-menu-list a span {{ color:{muted}; font-size:12px; white-space:nowrap; }}
.catalog-menu-flat {{ display:block; min-height:0; padding:24px 28px; }}
.catalog-menu-detail {{ padding:20px 28px; display:flex; flex-direction:column; gap:16px; }}
.catalog-menu-detail > a {{ font-weight:600; color:{ink}; font-size:15px; }}
.catalog-menu-groups {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(180px, 1fr)); gap:18px 24px; }}
.catalog-menu-group {{ display:flex; flex-direction:column; gap:6px; font-size:13px; }}
.catalog-menu-group a {{ color:{ink}; text-decoration:none; }}
.catalog-menu-group a:hover, .catalog-menu-list a:hover {{ text-decoration:underline; }}
.catalog-menu-group > a {{ display:flex; align-items:center; gap:10px; font-weight:600; font-size:14px; }}
.catalog-menu-group img {{ width:40px; height:40px; object-fit:contain; background:{card}; border-radius:{radius}; }}
.catalog-menu-group span {{ color:{muted}; font-size:12px; }}
.catalog-menu-list li.catalog-menu-all {{ border-top:1px solid {line}; margin-top:8px; padding-top:8px; }}
.catalog-menu-list li.catalog-menu-all a, a.catalog-menu-all {{ font-weight:600; }}
.catalog-menu-flat > a.catalog-menu-all {{ display:block; margin-top:22px; padding-top:16px; border-top:1px solid {line}; color:{ink}; font-size:14px; text-decoration:none; }}
.catalog-menu-flat > a.catalog-menu-all:hover {{ text-decoration:underline; }}
@media (max-width: 760px) {{
	.catalog-menu-inner {{ grid-template-columns:1fr; }}
	.catalog-menu-list {{ border-right:0; border-bottom:1px solid {line}; }}
}}
.listing {{ display:grid; grid-template-columns:240px minmax(0, 1fr); gap:40px; width:100%; align-items:start; }}
.listing-filters {{ display:flex; flex-direction:column; gap:22px; }}
.listing-filters-head {{ display:none; }}
.filter-group-label {{ margin:0 0 8px; font-size:12px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:{muted}; }}
.filter-value {{ display:flex; justify-content:space-between; gap:10px; padding:5px 0; font-size:14px; color:{ink}; text-decoration:none; }}
.filter-value:hover .filter-value-label {{ text-decoration:underline; }}
.filter-value[data-active="true"] {{ font-weight:600; background:none; color:{ink}; }}
.filter-group[data-single="true"] .filter-value-label::before {{ content:""; display:inline-block; width:14px; height:14px; margin-right:9px; vertical-align:-2px; border:1px solid {line}; border-radius:50%; }}
.filter-group[data-single="true"] .filter-value[data-active="true"] .filter-value-label::before {{ background:{ink}; border-color:{ink}; box-shadow:inset 0 0 0 3px {paper}; }}
.filter-group[data-multiple="true"] .filter-value-label::before {{ content:""; display:inline-block; width:14px; height:14px; margin-right:9px; vertical-align:-2px; border:1px solid {line}; border-radius:3px; }}
.filter-group[data-multiple="true"] .filter-value[data-active="true"] .filter-value-label::before {{ background:{ink}; border-color:{ink}; box-shadow:inset 0 0 0 2px {paper}; }}
.filter-value-count {{ color:{muted}; font-size:12px; }}
.listing-results {{ display:flex; flex-direction:column; gap:18px; min-width:0; }}
.listing-toolbar {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px 20px; padding-bottom:14px; border-bottom:1px solid {line}; }}
.listing-count {{ display:flex; align-items:baseline; gap:12px; font-size:14px; }}
.listing-count span {{ color:{muted}; font-size:13px; }}
.listing-controls {{ display:flex; align-items:center; flex-wrap:wrap; gap:14px; }}
.listing-select {{ display:flex; align-items:center; gap:8px; font-size:13px; color:{muted}; }}
.listing-select select {{ font:inherit; color:{ink}; background:{paper}; border:1px solid {line}; border-radius:{radius}; padding:6px 8px; cursor:pointer; }}
.view-toggle {{ display:flex; border:1px solid {line}; border-radius:{radius}; overflow:hidden; }}
.view-toggle a {{ padding:4px 10px; font-size:16px; line-height:1.3; color:{muted}; text-decoration:none; }}
.view-toggle a[data-active="true"] {{ background:{ink}; color:{paper}; }}
.filter-toggle {{ display:none; align-items:center; gap:6px; font:inherit; font-size:13px; color:{ink}; background:{paper}; border:1px solid {line}; border-radius:{radius}; padding:6px 12px; cursor:pointer; }}
.filter-toggle-count {{ background:{ink}; color:{paper}; border-radius:9px; font-size:11px; padding:0 6px; }}
.applied-filters {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px 14px; }}
.applied-filter {{ display:inline-flex; align-items:center; gap:6px; padding:5px 10px; font-size:13px; color:{paper}; background:{ink}; border-radius:{radius}; text-decoration:none; }}
.applied-filter::after {{ content:"\\00d7"; font-size:15px; line-height:1; }}
.clear-filters {{ font-size:13px; color:{ink}; text-decoration:underline; }}
.spec-table {{ display:flex; flex-direction:column; gap:16px; width:100%; max-width:860px; }}
.spec-table dl {{ margin:0; border-top:1px solid {line}; }}
.spec-row {{ display:grid; grid-template-columns:minmax(120px, 30%) 1fr; gap:16px; padding:10px 0; border-bottom:1px solid {line}; font-size:14px; }}
.spec-row dt {{ color:{muted}; }}
.spec-row dd {{ margin:0; color:{ink}; }}
.product-card-buy {{ display:flex; flex-direction:column; gap:8px; margin-top:auto; }}
.product-card-stock {{ font-size:12px; color:{ok}; }}
.product-card-stock[data-stock-state="out"] {{ color:{muted}; }}
.product-card-action {{ display:block; text-align:center; font:inherit; font-size:13px; font-weight:600; padding:9px 12px; border-radius:{radius}; cursor:pointer; text-decoration:none; border:1px solid {ink}; }}
button.product-card-action {{ background:{ink}; color:{paper}; }}
a.product-card-action {{ background:transparent; color:{ink}; }}
.product-card-summary {{ display:none; margin:0; font-size:13px; line-height:1.5; color:{muted}; }}
.product-grid[data-view="list"] {{ grid-template-columns:minmax(0, 1fr) !important; gap:0 !important; }}
.product-grid[data-view="list"] > * {{ border-bottom:1px solid {line}; padding:18px 0; }}
.product-grid[data-view="list"] .product-card {{ display:grid !important; grid-template-columns:150px minmax(0, 1fr) 200px; gap:6px 24px; align-items:start; }}
.product-grid[data-view="list"] .product-card > :first-child {{ grid-row:1 / span 6; }}
.product-grid[data-view="list"] .product-card .product-card-buy {{ grid-column:3; grid-row:1 / span 6; margin-top:0; }}
.product-grid[data-view="list"] .product-card-summary {{ display:block; }}
@media (max-width: 900px) {{
	.listing {{ grid-template-columns:minmax(0, 1fr); gap:20px; }}
	.listing-filters {{ display:none; }}
	.listing-filters[data-open="true"] {{ display:flex; position:fixed; inset:0; z-index:80; overflow-y:auto; background:{paper}; padding:20px; }}
	.listing-filters-head {{ display:flex; justify-content:space-between; align-items:center; position:sticky; top:-20px; margin:-20px -20px 0; padding:16px 20px; background:{paper}; border-bottom:1px solid {line}; }}
	.listing-filters-head button {{ font:inherit; font-weight:600; color:{paper}; background:{ink}; border:0; border-radius:{radius}; padding:8px 16px; cursor:pointer; }}
	.filter-toggle {{ display:inline-flex; }}
	.product-grid[data-view="list"] .product-card {{ grid-template-columns:96px minmax(0, 1fr); }}
	.product-grid[data-view="list"] .product-card .product-card-buy {{ grid-column:2; grid-row:auto; }}
}}
"""
