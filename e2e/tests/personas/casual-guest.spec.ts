import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import {
	drawer,
	expectDrawerOpen,
	fillCheckout,
	formatINR,
	parseMoney,
	submitCheckout,
	uniqueBuyer,
} from "./helpers";

test.describe.configure({ mode: "serial" });

test.describe("Guest browser who buys with COD", () => {
	let context: BrowserContext;
	let page: Page;
	const buyer = uniqueBuyer("casual-guest");
	let productName = "";
	let unitPrice = 0;
	let confirmationUrl = "";

	test.beforeAll(async ({ browser }) => {
		context = await browser.newContext();
		page = await context.newPage();
	});

	test.afterAll(async () => {
		await context?.close();
	});

	test("browses from home into a collection", async () => {
		await page.goto("/");
		await page.locator('a[href="/collection/apparel"]').first().click();
		await page.waitForURL(/\/collection\/apparel/);
		await expect(page.locator('a[href*="/product/"]').first()).toBeVisible();
	});

	test("opens a product from the collection grid", async () => {
		const card = page.locator('a[href*="/product/crew-neck-t-shirt"]').first();
		await expect(card).toBeVisible();
		await card.click();
		await page.waitForURL(/\/product\/crew-neck-t-shirt/);
		productName = "Crew Neck T-Shirt";
		await expect(page.locator("body")).toContainText(productName);
		unitPrice = parseMoney(await page.locator('[data-shop="pdp-price"]').innerText());
		expect(unitPrice).toBeGreaterThan(0);
	});

	test("adds to cart and the drawer opens with item and subtotal", async () => {
		await page.locator('[data-shop="add-to-cart"]').click();
		await expectDrawerOpen(page);
		await expect(drawer(page).locator(".drawer-item", { hasText: productName })).toBeVisible();
		await expect(drawer(page).locator('[data-shop="drawer-total"]')).toHaveText(
			formatINR(unitPrice)
		);
	});

	test("closes the drawer via the backdrop", async () => {
		await page
			.locator('[data-shop="drawer-backdrop"]')
			.click({ position: { x: 10, y: 300 } });
		await expect(drawer(page)).toHaveAttribute("data-open", "false");
	});

	test("cart survives a page reload", async () => {
		await page.reload();
		await expect(page.locator('[data-shop="cart-count"]').first()).toHaveText("1");
	});

	test("bumps quantity on the cart page", async () => {
		await page.goto("/cart");
		await expect(page.locator("body")).toContainText(productName);
		await page.locator('[data-shop="qty-inc"]').first().click();
		await expect(page.locator('[data-shop="cart-count"]').first()).toHaveText("2");
	});

	test("checks out with COD and lands on the confirmation page", async () => {
		await page.goto("/checkout");
		await expect(page.locator("body")).toContainText(productName);
		await fillCheckout(page, buyer);
		await submitCheckout(page, "cod");
		await page.waitForURL(/order-confirmation/);
		confirmationUrl = page.url();
		await expect(page.locator("body")).toContainText("Thank you for your order!");
		await expect(page.locator("body")).toContainText(productName);
		await expect(page.locator("body")).toContainText(formatINR(unitPrice * 2));
	});

	test("a tampered confirmation token does not leak order details", async () => {
		const tampered = confirmationUrl.replace(/token=[^&]+/, "token=wrong");
		await page.goto(tampered);
		await expect(page.locator("body")).not.toContainText(productName);
		await expect(page.locator("body")).not.toContainText(formatINR(unitPrice * 2));

		const orderId = confirmationUrl.match(/order-confirmation\/([^?]+)/)?.[1];
		const api = await page.request.get(
			`/api/method/shop.storefront.orders.get_order_summary?name=${orderId}&token=wrong`
		);
		expect(api.ok()).toBeFalsy();
	});
});
