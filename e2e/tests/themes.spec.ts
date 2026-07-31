import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import { adminApi, confirmDialog, loginViaApi, type AdminApi } from "./personas/helpers";

test.describe.configure({ mode: "serial" });

interface Theme {
	group: string;
	title: string;
	active: boolean;
}

test.describe("Storefront theme picker", () => {
	let api: AdminApi;
	let admin: BrowserContext;
	let page: Page;
	let shopper: BrowserContext;
	let shopperPage: Page;
	let live: Theme;
	let other: Theme;

	test.beforeAll(async ({ browser }) => {
		api = await adminApi();
		const themes = await api.call<Theme[]>("shop.themes.list_themes");
		expect(themes.length, "at least two themes to switch between").toBeGreaterThan(1);
		live = themes.find((theme) => theme.active) || themes[0];
		other = themes.find((theme) => theme.group !== live.group)!;
		admin = await browser.newContext();
		page = await admin.newPage();
		await loginViaApi(page, "Administrator", "admin");
		shopper = await browser.newContext();
		shopperPage = await shopper.newPage();
	});

	test.afterAll(async () => {
		if (live) await api.call("shop.themes.apply_theme", { group: live.group });
		await api?.dispose();
		await admin?.close();
		await shopper?.close();
	});

	function card(title: string) {
		return page.locator("div").filter({ hasText: new RegExp(`^${title}`) }).last();
	}

	async function switchTheme(to: Theme) {
		await page.getByRole("button", { name: "Apply" }).first().click();
		await confirmDialog(page, "Switch theme");
		await expect(page.getByText("is live on your storefront").first()).toBeVisible({
			timeout: 20000,
		});
		expect((await api.getSettings()).active_theme).toBe(to.group);

		const response = await shopperPage.goto("/products");
		expect(response?.status()).toBe(200);
		await expect(shopperPage.locator("body")).toContainText("Ceramic Mug");
	}

	test("settings lists every installed theme and marks the active one", async () => {
		await page.goto("/shop/settings");
		await expect(page.getByText(live.title, { exact: true })).toBeVisible();
		await expect(page.getByText(other.title, { exact: true })).toBeVisible();
		await expect(card(live.title).getByText("Active")).toBeVisible();
	});

	test("applying a theme rebuilds the storefront without taking it down", async () => {
		await switchTheme(other);
	});

	test("switching back restores the previous theme", async () => {
		await page.reload();
		await expect(card(other.title).getByText("Active")).toBeVisible();
		await switchTheme(live);
	});
});
