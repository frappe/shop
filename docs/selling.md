# Selling

Everything the store sells with is an ERPNext document, so the desk, reports and accounts
see exactly what the storefront did. This page lists the store settings (Shop Settings, also
in the admin at `/shop/settings`) and the ERPNext records behind them. New behaviour is off
until it is turned on.

## The catalogue

- Products are grouped in Shop Collections, which can sit inside each other and include an
  ERPNext Item Group's products. The store's catalogue menu (its label is **Catalogue Menu
  Label**) lists them, and a collection's page lists its products and those of the
  collections inside it.
- Listing pages filter by availability, price, Brand (the Item's), any Shop Specification set
  *Use as Filter*, and variant options; sort; and show 24, 48 or 96 a page, as a grid or a list.
  A product's specifications show as a table on its page.
- Search matches every word somewhere in a product (its name, item code, descriptions, brand,
  specifications or its variants' names). When nothing matches, words the store's products
  don't use are swapped for the nearest ones they do, and the page says so. Search boxes
  suggest products as the shopper types.
- Search engines: product pages carry their own title, description, image and schema.org
  Product data (price, stock, brand, rating); cart, checkout and account pages are marked
  noindex. `/store_sitemap.xml` lists the products and collections the site's sitemap leaves
  out, and robots.txt points to it.
- Options can be added to a product that is already selling: its Item becomes a variant of a
  new template, keeping its stock and sales (this needs ERPNext's support for stocked items
  becoming variants).

## Prices and tax

- Prices come from the store's Price List. A signed-in customer gets their own: the Price
  List of their Customer or Customer Group, with ERPNext's Pricing Rules applied (trade
  discounts, quantity breaks). A customer's own Price List is final: an item that isn't on
  it isn't for sale to them, as ERPNext would price it. A guest's cart gets the Pricing
  Rules of the default Customer Group.
- Coupons are ERPNext Coupon Codes: the order carries the code and ERPNext applies its
  Pricing Rule (who it is for, which items, the minimum), validates it and counts its use.
- Products say whether they can be bought: in stock, only a few left (**Low Stock
  Threshold**), out of stock, or not available online when they have no price. The cart
  takes only what can be bought.
- Checkout builds the Sales Order it will place and lets ERPNext price, tax and total it, so
  the total shown is the total charged. Coupons, Item Tax Templates and rounding follow
  ERPNext.
- Taxes: the store's Tax Template, or the ERPNext Tax Rule marked *Use for Shopping Cart*
  that matches the delivery address and customer. Orders shipped outside the company's
  country use the **Export Tax Template** when no rule matches.
- **Prices Include Tax**: the price list includes the Tax Template's tax (its rows must be
  *Included in Print Rate*).
- **Show Prices With Tax**: product, cart and checkout prices are shown with the tax, and
  the price without tax under them. Each item is shown at the rate of its Item Tax Template
  (on the Item or its Item Group), so a zero-rated item is shown without tax.

## Paying

- **Cash on Delivery**.
- **Online**: any gateway of the payments app, through a Payment Gateway Account. The
  **Online Payment Label** names it at checkout. A **Card Fee** (percent and fixed, with
  their own international rates) can be added as a line: what the store keeps of it covers
  the provider's charge on the final total.
- **Bank transfer**: the store's ERPNext Bank Accounts, one per currency, listed in Shop
  Settings. The shopper sees the account details, the amount and the order number as the
  reference. An account in another currency can add a currency conversion fee.
  - Each account can add the fee its bank takes from a transfer (the **Transfer Fee Item**
    line): a **Local Transfer Fee**, and a **Swift Transfer Fee** for international
    transfers. Swift is offered when the account's Bank has a SWIFT code; the shopper picks
    where they pay from, suggested by where the order is going.
  - A deposit in a Bank Transaction (from a bank statement import or a bank feed) whose
    reference names an unpaid bank transfer order pays it: a Payment Entry for what the
    customer sent, with any fee the bank reports booked to the **Bank Charges Account**,
    reconciled with the Bank Transaction. A payment short of the total leaves the order
    waiting, and the customer is emailed the balance.
- **Pay on account**: customers with *Pay on Account at the Store* and Payment Terms are
  invoiced straight away, to their billing address. Their credit limit applies to orders on
  account (approving a trade account sets ERPNext's *Bypass Credit Limit Check at Sales
  Order*, so orders paid up front aren't held).
- Checkout takes the buyer's purchase order number (into ERPNext's *Customer's Purchase
  Order*, which goes onto the invoice) and a note for the order, which staff see on the order.
