# Theming

The storefront is made of ordinary [Frappe Builder](https://github.com/frappe/builder)
pages, so anything you can build in Builder can be a storefront page.

## Page data

Every storefront page gets its data from a one line page data script that calls
`shop.storefront.page_data.*`:

| Route                          | Function             | Main data keys                                                                              |
| ------------------------------ | -------------------- | ------------------------------------------------------------------------------------------- |
| `home`                         | `home`               | `store`, `collections`, `featured_products`                                                 |
| `products`                     | `listing`            | `store`, `products`, `collections`, `filters`, `search`, `page`, `has_more`                 |
| `product/:slug`                | `product_page`       | `store`, `product`, `related_products`, `reviews`                                           |
| `collection/:slug`             | `collection_page`    | `store`, `collection`, `products`, `breadcrumbs`, `sub_collections`                         |
| `cart`                         | `cart_page`          | `store`, `cart`                                                                             |
| `checkout`                     | `checkout_page`      | `store`, `cart`, `payment_methods`, `addresses`, `prefill`, `countries`, `terms`            |
| `order-confirmation/:order_id` | `order_confirmation` | `store`, `order` (with `totals_html`, `payment_html`)                                       |
| `account/orders`               | `account_orders`     | `store`, `orders`, `account_html`, `trade`                                                  |
| `account/signin`               | `signin_page`        | `store`, `show_form`, `notice`, `redirect_to` (Frappe's login and password reset)             |
| `account/register`             | `register_page`      | `store`, `terms`, `show_form`, `notice`                                                     |
| `account/trade`                | `trade_page`         | `store`, `terms`, `countries`, `prefill`, `industries`, `show_form`, `notice`               |
| `quote/:quote_id`              | `quote_page`         | `store`, `quote`, `quote_invalid`, `terms`                                                  |
| `terms`                        | `terms_page`         | `store`, `terms_html`, `terms_version`                                                      |
| `about`, `contact`, `faq`      | `basic`              | `store`                                                                                     |

`store` carries the store's name and logo, the account and sign-up links, and
`currency_picker_html`. Prices come formatted for the shopper (`formatted_price`, and
`formatted_price_excl` when the store shows prices with tax). Page data goes into the page
as HTML, so anything a shopper typed is escaped on the server.

```python
result = frappe.call("shop.storefront.page_data.home")
data.update(result)
```

`server_script_enabled` has to be set bench-wide (`bench set-config --global
server_script_enabled 1`), since page data scripts run through Frappe's
`safe_exec`, which only reads `common_site_config.json`.

## Building a page

Each theme ships its building blocks as Builder Components, listed in Builder's
insert panel: navbar, footer, cart drawer, hero, product card, collection tile,
filter bar, review card, delivery promise and spec row. Theme pages are
assembled from those same components, so you can rebuild any page, or design a
new one, by dragging them onto a canvas.

List driven components (product card, collection tile, review card) go inside a
repeater bound to the matching list key: `products`, `collections`,
`reviews.reviews`. Include `<script src="/assets/shop/js/storefront.js" defer></script>`
in the page's body HTML and add the cart drawer as the last block so cart,
drawer and checkout interactions work, then publish.

## Authoring a theme

Themes are generated programmatically. See `shop/theme_generators/frappe.py`
and `dot.py` for two worked examples.

1. On a `developer_mode` site, set `"template_target_app": "shop"` in
   site_config.
2. Write a generator that builds the canonical pages with
   `shop.theme_generators.blocks` helpers and the palette as Builder Variables
   (`group` = theme codename), then run it with `bench execute`. Every save auto
   exports fixtures to `shop/builder_templates/<group>/`.
3. Register reusable pieces with `upsert_component(component_id, component_name, block)`
   and place them with `component_ref(component_id)`. Component ids are global
   rather than per group, so prefix them with the theme codename (`dot-navbar`)
   or a second theme will overwrite the first theme's components.
4. Keep the functional `data-shop` hooks intact (see `storefront.js`) and give
   the theme a distinct structural layout, not just new colours.
5. Fill `template.json` (description, categories, order) and verify with the
   Playwright suite.

### Site themes

A site can have its own version of a theme without copying it: pass a `Theme` with what
differs to the generator, from the site's own app.

```python
from shop.theme_generators import frappe as base


def generate():
	base.generate(
		base.Theme(
			group="acme",  # its own template group; components are named acme-navbar, acme-hero...
			title="Acme",
			head="Fraunces",
			body="Inter",
			palette={"accent": ("#0F766E", "#2DD4BF")},
			skip_routes={"about", "contact"},  # pages the site already has
			component_ids={"shop-footer": "acme-footer"},
			site_components={"acme-footer"},  # the site's own footer, placed but not generated
			header_component="acme-header",  # placed above every page
			blocks={"hero": acme_hero},  # function(refs) -> block, for any component or page
			faqs=[("Do you ship abroad?", "Yes, to most countries.")],
			listing_subtitle="Everything we make.",
			extra_css=".product-description h3 { font-size: 18px; }",
		)
	)
```

The dot generator takes the same `Theme` (`shop.theme_generators.dot.Theme`), with a `mono`
font as well. Register the generated components in the site app's `shop_theme_components`
hook (see [Extending Shop](extending.md#site-themes)), then apply the theme with
`shop.themes.apply_theme("acme")`.

### Deploying changes

```bash
bench --site yoursite execute shop.theme_generators.dot.generate
bench --site yoursite execute shop.themes.refresh_theme --kwargs '{"group":"dot"}'
```

`refresh_theme` pushes regenerated templates into the live pages in place and
never unpublishes, so the storefront stays up. `apply_theme` is for switching
themes; on its own it republishes the existing clones, which still point at the
previous component block ids.

Both helpers clear the site cache when they finish. Builder resolves a page's
components through the cached Builder Component doc, and a stale entry renders
every component instance (navbar, footer, cart drawer) as empty divs.

### Test contract

The Playwright suite is theme agnostic: it drives `data-shop` hooks rather than
markup. It does pin a little shared copy, so a new theme should keep phrases
like "Your cart is empty." and headings like "Order summary" and
"Returns & replacements".
