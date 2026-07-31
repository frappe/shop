import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import { addToCartViaPDP, fillCheckout, openFilters, submitCheckout, uniqueBuyer } from "./helpers";

test.describe.configure({ mode: "serial" });

test.describe("Filter-heavy bargain hunter using buy-now and gateway", () => {
	let context: BrowserContext;
	let page: Page;
	const buyer = uniqueBuyer("deal-hunter");

	test.beforeAll(async ({ browser }) => {
		context = await browser.newContext();
		page = await context.newPage();
	});

	test.afterAll(async () => {
		await context?.close();
	});

	test("price chip narrows the listing to the only sub-500 product", async () => {
		await page.goto("/products");
		await openFilters(page);
		await page.getByRole("link", { name: "Under ₹ 500" }).click();
		await page.waitForURL(/price=0-500/);
		await expect(page.locator('a[href*="/product/enamel-pin-set"]').first()).toBeVisible();
		await expect(
			page.locator('a[href^="/product/"]:not([href*="enamel-pin-set"])')
		).toHaveCount(0);
	});

	test("availability chip hides the out-of-stock print", async () => {
		await page.goto("/products");
		await openFilters(page);
		await page.getByRole("link", { name: "In stock", exact: true }).click();
		await page.waitForURL(/stock=in/);
		await expect(page.locator('a[href*="/product/botanical-art-print"]')).toHaveCount(0);
		await expect(page.locator('a[href*="/product/ceramic-mug"]').first()).toBeVisible();
		await expect(page.locator('a[href*="/product/wool-throw-blanket"]').first()).toBeVisible();
	});

	test("applied filters stay visible once the panel is collapsed", async () => {
		await page.goto("/products?collection=stationery&stock=in");
		const toggle = page.locator('[data-shop="filter-toggle"]');
		// themes without a collapsible panel always show what is applied
		if (!(await toggle.count())) test.skip();
		const panel = page.locator('[data-shop="filter-panel"]');
		await expect(panel).toHaveAttribute("data-open", "true");
		await toggle.click();
		await expect(panel).toBeHidden();
		await expect(toggle).toContainText("2");
		await page.goto("/products");
		await expect(toggle).not.toContainText("2");
	});

	test("sorting by price puts the most expensive product first", async () => {
		await page.goto("/products");
		await openFilters(page);
		await page.getByRole("link", { name: "Price, high to low" }).click();
		await page.waitForURL(/sort=price_desc/);
		await expect(page.locator('a[href^="/product/"]').first()).toHaveAttribute(
			"href",
			/wool-throw-blanket/
		);
	});

	test("search finds only the hoodie", async () => {
		await page.locator('[data-shop="search-form"] [name="search"]').fill("hoodie");
		await page.locator('[data-shop="search-form"] [name="search"]').press("Enter");
		await page.waitForURL(/search=hoodie/);
		await expect(page.locator('a[href*="/product/zip-hoodie"]').first()).toBeVisible();
		await expect(page.locator('a[href^="/product/"]:not([href*="zip-hoodie"])')).toHaveCount(0);
	});

	test("out-of-stock variant disables both purchase buttons", async () => {
		await page.locator('a[href*="/product/zip-hoodie"]').first().click();
		await page.waitForURL(/\/product\/zip-hoodie/);

		await page.locator('[data-shop="variant-option"][data-value="Large"]').click();
		await page.locator('[data-shop="variant-option"][data-value="Olive"]').click();

		const addToCart = page.locator('[data-shop="add-to-cart"]');
		await expect(addToCart).toBeDisabled();
		await expect(addToCart).toHaveText("Out of stock");
		for (const buyNow of await page.locator('[data-shop="buy-now"]').all()) {
			await expect(buyNow).toBeDisabled();
			await expect(buyNow).toHaveText("Out of stock");
		}
	});

	test("switching to an in-stock colour re-enables buy now", async () => {
		await page.locator('[data-shop="variant-option"][data-value="Charcoal"]').click();
		const buyNow = page.locator('[data-shop="buy-now"]').first();
		await expect(buyNow).toBeEnabled();
		await expect(buyNow).toHaveText("Buy now");
		await buyNow.click();
		await page.waitForURL(/\/checkout/);
		await expect(page.locator("body")).toContainText("Zip Hoodie");
	});

	test("paying online hands off to the razorpay checkout page", async () => {
		await expect(page.getByText("Pay Online")).toBeVisible();
		await fillCheckout(page, buyer);
		await submitCheckout(page, "gateway");
		await page.waitForURL(/razorpay_checkout/);
		expect(page.url()).toContain("razorpay_checkout");
	});

	const couponBuyer = uniqueBuyer("deal-hunter-coupon");

	const summaryCard = () =>
		page
			.locator("div")
			.filter({ has: page.getByRole("heading", { name: "Order summary" }) })
			.filter({ hasText: "Subtotal" })
			.last();

	const summaryValue = (label: string) =>
		summaryCard().getByText(label, { exact: true }).locator("xpath=following-sibling::*[1]");

	async function applyCoupon(code: string) {
		const form = page.locator('[data-shop="coupon-form"]');
		await form.locator('[name="code"]').fill(code);
		await form.locator('[type="submit"]').click();
	}

	test("applying WELCOME10 discounts the order summary", async () => {
		await page.request.post("/api/method/shop.storefront.cart.clear", { data: {} });
		await addToCartViaPDP(page, "ceramic-mug");
		await page.goto("/checkout");
		await applyCoupon("WELCOME10");
		await expect(summaryCard().getByText("WELCOME10")).toBeVisible();
		await expect(summaryValue("Subtotal")).toHaveText("₹ 599.00");
		await expect(summaryValue("Discount")).toContainText("₹ 59.90");
		await expect(summaryValue("Total")).toHaveText("₹ 539.10");
	});

	test("a bogus code trips the error banner", async () => {
		await applyCoupon("NOTREAL");
		const banner = page.locator('[data-shop="error"]');
		await expect(banner).toBeVisible();
		await expect(banner).toContainText("not valid");
	});

	test("removing the coupon restores the full total", async () => {
		await page.locator('[data-shop="coupon-remove"]').click();
		await expect(summaryValue("Total")).toHaveText("₹ 599.00");
		await expect(summaryCard().getByText("Discount", { exact: true })).toHaveCount(0);
	});

	test("the discount carries through COD checkout to the confirmation", async () => {
		await applyCoupon("WELCOME10");
		await expect(summaryCard().getByText("WELCOME10")).toBeVisible();
		await fillCheckout(page, couponBuyer);
		await submitCheckout(page, "cod");
		await page.waitForURL(/order-confirmation/);
		await expect(summaryValue("Subtotal")).toHaveText("₹ 599.00");
		await expect(summaryValue("Discount")).toContainText("₹ 59.90");
		await expect(summaryValue("Total")).toHaveText("₹ 539.10");
	});
});
