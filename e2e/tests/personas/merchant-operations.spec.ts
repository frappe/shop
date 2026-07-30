import { expect, test, type BrowserContext, type Locator, type Page } from "@playwright/test";

import {
	addToCartViaPDP,
	adminApi,
	applyCoupon,
	chooseOption,
	clearCart,
	confirmDialog,
	loginViaApi,
	placeCodOrder,
	saveSettingsSection,
	summaryValue,
	uniqueBuyer,
	type AdminApi,
} from "./helpers";

test.describe.configure({ mode: "serial" });

const ts = Date.now();
const ORDER_PRODUCT = { name: "Scented Soy Candle", slug: "scented-soy-candle", item: "SHOP-DEMO-005" };
const CART_PRODUCT = { slug: "enamel-pin-set", pairValue: "₹ 998.00" };
const REVIEW_PRODUCT = { name: "Wireless Charging Pad", slug: "wireless-charging-pad" };
const MUG = "Ceramic Mug";
const PRODUCT_NAME = `Persona Widget ${ts}`;
const PRODUCT_SLUG = `persona-widget-${ts}`;
const HIGHLIGHT = "Machined from a single billet";
const COUPON = `PERSONA${ts}`;

interface ReviewDoc {
	name: string;
	product: string;
	reviewer_name: string;
	rating: number;
	title: string;
	review: string;
	verified: number;
}

