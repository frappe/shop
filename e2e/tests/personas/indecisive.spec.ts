import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import {
	addToCartViaPDP,
	closeDrawer,
	drawer,
	drawerItem,
	drawerTotal,
	expectDrawerOpen,
	fillCheckout,
	formatINR,
	setDrawerQty,
	submitCheckout,
	uniqueBuyer,
} from "./helpers";

test.describe.configure({ mode: "serial" });

test.describe("Adds, edits, empties, then finally buys", () => {
	const MUG = "Ceramic Mug";
	const TOTE = "Canvas Tote Bag";
	const JOURNAL = "Leather Journal";
	let context: BrowserContext;
	let page: Page;
	const buyer = uniqueBuyer("indecisive");
	let mugPrice = 0;

	test.beforeAll(async ({ browser }) => {
		context = await browser.newContext();
		page = await context.newPage();
	});

	test.afterAll(async () => {
		await context?.close();
	});

	test("fills the drawer with three products", async () => {
		await addToCartViaPDP(page, "ceramic-mug");
		await addToCartViaPDP(page, "canvas-tote-bag");
		await addToCartViaPDP(page, "leather-journal", { close: false });
		await expect(drawer(page).locator(".drawer-item")).toHaveCount(3);
		mugPrice = parseFloat(
			(await drawerItem(page, MUG).locator(".drawer-rate").innerText()).replace(/[^\d.]/g, "")
		);
		expect(mugPrice).toBeGreaterThan(0);
	});

	test("edits quantities and removes items in the drawer without a reload", async () => {
		await page.evaluate(() => ((window as any).__noReloadMarker = true));

		const before = await drawerTotal(page);
		await setDrawerQty(page, MUG, 3);
		const afterBump = await drawerTotal(page);
		expect(afterBump).toBeCloseTo(before + mugPrice * 2, 1);

		await drawerItem(page, JOURNAL).locator(".drawer-remove").click();
		await expect(drawer(page).locator(".drawer-item")).toHaveCount(2);
		const afterRemove = await drawerTotal(page);
		expect(afterRemove).toBeLessThan(afterBump);

		await drawerItem(page, TOTE).locator('[data-drawer-step="-1"]').click();
		await expect(drawer(page).locator(".drawer-item")).toHaveCount(1);
		const afterZero = await drawerTotal(page);
		expect(afterZero).toBeCloseTo(mugPrice * 3, 1);

		expect(await page.evaluate(() => (window as any).__noReloadMarker)).toBe(true);
		await closeDrawer(page);
	});

	test("clears the rest from the cart page and sees the empty state", async () => {
		await page.goto("/cart");
		await expect(page.locator("body")).toContainText(MUG);
		await page.locator('[data-shop="remove"]').first().click();
		await expect(page.locator("body")).toContainText("Your cart is empty.");
		await expect(page.locator('[data-shop="cart-count"]').first()).toHaveText("0");
	});

	test("stocks up beyond the available quantity", async () => {
		await addToCartViaPDP(page, "ceramic-mug", { close: false });
		await setDrawerQty(page, MUG, 26);
		await closeDrawer(page);
	});

	test("checkout blocks the order and reports available stock", async () => {
		await page.goto("/checkout");
		await fillCheckout(page, buyer);
		await submitCheckout(page, "cod");
		const error = page.locator('[data-shop="error"]');
		await expect(error).toBeVisible();
		await expect(error).toContainText(/Only 25 .* left in stock/);
		await expect(page).toHaveURL(/\/checkout/);
	});

	test("fixes the quantity in the drawer on the checkout page and orders", async () => {
		await page.locator('[data-shop="cart-toggle"]').click();
		await expectDrawerOpen(page);
		await setDrawerQty(page, MUG, 2);
		await closeDrawer(page);

		await submitCheckout(page, "cod");
		await page.waitForURL(/order-confirmation/);
		await expect(page.locator("body")).toContainText(MUG);
		await expect(page.locator("body")).toContainText(formatINR(mugPrice * 2));
	});
});
