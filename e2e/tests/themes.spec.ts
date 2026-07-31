import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import { adminApi, confirmDialog, loginViaApi, type AdminApi } from "./personas/helpers";

test.describe.configure({ mode: "serial" });

test.describe("Storefront theme picker", () => {
	let api: AdminApi;
	let admin: BrowserContext;
	let page: Page;
	let shopper: BrowserContext;
	let shopperPage: Page;
	let original = "";

	test.beforeAll(async ({ browser }) => {
		api = await adminApi();
		original = ((await api.getSettings()).active_theme as string) || "frappe";
		admin = await browser.newContext();
		page = await admin.newPage();
		await loginViaApi(page, "Administrator", "admin");
		shopper = await browser.newContext();
		shopperPage = await shopper.newPage();
	});

	test.afterAll(async () => {
		if (original) await api.call("shop.themes.apply_theme", { group: original });
		await api?.dispose();
		await admin?.close();
		await shopper?.close();
	});

	function card(title: string) {
		return page.locator("div").filter({ hasText: new RegExp(`^${title}`) }).last();
	}

	async function expectStorefrontHealthy() {
		const response = await shopperPage.goto("/products");
		expect(response?.status()).toBe(200);
		await expect(shopperPage.locator("body")).toContainText("Ceramic Mug");
	}

	test("settings lists every installed theme and marks the active one", async () => {
		await page.goto("/shop/settings");
		await expect(page.getByText("Frappe", { exact: true })).toBeVisible();
		await expect(page.getByText("Dot", { exact: true })).toBeVisible();
		await expect(card("Frappe").getByText("Active")).toBeVisible();
	});

	test("applying a theme rebuilds the storefront without taking it down", async () => {
		await page.getByRole("button", { name: "Apply" }).first().click();
		await confirmDialog(page, "Switch theme");
		await expect(page.getByText("is live on your storefront").first()).toBeVisible({
			timeout: 20000,
		});
		expect((await api.getSettings()).active_theme).toBe("dot");
		await expectStorefrontHealthy();
	});

	test("switching back restores the previous theme", async () => {
		await page.reload();
		await expect(card("Dot").getByText("Active")).toBeVisible();
		await page.getByRole("button", { name: "Apply" }).first().click();
		await confirmDialog(page, "Switch theme");
		await expect(page.getByText("is live on your storefront").first()).toBeVisible({
			timeout: 20000,
		});
		expect((await api.getSettings()).active_theme).toBe("frappe");
		await expectStorefrontHealthy();
	});
});
