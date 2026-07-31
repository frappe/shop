# Shop

B2C e-commerce for the Frappe stack. The shopper-facing storefront is rendered
entirely by [Frappe Builder](https://github.com/frappe/builder) pages, so
merchants can restyle every page visually. Orders, items, pricing, stock and
customers live in ERPNext. A frappe-ui admin at `/shop` handles onboarding and
day-to-day store management.

## How it fits together

- **Storefront** — eight Builder pages per theme (`home`, `products`,
  `product/:slug`, `collection/:slug`, `cart`, `checkout`,
  `order-confirmation/:order_id`, `account/orders`). Each page has a thin
  `page_data_script` that calls `shop.storefront.page_data.*`; business logic
  lives in `shop/storefront/` and is unit-tested. One shared vanilla JS file
  (`shop/public/js/storefront.js`) powers cart, variant picker and checkout on
  every theme via `data-shop` attributes.
- **Themes** — shipped as Builder template groups in `shop/builder_templates/`
  and synced (unpublished) on install/migrate. Two ship today: **Frappe** (crisp
  white merch storefront, serif display moments) and **Dot** (technical
  monochrome, dot grid canvas, floating capsule nav). Merchants switch between
  them in Settings, Storefront. `shop.themes.apply_theme(group)` clones the group
  into live published pages; merchant edits to the clones survive theme switches.
  Only one theme's pages are published at a time, so no custom page renderer is
  needed. Use `shop.themes.refresh_theme(group)` to push regenerated templates
  into the live pages in place; it never unpublishes, so the storefront stays up.
  Both helpers clear the site cache when they finish: Builder resolves a page's
  components through the cached Builder Component doc, and a stale entry renders
  every component instance (navbar, footer, cart drawer) as empty divs.
- **Cart and checkout** — `Shop Cart` is a lean doctype keyed by an httponly
  cookie token, so guests can shop without an account. Checkout re-validates
  everything server-side, then creates Customer, Contact, Address and a
  submitted Sales Order. Cash on Delivery works out of the box; configuring a
  Payment Gateway Account enables online payment via Payment Request.
- **Catalog** — `Shop Product` is a publish layer over ERPNext Item (slug,
  images, copy, collections, compare-at price, highlights). Variants use
  ERPNext item variants, with the option values a product uses stored on the
  product itself; prices come from Item Price on the configured Price List;
  stock from Bin.
- **Admin** — a frappe-ui app at `/shop` backed by `shop/api/`: analytics,
  orders (mark paid, fulfil, cancel with a timeline), products and variants,
  inventory, collections, customers, reviews, discounts, abandoned carts and
  settings. Each module is a thin whitelisted layer over the same ERPNext
  documents the storefront reads, so nothing is duplicated.

## What merchants can do

| Area | Controls |
| --- | --- |
| Dashboard | Revenue, orders, average order value and conversion over 7, 30 or 90 days, revenue chart, attention list, top products, setup guide |
| Orders | Filter by status, payment and search; mark paid, fulfil, cancel; activity timeline |
| Products | Publish toggles, full editor for copy, media, pricing, compare-at, highlights and collections; create a product with its item, price and opening stock in one step |
| Variants | Define the options a product varies by, generate every combination, then price, stock and enable each one |
| Inventory | Stock levels with low-stock flags and exact-quantity adjustment |
| Customers | Lifetime spend, order history, addresses, reviews |
| Marketing | Coupon codes with validity, usage limits and minimum spend |
| Store | Payments, shipping rates, catalog defaults, storefront theme |

## Setup

```bash
bench get-app shop
bench --site yoursite install-app shop     # requires erpnext, payments, builder
```

`server_script_enabled` must be set in site or common config (page data scripts
run through Frappe's safe_exec).

Open `/shop` and complete onboarding: store details, sample products and
payments. The storefront ships with the Frappe theme, fully editable in
Builder.

## Payments

Cash on Delivery works with zero configuration. For online payments, connect
any gateway supported by the [payments](https://github.com/frappe/payments)
app (Razorpay, Stripe, PayPal, Paytm, Braintree, Mpesa): fill in that
gateway's settings doctype in Desk and a Payment Gateway Account is created
automatically. Pick it in Shop onboarding or Settings. Checkout then issues a
Payment Request and redirects the shopper to the hosted gateway page; after a
successful payment the shop's Payment Request override records a Payment
Entry against the Sales Order and sends the shopper back to their order
confirmation page.

## Development

Dev site setup used for this repo: `shop.localhost` with erpnext, payments,
builder and shop installed, `developer_mode` on.

```bash
bench --site shop.localhost execute shop.demo.setup      # sample catalog
bench --site shop.localhost execute shop.demo.teardown   # remove it
bench --site shop.localhost run-tests --app shop         # server tests
cd apps/shop/e2e && npx playwright test                  # storefront E2E
cd apps/shop && yarn dev                                 # admin SPA dev server
```

## Building your own storefront

The theme's building blocks ship as reusable Builder Components, listed in
Builder's insert panel under a "Shop" prefix: Shop Navbar, Shop Footer, Shop
Cart Drawer, Shop Hero, Shop Product Card, Shop Collection Tile, Shop Filter
Bar, Shop Review Card, Shop Delivery Promise and Shop Trust Row. Theme pages
are assembled from these same components, so a merchant can rebuild any page,
or design a new one, by dragging them onto a canvas.

Every storefront page gets its data from a one-line page data script that
calls `shop.storefront.page_data.*`:

| Route                          | Function             | Main data keys                                                              |
| ------------------------------ | -------------------- | --------------------------------------------------------------------------- |
| `home`                         | `home`               | `store`, `collections`, `featured_products`                                 |
| `products`                     | `listing`            | `store`, `products`, `collections`, `filters`, `search`, `page`, `has_more` |
| `product/:slug`                | `product_page`       | `store`, `product`, `related_products`, `reviews`                           |
| `collection/:slug`             | `collection_page`    | `store`, `collection`, `products`                                           |
| `cart`                         | `cart_page`          | `store`, `cart`                                                             |
| `checkout`                     | `checkout_page`      | `store`, `cart`, `payment_methods`, `currency`                              |
| `order-confirmation/:order_id` | `order_confirmation` | `store`, `order`                                                            |
| `account/orders`               | `account_orders`     | `store`, `orders`                                                           |
| `about`, `contact`, `faq`      | `basic`              | `store`                                                                     |

To build a new page: create it in Builder, drop Shop components in, and set
the page data script to the matching call, for example:

```python
result = frappe.call("shop.storefront.page_data.home")
data.update(result)
```

Data-bound components resolve against that context: list-driven ones (Shop
Product Card, Shop Collection Tile, Shop Review Card) go inside a repeater
bound to the matching list key (`products`, `collections`, `reviews.reviews`).
Include `<script src="/assets/shop/js/storefront.js" defer></script>` in the
page's body HTML and add Shop Cart Drawer as the last block so cart, drawer
and checkout interactions work, then publish.

## Authoring a theme

Themes are generated programmatically (see `shop/theme_generators/frappe.py`
and `dot.py`):

1. On a `developer_mode` site, set `"template_target_app": "shop"` in
   site_config.
2. Write a generator that builds the eight canonical pages with
   `shop.theme_generators.blocks` helpers, palette as Builder Variables
   (`group` = theme codename), and run it with `bench execute`. Every save
   auto-exports fixtures to `shop/builder_templates/<group>/`.
3. Register reusable pieces (navbar, footer, cards, drawer) as Builder
   Components with `upsert_component(component_id, component_name, block)` and
   place them in pages with `component_ref(component_id)`; repeater children
   can be component refs too. Component ids are global, not per group, so
   prefix them with the theme codename (`dot-navbar`) or a second theme will
   overwrite the first theme's components. Components referenced by template
   pages are exported to `shop/builder_templates/<group>/components/` and
   installed on consumer sites automatically.
4. Keep all functional `data-shop` hooks intact (see `storefront.js`) and give
   the theme a distinct structural layout, not just new colors.
5. Fill `template.json` (description, categories, order) and verify with the
   Playwright suite after `shop.themes.apply_theme`. The suite is theme
   agnostic: it drives `data-shop` hooks, but it does pin shared copy such as
   "Your cart is empty." and headings like "Order summary", so keep those.
