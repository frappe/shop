import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import {
	adminApi,
	addToCartViaPDP,
	closeDrawer,
	drawer,
	expectDrawerOpen,
	fillCheckout,
	loginUI,
	submitCheckout,
	uniqueBuyer,
	type AdminApi,
} from "./helpers";

test.describe.configure({ mode: "serial" });

test.describe("Registered customer with cart merge and verified review", () => {
	// password strength validation rejects simple passwords like "meera1234"
	const PASSWORD = "meera-Kip4-voyage";
	const EMAIL = `meera-${Date.now()}@example.test`;
	let api: AdminApi;
	let context: BrowserContext;
	let page: Page;
	let orderId = "";

	test.beforeAll(async ({ browser }) => {
		api = await adminApi();
		await api.call("frappe.client.insert", {
			doc: {
				doctype: "User",
				email: EMAIL,
				first_name: "Meera",
				send_welcome_email: 0,
				new_password: PASSWORD,
				user_type: "Website User",
			},
		});
		context = await browser.newContext();
		page = await context.newPage();
	});

	test.afterAll(async () => {
		try {
			const reviews = await api.call<{ name: string }[]>("frappe.client.get_list", {
				doctype: "Shop Review",
				filters: { user: EMAIL },
			});
			for (const review of reviews)
				await api.call("frappe.client.delete", { doctype: "Shop Review", name: review.name });
		} catch (error) {
			// best-effort cleanup
		}
		await api?.dispose();
		await context?.close();
	});

	test("adds a mug to the cart as a guest", async () => {
		await addToCartViaPDP(page, "ceramic-mug");
		await expect(page.locator('[data-shop="cart-count"]').first()).toHaveText("1");
	});

	test("logs in via the login page and keeps shopping", async () => {
		await loginUI(page, EMAIL, PASSWORD, "/product/canvas-tote-bag");
		await expect(page).toHaveURL(/\/product\/canvas-tote-bag/);
		await page.locator('[data-shop="add-to-cart"]').click();
		await expectDrawerOpen(page);
		await expect(drawer(page).locator(".drawer-item", { hasText: "Canvas Tote Bag" })).toBeVisible();
		await closeDrawer(page);
	});

	test("guest cart was merged into the logged-in session", async () => {
		await page.goto("/cart");
		await expect(page.locator("body")).toContainText("Ceramic Mug");
		await expect(page.locator("body")).toContainText("Canvas Tote Bag");
	});

	test("checks out with COD using her own email", async () => {
		await page.goto("/checkout");
		const buyer = { ...uniqueBuyer("meera"), email: EMAIL, full_name: "Meera" };
		await fillCheckout(page, buyer);
		await submitCheckout(page, "cod");
		await page.waitForURL(/order-confirmation/);
		orderId = page.url().match(/order-confirmation\/([^?]+)/)?.[1] || "";
		expect(orderId).toBeTruthy();
	});

	test("stays signed in through checkout and sees her order history", async () => {
		await page.goto("/account/orders");
		await expect(page.locator("body")).toContainText(orderId);
	});

	test("writes a review that is tagged as a verified purchase", async () => {
		await page.goto("/product/ceramic-mug");
		await expect(page.locator('[data-shop="review-signin"]')).toBeHidden();
		const form = page.locator('[data-shop="review-form"]');
		await expect(form).toBeVisible();

		await page.locator('[data-shop="rating-star"][data-value="4"]').click();
		await expect(page.locator('[data-shop="rating-star"][data-value="4"]')).toHaveAttribute(
			"data-selected",
			"true"
		);
		await form.locator('[name="title"]').fill("Solid everyday mug");
		await form.locator('[name="review"]').fill("Holds heat well and looks great on my desk.");
		await form.locator('[type="submit"]').click();

		const reviewerName = page.locator("span", { hasText: /^Meera$/ }).first();
		await expect(reviewerName).toBeVisible({ timeout: 10000 });
		await expect(reviewerName.locator("xpath=ancestor::div[2]")).toContainText("Verified buyer");
	});
});