- A customer can have two orders waiting for a bank transfer, and one visitor can place five
  a day, so stock can't be held without paying.
- **Order Naming Series**: a short Sales Order series for store orders (e.g. `SO-.#####`),
  so the order number fits a bank transfer reference. Deposits are matched to an order
  whatever spaces, dashes or case the payer used.

Shipping and fees are order lines (the Shipping Item, Card Fee Item, Currency Conversion Item and
Transfer Fee Item), so they show on the order and invoice like any other line.

## After checkout

- **Invoice Paid Orders**: once an order is paid in full, its Sales Invoice is made with
  ERPNext's own *Make Sales Invoice*, the payment allocated, and emailed to the customer.
- **Cancel Unpaid Orders**: online and bank transfer orders not paid by their due date
  (**Days to Pay Online**, **Days to Pay** for bank transfers) are cancelled, and the
  customer is told.
- **Email Shipping Updates**: the customer hears when their order ships and when it is
  delivered. An order sent through a fulfilment provider shows *Preparing* until the
  courier has it.
- **Unpaid online orders**: the customer can pay later from their order page, and is
  reminded once by email (**Remind Unpaid Online Orders After**, in hours; 0 for none).
- **Remind Left Carts After** (hours; 0 for none): a cart left with items is emailed about
  once, with a link that brings it back. Check your country's rules on marketing email first.
- **Back in stock**: on an out-of-stock product or variant the shopper can leave their email,
  and is emailed once when it can be bought again (Shop Stock Alert).
- **Returns**: customers ask from their order page once it has shipped, within the **Return
  Window** (days; 0 turns it off). Approving emails them; completing makes ERPNext's return
  Delivery Note and credit note for the quantity returned.
- **Cancelling**: staff cancel an order from the admin before it ships. An unpaid order is
  cancelled; a paid or invoiced one is credited in full and closed. The customer is emailed
  either way.
- **Refunds** are never automatic. A credit note still owed to the customer shows under
  *Refunds due* on the admin order page, where staff refund it to the card (through a
  gateway that can refund, such as Stripe) or record a refund paid from a bank account.
  Either way it is an ERPNext Payment Entry against the credit note, and the customer is
  emailed.
- **Shipping** is booked by staff: a paid order sent to a fulfilment provider gets a draft
  Shipment, which staff book with a courier and print the label from, on the admin order
  page.
- Store emails are Frappe Email Templates named *Shop: ...*, made once and never
  overwritten, so they can be edited in the desk.

## Customer accounts

- **Require Terms**: shoppers accept the store's ERPNext Terms and Conditions when they sign
  up, order or accept a quote. What they accepted and when is kept on the order or user,
  and the terms print on the order and invoice.
- **Trade accounts**: businesses apply on the store's trade page. Each application is an
  ERPNext Lead (UTM Source *Store Trade Application*). Staff approve or decline it from the
  Lead: approving makes the Customer (or updates the applicant's own) in the **Trade
  Customer Group**, with Payment Terms, credit limit and pay on account as chosen.
  Waiting applications show on the Shop dashboard. In the Shop admin, a customer's page can
  make them a trade customer (or end it). **Trade accounts** in the admin lists the accounts,
  the applications and the trade rates: percent off or a fixed price for an Item Group or a
  product, with quantity breaks, for everyone, for trade accounts or for one customer (whose
  own rates replace the trade ones). Each rate is an ERPNext Pricing Rule.
- **Quote Requests**: shoppers can ask for a quote at checkout. It arrives as a draft
  Quotation, valid for **Quotes Valid For** days; staff submit it and send it from the
  Quotation, and the customer accepts it online, which places the order.
- **Email Monthly Statements**: the trade Customer Group gets an ERPNext Process Statement
  Of Accounts each month. Customers can also download their statement from their account.
- The account page lists the customer's invoices, says what is owing and what is overdue, and
  has a Pay button beside each unpaid invoice an app gives a payment link (the payments app's
  invoice payment links); the statement email links to paying too.

## Currencies

Shoppers can see approximate prices in any currency the store has a bank account in, at
ERPNext's exchange rate, and pay by bank transfer in it. Online and cash payments are in the
company currency.
