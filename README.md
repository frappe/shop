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
  and synced (unpublished) on install/migrate. `shop.themes.apply_theme(group)`
  clones the group into live published pages; merchant edits to the clones
  survive theme switches. Only one theme's pages are published at a time, so no
  custom page renderer is needed.
- **Cart and checkout** — `Shop Cart` is a lean doctype keyed by an httponly
  cookie token, so guests can shop without an account. Checkout re-validates
  everything server-side, then creates Customer, Contact, Address and a
  submitted Sales Order. Cash on Delivery works out of the box; configuring a
  Payment Gateway Account enables online payment via Payment Request.
- **Catalog** — `Shop Product` is a publish layer over ERPNext Item (slug,
  images, copy, collections). Variants use ERPNext item variants; prices come
  from Item Price on the configured Price List; stock from Bin.

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

## Authoring a theme

Themes are generated programmatically (see `shop/theme_generators/linen.py`):

1. On a `developer_mode` site, set `"template_target_app": "shop"` in
   site_config.
2. Write a generator that builds the eight canonical pages with
   `shop.theme_generators.blocks` helpers, palette as Builder Variables
   (`group` = theme codename), and run it with `bench execute`. Every save
   auto-exports fixtures to `shop/builder_templates/<group>/`.
3. Keep all functional `data-shop` hooks intact (see `storefront.js`) and give
   the theme a distinct structural layout, not just new colors.
4. Fill `template.json` (description, categories, order) and verify with the
   Playwright suite after `shop.themes.apply_theme`.
