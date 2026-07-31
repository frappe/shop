import { expect, test } from "@playwright/test";

import { loginViaApi } from "./personas/helpers";

test.describe("walkthrough launcher", () => {
	test.beforeEach(async ({ page }) => {
		await loginViaApi(page, "Administrator", "admin");
	});

	test("lists every persona in its group", async ({ page }) => {
		await page.goto("/shop/walkthroughs");
		await expect(page.getByText("Shopping flows")).toBeVisible();
		await expect(page.getByText("Store management flows")).toBeVisible();
		for (const title of [
			"Casual guest",
			"Returning customer",
			"Deal hunter",
			"Indecisive shopper",
			"Mobile shopper",
			"Store owner",
			"Operations manager",
		]) {
			await expect(page.getByText(title, { exact: true })).toBeVisible();
		}
	});

	test("preparing a persona seeds state and opens the guide", async ({ page }) => {
		await page.goto("/shop/walkthroughs");
		await page.getByText("Returning customer", { exact: true }).click();
		await expect(page.getByText("Set up for you just now")).toBeVisible({ timeout: 30000 });
		await expect(page.getByText("walkthrough-shopper@example.test").first()).toBeVisible();
		await expect(page.getByText("Steps", { exact: true })).toBeVisible();
		await expect(page.getByRole("button", { name: "Open storefront" })).toBeVisible();
		await expect(page.getByRole("button", { name: "Prepare again" })).toBeVisible();
		await expect(page.getByRole("checkbox").first()).toBeVisible();
	});
});