test.describe("Store owner running the admin panel day to day", () => {
	const buyer = { ...uniqueBuyer("ops"), full_name: `Ops Buyer ${ts}` };

	let api: AdminApi;
	let settings: Record<string, unknown>;
	let admin: BrowserContext;
	let page: Page;
	let shopper: BrowserContext;
	let shopperPage: Page;
	let browserCtx: BrowserContext;
	let orderId = "";
	let mugStock = 0;
	let orderProductStock = 0;
	let widgetItem = "";
	let reviewBackup: ReviewDoc[] = [];

	function row(text: string) {
		return page.locator("tbody tr", { hasText: text });
	}

	function section(description: string) {
		return page.locator("section", { hasText: description });
	}

	function timeline() {
		return page.getByRole("heading", { name: "Timeline" }).locator("xpath=..");
	}

	function chartBars() {
		return page.locator("svg rect.fill-surface-gray-7");
	}

	function reviewSummary() {
		return page.getByRole("heading", { name: "Reviews" }).locator("xpath=following-sibling::div[1]");
	}

	function reviewCards() {
		return page.locator("div.rounded-lg.border-outline-gray-1.p-4");
	}

	function thresholdTile() {
		return page.getByText("Low stock threshold").locator("xpath=following-sibling::div[1]");
	}

	async function readReviewSummary() {
		const text = (await reviewSummary().textContent()) || "";
		const match = text.match(/([\d.]+)\s*from (\d+) reviews/);
		return { average: Number(match?.[1]), total: Number(match?.[2]) };
	}

	/** Lists reload asynchronously, so poll the rendered values instead of reading them once. */
	function distinctText(locator: Locator, attribute?: string) {
		return locator.evaluateAll(
			(nodes, name) => [
				...new Set(nodes.map((node) => (name ? node.getAttribute(name) : node.textContent))),
			],
			attribute
		);
	}

	async function pdpReviewCount(slug: string): Promise<number> {
		await shopperPage.goto(`/product/${slug}`);
		const text = (await shopperPage.locator("body").textContent()) || "";
		return Number(text.match(/Based on (\d+) reviews/)?.[1]);
	}

	async function firstIncomeAccount(): Promise<string> {
		await page.locator('[data-slot="trigger"]', { hasText: "No shipping account" }).click();
		const label = await page.getByRole("option").nth(1).innerText();
		await page.keyboard.press("Escape");
		return label.trim();
	}

	async function freshCheckout() {
		await clearCart(shopperPage);
		await addToCartViaPDP(shopperPage, ORDER_PRODUCT.slug);
		await shopperPage.goto("/checkout");
	}

	async function productNamed(slug: string): Promise<string> {
		const rows = await api.call<{ name: string }[]>("frappe.client.get_list", {
			doctype: "Shop Product",
			filters: { slug },
		});
		return rows[0].name;
	}

	async function reviewsOf(product: string): Promise<ReviewDoc[]> {
		return api.call("frappe.client.get_list", {
			doctype: "Shop Review",
			filters: { product },
			fields: ["name", "product", "reviewer_name", "rating", "title", "review", "verified"],
			limit_page_length: 0,
		});
	}

	async function restoreReviews() {
		for (const review of reviewBackup) {
			const exists = await api.call<{ name: string }[]>("frappe.client.get_list", {
				doctype: "Shop Review",
				filters: { name: review.name },
			});
			if (exists.length) continue;
			const { name, ...fields } = review;
			await api.call("frappe.client.insert", { doc: { doctype: "Shop Review", ...fields } });
		}
	}

	async function deleteIfExists(doctype: string, filters: Record<string, unknown>) {
		const rows = await api.call<{ name: string }[]>("frappe.client.get_list", {
			doctype,
			filters,
			limit_page_length: 0,
		});
		for (const doc of rows)
			await api.call("frappe.client.delete", { doctype, name: doc.name }).catch(() => {});
	}

	async function readStock(itemCode: string): Promise<number> {
		const rows = await api.call<{ actual_qty: number }[]>("frappe.client.get_list", {
			doctype: "Bin",
			filters: { item_code: itemCode, warehouse: settings.default_warehouse },
			fields: ["actual_qty"],
		});
		return rows[0]?.actual_qty ?? 0;
	}

	async function restoreStock(itemCode: string, qty: number) {
		if ((await readStock(itemCode)) === qty) return;
		await api.call("shop.api.inventory.set_stock", { item_code: itemCode, qty });
	}

	/** The Add product dialog leaves an Item, its price and an opening stock entry behind. */
	async function purgeWidgetItem() {
		if (!widgetItem) return;
		await deleteIfExists("Shop Product", { product_name: PRODUCT_NAME });
		const entries = await api.call<{ parent: string }[]>("frappe.client.get_list", {
			doctype: "Stock Entry Detail",
			filters: { item_code: widgetItem },
			fields: ["parent"],
			parent: "Stock Entry",
			limit_page_length: 0,
		});
		for (const entry of new Set(entries.map((detail) => detail.parent)))
			await api.call("frappe.client.cancel", { doctype: "Stock Entry", name: entry }).catch(() => {});
		await deleteIfExists("Item Price", { item_code: widgetItem });
		try {
			await api.call("frappe.client.delete", { doctype: "Item", name: widgetItem });
		} catch {
			// ERPNext keeps items whose stock has moved, so retire it out of the catalogue instead
			await api
				.call("frappe.client.set_value", {
					doctype: "Item",
					name: widgetItem,
					fieldname: "disabled",
					value: 1,
				})
				.catch(() => {});
		}
	}

	test.beforeAll(async ({ browser }) => {
		api = await adminApi();
		settings = await api.getSettings();
		await api.setSettings({ onboarding_complete: 1 });
		orderProductStock = await readStock(ORDER_PRODUCT.item);

		admin = await browser.newContext();
		page = await admin.newPage();
		await loginViaApi(page, "Administrator", "admin");

		shopper = await browser.newContext();
		shopperPage = await shopper.newPage();
	});

	test.afterAll(async () => {
		try {
			await api.setSettings({
				store_name: settings?.store_name || "Frappe Shop",
				enable_cod: 1,
				onboarding_complete: 1,
				flat_shipping_rate: settings?.flat_shipping_rate || 0,
				free_shipping_above: settings?.free_shipping_above || 0,
				shipping_account: settings?.shipping_account || "",
				low_stock_threshold: settings?.low_stock_threshold || 5,
			});
			if (mugStock) await restoreStock("SHOP-DEMO-003", mugStock);
			// fulfilling the order shipped a unit out of the demo catalogue
			if (orderProductStock) await restoreStock(ORDER_PRODUCT.item, orderProductStock);
			await restoreReviews();
			await deleteIfExists("Coupon Code", { coupon_code: COUPON });
			await deleteIfExists("Pricing Rule", { title: `Shop coupon ${COUPON}` });
			await purgeWidgetItem();
		} finally {
			await api?.dispose();
			await admin?.close();
			await shopper?.close();
			await browserCtx?.close();
		}
	});

	test("a guest places a fresh COD order on the storefront", async () => {
		await clearCart(shopperPage);
		await addToCartViaPDP(shopperPage, ORDER_PRODUCT.slug);
		orderId = await placeCodOrder(shopperPage, buyer);
		expect(orderId).toBeTruthy();
	});

	test("searching the orders list opens the new order as unpaid and unfulfilled", async () => {
		await page.goto("/shop/orders");
		await page.getByPlaceholder("Search orders").fill(orderId);
		await expect(row(orderId)).toBeVisible();
		await expect(row(orderId)).toContainText(buyer.full_name);
		await row(orderId).click();

		await page.waitForURL(new RegExp(`/shop/orders/${orderId}`));
		await expect(page.getByText("Unpaid", { exact: true })).toBeVisible();
		await expect(page.getByText("Unfulfilled", { exact: true })).toBeVisible();
		await expect(page.locator("tbody")).toContainText(ORDER_PRODUCT.name);
	});

	test("Mark paid records a payment on the timeline and flips the badge", async () => {
		await page.getByRole("button", { name: "Mark paid", exact: true }).click();
		await expect(
			page.getByRole("dialog").getByText(`Record a payment entry for ${orderId}?`)
		).toBeVisible();
		await confirmDialog(page, "Mark paid");

		await expect(page.getByText("Paid", { exact: true })).toBeVisible();
		await expect(timeline()).toContainText("Payment recorded");
	});

	test("Fulfill ships the order and the actions stop being offered", async () => {
		await page.getByRole("button", { name: "Fulfill", exact: true }).click();
		await expect(page.getByRole("dialog").getByText(`delivery note for ${orderId}?`)).toBeVisible();
		await confirmDialog(page, "Fulfill");

		await expect(page.getByText("Fulfilled", { exact: true })).toBeVisible();
		await expect(timeline()).toContainText(/Fulfilled via \S+/);
		await expect(page.getByRole("button", { name: "Mark paid", exact: true })).toHaveCount(0);
		await expect(page.getByRole("button", { name: "Fulfill", exact: true })).toHaveCount(0);
	});

	test("the orders list shows the new badges and honours the payment filter", async () => {
		await page.goto("/shop/orders");
		await page.getByPlaceholder("Search orders").fill(orderId);
		await expect(row(orderId)).toContainText("Paid");
		await expect(row(orderId)).toContainText("Fulfilled");

		await chooseOption(page, "All payments", "Paid");
		await expect(row(orderId)).toBeVisible();

		await chooseOption(page, "Paid", "Unpaid");
		await expect(page.locator("tbody")).not.toContainText(orderId);
		await expect(page.getByText("No orders found")).toBeVisible();
	});

	test("the dashboard period switcher relabels the stats and redraws the chart", async () => {
		await page.goto("/shop");
		await expect(page.getByText("Last 30 days").first()).toBeVisible();
		await expect(chartBars()).toHaveCount(30);

		await page.getByRole("radio", { name: "7 days" }).click();
		await expect(page.getByText("Last 7 days").first()).toBeVisible();
		await expect(page.getByText("Last 30 days")).toHaveCount(0);
		await expect(chartBars()).toHaveCount(7);

		await page.getByRole("radio", { name: "90 days" }).click();
		await expect(page.getByText("Last 90 days").first()).toBeVisible();
		await expect(chartBars()).toHaveCount(90);

		await page.getByRole("radio", { name: "30 days" }).click();
		await expect(page.getByText("Last 30 days").first()).toBeVisible();
	});

	test("the Needs attention cards deep link into the right pages", async () => {
		const targets = [
			["orders to fulfill", "/shop/orders"],
			["low stock products", "/shop/inventory"],
			["active carts", "/shop/carts"],
		];
		for (const [label, route] of targets) {
			await page.goto("/shop");
			await page.getByRole("link").filter({ hasText: label }).click();
			await page.waitForURL(new RegExp(`${route}$`));
		}
	});

	test("the dashboard lists at least one top selling product", async () => {
		await page.goto("/shop");
		const table = page
			.getByRole("heading", { name: "Top products" })
			.locator("xpath=following-sibling::div[1]");
		await expect(table).not.toContainText("No sales yet");
		expect(await table.locator("tbody tr").count()).toBeGreaterThan(0);
	});

	test("the product page publishes a product with price and opening stock", async () => {
		await page.goto("/shop/products");
		await page.getByRole("link", { name: "Add product" }).click();
		await page.waitForURL(/\/shop\/products\/new/);

		await page.getByLabel("Product name").fill(PRODUCT_NAME);
		await page.getByLabel("Price", { exact: true }).fill("349");
		await page.getByLabel("Opening stock", { exact: true }).fill("6");
		await expect(page.getByRole("switch", { name: "Published" })).toHaveAttribute("aria-checked", "true");
		await page.getByRole("button", { name: "Create" }).click();
		await page.waitForURL(/\/shop\/products\/[^/]+$/, { timeout: 20000 });

		await page.goto("/shop/products");

		await page.getByPlaceholder("Search products").fill(PRODUCT_NAME);
		await expect(row(PRODUCT_NAME)).toBeVisible();
		await expect(row(PRODUCT_NAME).locator("td").nth(2)).toHaveText("₹ 349.00");
		await expect(row(PRODUCT_NAME).locator("td").nth(3)).toHaveText("6");

		const created = await api.call<{ item: string }[]>("frappe.client.get_list", {
			doctype: "Shop Product",
			filters: { product_name: PRODUCT_NAME },
			fields: ["item"],
		});
		widgetItem = created[0].item;
	});

	test("the editor saves a compare-at price and a highlight line", async () => {
		await page.goto("/shop/products");
		await page.getByPlaceholder("Search products").fill(PRODUCT_NAME);
		await row(PRODUCT_NAME).locator("td").nth(1).click();
		await page.waitForURL(/\/shop\/products\/[^/]+$/);

		await expect(page.getByLabel("Slug")).toHaveValue(PRODUCT_SLUG);
		await page.getByLabel("Compare-at price").fill("499");
		await page.getByPlaceholder("Dishwasher safe").fill(HIGHLIGHT);
		await page.getByRole("button", { name: "Save" }).click();
		await expect(page.getByRole("button", { name: "Save" })).toBeDisabled({ timeout: 15000 });
	});

	test("the storefront PDP shows the struck price, discount tag and highlight", async () => {
		await shopperPage.goto(`/product/${PRODUCT_SLUG}`);
		await expect(shopperPage.locator('[data-shop="pdp-price"]')).toHaveText("₹ 349.00");

		const struck = shopperPage.locator('[data-shop="pdp-price"] ~ span').first();
		await expect(struck).toHaveText("₹ 499.00");
		await expect(struck).toHaveCSS("text-decoration-line", "line-through");
		await expect(shopperPage.locator('[data-shop="pdp-price"] ~ div').first()).toHaveText("30% OFF");
		await expect(shopperPage.getByText(HIGHLIGHT)).toBeVisible();
	});

	test("unpublishing from the list takes the PDP off the storefront", async () => {
		await page.goto("/shop/products");
		await page.getByPlaceholder("Search products").fill(PRODUCT_NAME);
		await expect(row(PRODUCT_NAME)).toBeVisible();
		await row(PRODUCT_NAME).getByRole("switch").click();
		await expect(row(PRODUCT_NAME).getByRole("switch")).toHaveAttribute("aria-checked", "false");

		const response = await shopperPage.goto(`/product/${PRODUCT_SLUG}`);
		expect(response?.status()).toBe(404);
	});

	test("deleting it from the row menu drops it out of the list", async () => {
		await row(PRODUCT_NAME).locator("td").last().getByRole("button").click();
		await page.getByRole("menuitem", { name: "Delete" }).click();
		await expect(page.getByRole("dialog")).toContainText(PRODUCT_NAME);
		await confirmDialog(page, "Delete");

		await expect(page.getByText("No products found")).toBeVisible();
		await expect(page.locator("tbody")).toHaveCount(0);
	});

	test("inventory sets an exact stock count that the products list picks up", async () => {
		await page.goto("/shop/inventory");
		await page.getByPlaceholder("Search by item or product").fill(MUG);
		await expect(row(MUG)).toHaveCount(1);
		mugStock = Number(await row(MUG).locator("td").nth(3).innerText());
		expect(mugStock).toBeGreaterThan(0);

		await row(MUG).locator('input[type="number"]').fill("17");
		await row(MUG).getByRole("button", { name: "Set" }).click();
		await expect(page.getByText("Stock set to 17")).toBeVisible();
		await expect(row(MUG).locator("td").nth(3)).toHaveText("17");

		await page.goto("/shop/products");
		await page.getByPlaceholder("Search products").fill(MUG);
		await expect(row(MUG).locator("td").nth(3)).toHaveText("17");
	});

	test("restoring the count from inventory puts the demo catalogue back", async () => {
		await page.goto("/shop/inventory");
		await page.getByPlaceholder("Search by item or product").fill(MUG);
		await expect(row(MUG)).toHaveCount(1);
		await row(MUG).locator('input[type="number"]').fill(String(mugStock));
		await row(MUG).getByRole("button", { name: "Set" }).click();
		await expect(page.getByText(`Stock set to ${mugStock}`)).toBeVisible();
		await expect(row(MUG).locator("td").nth(3)).toHaveText(String(mugStock));
	});

	test("Low stock only surfaces the out of stock demo print", async () => {
		await page.getByPlaceholder("Search by item or product").fill("");
		await page.getByRole("switch", { name: "Low stock only" }).click();
		await expect(row("Botanical Art Print")).toBeVisible();
		await expect(row(MUG)).toHaveCount(0);
	});

	test("the reviews page reports the catalogue average and total", async () => {
		await page.goto("/shop/reviews");
		await expect(reviewSummary()).toContainText("reviews");

		const { average, total } = await readReviewSummary();
		expect(average).toBeGreaterThan(0);
		expect(average).toBeLessThanOrEqual(5);
		expect(total).toBeGreaterThan(0);
	});

	test("the rating filter narrows the list to five star reviews", async () => {
		const { total } = await readReviewSummary();
		await chooseOption(page, "All ratings", "5 stars");

		await expect
			.poll(() => distinctText(reviewCards().locator("[title]"), "title"))
			.toEqual(["5 out of 5"]);
		const filtered = await readReviewSummary();
		expect(filtered.total).toBeGreaterThan(0);
		expect(filtered.total).toBeLessThan(total);
	});

	test("deleting a review drops the admin total and the storefront count", async () => {
		await chooseOption(page, "5 stars", "All ratings");
		await page.getByRole("button", { name: "All products" }).click();
		await page.locator('input[role="combobox"]').fill(REVIEW_PRODUCT.name);
		await page.getByRole("option", { name: REVIEW_PRODUCT.name, exact: true }).click();
		await expect
			.poll(() => distinctText(reviewCards().locator("a")))
			.toEqual([REVIEW_PRODUCT.name]);

		const before = await readReviewSummary();
		expect(before.total).toBeGreaterThan(1);
		reviewBackup = await reviewsOf(await productNamed(REVIEW_PRODUCT.slug));
		const storefrontBefore = await pdpReviewCount(REVIEW_PRODUCT.slug);
		expect(storefrontBefore).toBe(before.total);

		await reviewCards().first().getByRole("button").click();
		await expect(page.getByRole("dialog")).toContainText("Delete this review");
		await confirmDialog(page, "Delete");
		await expect(page.getByText("Review deleted")).toBeVisible();

		await expect.poll(async () => (await readReviewSummary()).total).toBe(before.total - 1);
		expect(await pdpReviewCount(REVIEW_PRODUCT.slug)).toBe(storefrontBefore - 1);
	});

	test("a new percentage coupon lists as enabled", async () => {
		await page.goto("/shop/discounts");
		await page.getByRole("button", { name: "New coupon" }).click();

		const dialog = page.getByRole("dialog");
		await dialog.getByLabel("Code").fill(COUPON);
		await dialog.getByLabel("Percent off").fill("20");
		await dialog.getByRole("button", { name: "Create" }).click();
		await expect(dialog).toBeHidden();

		await expect(row(COUPON)).toContainText("20.0% off");
		await expect(row(COUPON).getByRole("switch")).toHaveAttribute("aria-checked", "true");
	});

	test("shoppers can redeem the coupon at checkout", async () => {
		await freshCheckout();
		await applyCoupon(shopperPage, COUPON);

		await expect(summaryValue(shopperPage, "Subtotal")).toHaveText("₹ 899.00");
		await expect(summaryValue(shopperPage, "Discount")).toContainText("₹ 179.80");
		await expect(summaryValue(shopperPage, "Total")).toHaveText("₹ 719.20");

		// hand the code back, otherwise the cart keeps the coupon linked and blocks its deletion
		await shopperPage.locator('[data-shop="coupon-remove"]').click();
		await expect(summaryValue(shopperPage, "Total")).toHaveText("₹ 899.00");
	});

	test("disabling the coupon makes the storefront reject the code", async () => {
		await page.goto("/shop/discounts");
		await row(COUPON).getByRole("switch").click();
		await expect(row(COUPON).getByRole("switch")).toHaveAttribute("aria-checked", "false");

		await shopperPage.goto("/checkout");
		await applyCoupon(shopperPage, COUPON);
		const banner = shopperPage.locator('[data-shop="error"]');
		await expect(banner).toBeVisible();
		await expect(banner).toContainText("not valid");
	});

	test("deleting the coupon removes the row", async () => {
		await row(COUPON).locator("td").last().getByRole("button").click();
		await page.getByRole("menuitem", { name: "Delete" }).click();
		await expect(page.getByRole("dialog")).toContainText(COUPON);
		await confirmDialog(page, "Delete");

		await expect(page.getByText("Coupon deleted")).toBeVisible();
		await expect(page.locator("tbody")).not.toContainText(COUPON);
	});

	test("the buyer shows up under customers with the order on their detail page", async () => {
		await page.goto("/shop/customers");
		await page.getByPlaceholder("Search customers").fill(buyer.full_name);
		await expect(row(buyer.full_name)).toHaveCount(1);
		expect(Number(await row(buyer.full_name).locator("td").nth(2).innerText())).toBeGreaterThanOrEqual(1);

		await row(buyer.full_name).click();
		await page.waitForURL(/\/shop\/customers\/.+/);
		await expect(page.getByRole("heading", { name: buyer.full_name })).toBeVisible();
		await expect(page.locator("tbody")).toContainText(orderId);
	});

	test("an open guest cart shows up under active carts", async ({ browser }) => {
		browserCtx = await browser.newContext();
		const cartPage = await browserCtx.newPage();
		await addToCartViaPDP(cartPage, CART_PRODUCT.slug);
		await addToCartViaPDP(cartPage, CART_PRODUCT.slug);
		await expect(cartPage.locator('[data-shop="cart-count"]').first()).toHaveText("2");

		await page.goto("/shop/carts");
		await expect(page.getByRole("radio", { name: "Active" })).toHaveAttribute(
			"aria-checked",
			"true"
		);
		await expect(row(CART_PRODUCT.pairValue)).toHaveCount(1);
		await expect(row(CART_PRODUCT.pairValue).locator("td").nth(0)).toHaveText("Guest");
		await expect(row(CART_PRODUCT.pairValue).locator("td").nth(1)).toHaveText("2");

		const openValue = page.getByText("Open cart value").locator("xpath=following-sibling::div[1]");
		await expect(openValue).not.toHaveText("₹ 0.00");

		await clearCart(cartPage);
		await cartPage.close();
	});

	test("a flat shipping rate shows up on the checkout summary", async () => {
		await page.goto("/shop/settings");
		const shipping = section("Delivery charges applied at checkout");
		await shipping.getByLabel("Flat rate").fill("49");
		await chooseOption(page, "No shipping account", await firstIncomeAccount());
		await saveSettingsSection(page, shipping);

		await freshCheckout();
		await expect(summaryValue(shopperPage, "Shipping")).toHaveText("₹ 49.00");
		await expect(summaryValue(shopperPage, "Total")).toHaveText("₹ 948.00");
	});

	test("a free shipping threshold takes the charge back off", async () => {
		await page.goto("/shop/settings");
		const shipping = section("Delivery charges applied at checkout");
		await shipping.getByLabel("Free shipping above").fill("1");
		await saveSettingsSection(page, shipping);

		await shopperPage.reload();
		await expect(summaryValue(shopperPage, "Shipping")).toHaveText("Free");
		await expect(summaryValue(shopperPage, "Total")).toHaveText("₹ 899.00");
	});

	test("clearing the shipping settings leaves checkout free", async () => {
		await page.goto("/shop/settings");
		const shipping = section("Delivery charges applied at checkout");
		await shipping.getByLabel("Flat rate").fill("0");
		await shipping.getByLabel("Free shipping above").fill("0");
		await saveSettingsSection(page, shipping);

		await shopperPage.reload();
		await expect(summaryValue(shopperPage, "Shipping")).toHaveText("Free");
		await expect(summaryValue(shopperPage, "Total")).toHaveText("₹ 899.00");
		await clearCart(shopperPage);
	});

	test("the catalog low stock threshold flows through to inventory", async () => {
		await page.goto("/shop/settings");
		await section("Pricing, stock and tax defaults").getByLabel("Low stock threshold").fill("3");
		await saveSettingsSection(page, section("Pricing, stock and tax defaults"));

		await page.goto("/shop/inventory");
		await expect(thresholdTile()).toHaveText("3");

		await page.goto("/shop/settings");
		await section("Pricing, stock and tax defaults").getByLabel("Low stock threshold").fill("5");
		await saveSettingsSection(page, section("Pricing, stock and tax defaults"));

		await page.goto("/shop/inventory");
		await expect(thresholdTile()).toHaveText("5");
	});
});
