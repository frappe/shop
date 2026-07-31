import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import {
	addToCartViaPDP,
	adminApi,
	confirmDialog,
	fillCheckout,
	loginViaApi,
	submitCheckout,
	uniqueBuyer,
	type AdminApi,
} from "./helpers";

test.describe.configure({ mode: "serial" });

test.describe("Return request round trip between shopper and merchant", () => {
	const buyer = { ...uniqueBuyer("returner"), full_name: "Riya Returner" };

	let api: AdminApi;
	let shopper: BrowserContext;
	let page: Page;
	let admin: BrowserContext;
	let adminPage: Page;
	let orderId = "";
	let confirmationUrl = "";

	test.beforeAll(async ({ browser }) => {
		api = await adminApi();
		shopper = await browser.newContext();
		page = await shopper.newPage();
		admin = await browser.newContext();
		adminPage = await admin.newPage();
		await loginViaApi(adminPage, "Administrator", "admin");
	});

	test.afterAll(async () => {
		await api?.dispose();
		await shopper?.close();
		await admin?.close();
	});

	function requestRow() {
		return adminPage.locator("tbody tr", { hasText: orderId });
	}

	function returnsCard() {
		return page
			.locator("div")
			.filter({ has: page.getByRole("heading", { name: "Returns & replacements" }) })
			.last();
	}

	test("a guest buys a mug with cash on delivery", async () => {
		await addToCartViaPDP(page, "ceramic-mug");
		await page.goto("/checkout");
		await fillCheckout(page, buyer);
		await submitCheckout(page, "cod");
		await page.waitForURL(/order-confirmation/);
		orderId = page.url().match(/order-confirmation\/([^?]+)/)?.[1] || "";
		expect(orderId).toBeTruthy();
		confirmationUrl = page.url();
	});

	test("returns are not offered before the order ships", async () => {
		await expect(page.getByText("Returns & replacements")).toBeHidden();
	});

	test("the merchant ships the order", async () => {
		const fulfillment = await api.call<{ name: string }>("shop.api.fulfillment.send_order", {
			order: orderId,
			provider: "manual",
		});
		await api.call("shop.api.fulfillment.mark_shipped", {
			fulfillment: fulfillment.name,
			carrier: "Delhivery",
			tracking_number: `RT-${Date.now()}`,
		});
	});

	test("the confirmation page now takes a return request", async () => {
		await page.goto(confirmationUrl);
		const form = page.locator('[data-shop="return-form"]');
		await expect(form).toBeVisible();
		await form.locator('select[name="request_type"]').selectOption("Return");
		await form.locator('[name="reason"]').fill("The rim arrived chipped");
		await form.locator('[type="submit"]').click();
		await expect(page.getByText("Return · Ceramic Mug")).toBeVisible();
		await expect(returnsCard()).toContainText("Requested");
	});

	test("the merchant approves it from the returns queue with a note", async () => {
		await adminPage.goto("/shop/returns");
		await expect(requestRow()).toContainText("Requested");
		await expect(requestRow()).toContainText("The rim arrived chipped");
		await requestRow().getByRole("button").first().click();
		await expect(adminPage.getByRole("dialog")).toContainText("Approve request");
		await adminPage.getByRole("dialog").locator("textarea").fill("Pickup scheduled for Friday");
		await confirmDialog(adminPage, "Approve");
		await expect(adminPage.getByText("Request approved").first()).toBeVisible();
		await expect(requestRow()).toContainText("Approved");
	});

	test("the shopper sees the approval and the note", async () => {
		await page.goto(confirmationUrl);
		await expect(returnsCard()).toContainText("Approved");
		await expect(returnsCard()).toContainText("Pickup scheduled for Friday");
	});

	test("completing the pickup closes the loop for both sides", async () => {
		await requestRow().getByRole("button").first().click();
		await expect(adminPage.getByRole("dialog")).toContainText("Mark completed");
		await adminPage
			.getByRole("dialog")
			.locator("textarea")
			.fill("Refund issued to the original payment method");
		await confirmDialog(adminPage, "Mark completed");
		await expect(requestRow()).toContainText("Completed");

		await page.goto(confirmationUrl);
		await expect(returnsCard()).toContainText("Completed");
		await expect(returnsCard()).toContainText("Refund issued to the original payment method");
	});
});
