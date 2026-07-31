import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import { drawer, expectDrawerOpen, fillCheckout, submitCheckout, uniqueBuyer } from "./helpers";

const VIEWPORT = { width: 390, height: 844 };

test.describe.configure({ mode: "serial" });

test.describe("iPhone-class shopper", () => {
	let context: BrowserContext;
	let page: Page;
	const buyer = uniqueBuyer("mobile");

	test.beforeAll(async ({ browser }) => {
		context = await browser.newContext({ viewport: VIEWPORT });
		page = await context.newPage();
	});

	test.afterAll(async () => {
		await context?.close();
	});

	test("home renders without horizontal scroll", async () => {
		await page.goto("/");
		const scrollWidth = await page.evaluate(
			() => document.scrollingElement!.scrollWidth
		);
		expect(scrollWidth).toBeLessThanOrEqual(VIEWPORT.width + 1);
	});

	test("products grid is a usable two-column layout", async () => {
		await page.goto("/products");
		const cards = page.locator('a[href^="/product/"]');
		await expect(cards.first()).toBeVisible();
		const first = await cards.nth(0).boundingBox();
		const second = await cards.nth(1).boundingBox();
		expect(first && second).toBeTruthy();
		expect(Math.abs(first!.y - second!.y)).toBeLessThan(10);
		expect(second!.x).toBeGreaterThan(first!.x);
		expect(second!.x + second!.width).toBeLessThanOrEqual(VIEWPORT.width + 1);
	});

	test("PDP shows a sticky buy bar pinned to the viewport bottom", async () => {
		await page.goto("/product/ceramic-mug");
		const bar = page.locator(".pdp-buybar");
		await expect(bar).toBeVisible();
		const box = await bar.boundingBox();
		expect(box).toBeTruthy();
		expect(Math.abs(box!.y + box!.height - VIEWPORT.height)).toBeLessThanOrEqual(2);
	});

	test("buys from the sticky bar and completes COD checkout", async () => {
		await page.locator('.pdp-buybar [data-shop="buy-now"]').click();
		await page.waitForURL(/\/checkout/);

		const form = page.locator('[data-shop="checkout-form"]');
		const formBox = await form.boundingBox();
		expect(formBox!.width).toBeLessThanOrEqual(VIEWPORT.width);

		await fillCheckout(page, buyer);
		await submitCheckout(page, "cod");
		await page.waitForURL(/order-confirmation/);
		await expect(page.locator("body")).toContainText("Ceramic Mug");
	});

	test("cart drawer fits the mobile viewport", async () => {
		await page.goto("/");
		await page.locator('[data-shop="cart-toggle"]').first().click();
		await expectDrawerOpen(page);
		const panel = drawer(page).locator(".drawer-panel");
		// each theme picks its own inset and may slide the panel in, so poll until it settles
		await expect
			.poll(async () => {
				const settling = await panel.boundingBox();
				return settling ? Math.round(settling.x + settling.width) : -1;
			})
			.toBeLessThanOrEqual(VIEWPORT.width + 1);

		const box = await panel.boundingBox();
		expect(box!.width).toBeGreaterThanOrEqual(280);
		expect(box!.width).toBeLessThanOrEqual(Math.min(420, VIEWPORT.width));
		expect(box!.x).toBeGreaterThanOrEqual(0);
	});
});
