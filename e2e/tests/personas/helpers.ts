import { expect, request as playwrightRequest, type Locator, type Page } from "@playwright/test";

export const BASE_URL = process.env.SHOP_BASE_URL || "http://shop.localhost:8000";

export interface AdminApi {
	call<T = unknown>(method: string, args?: Record<string, unknown>): Promise<T>;
	setSettings(values: Record<string, unknown>): Promise<void>;
	getSettings(): Promise<Record<string, unknown>>;
	dispose(): Promise<void>;
}

export async function adminApi(): Promise<AdminApi> {
	const ctx = await playwrightRequest.newContext({ baseURL: BASE_URL });
	const login = await ctx.post("/api/method/login", {
		data: { usr: "Administrator", pwd: "admin" },
	});
	expect(login.ok(), "Administrator API login").toBeTruthy();

	async function call<T>(method: string, args?: Record<string, unknown>): Promise<T> {
		const response = await ctx.post(`/api/method/${method}`, { data: args || {} });
		if (!response.ok())
			throw new Error(`${method} failed (${response.status()}): ${await response.text()}`);
		return (await response.json()).message;
	}

	return {
		call,
		async setSettings(values) {
			for (const [fieldname, value] of Object.entries(values))
				await call("frappe.client.set_value", {
					doctype: "Shop Settings",
					name: "Shop Settings",
					fieldname,
					value,
				});
		},
		getSettings: () => call("frappe.client.get", { doctype: "Shop Settings" }),
		dispose: () => ctx.dispose(),
	};
}

export function uniqueBuyer(prefix: string) {
	return {
		email: `${prefix}-${Date.now()}@example.test`,
		full_name: "Persona Shopper",
		phone: "9876543210",
		address_line1: "12 Persona Lane",
		city: "Bengaluru",
		state: "Karnataka",
		pincode: "560001",
	};
}

export type Buyer = ReturnType<typeof uniqueBuyer>;

export async function loginUI(page: Page, email: string, password: string, redirectTo: string) {
	await page.goto(`/login?redirect-to=${encodeURIComponent(redirectTo)}`);
	await page.fill("#login_email", email);
	await page.fill("#login_password", password);
	await page.locator("button.btn-login:visible").first().click();
	await page.waitForURL((url) => !url.pathname.startsWith("/login"));
	await expect
		.poll(async () => {
			const cookies = await page.context().cookies();
			return cookies.find((cookie) => cookie.name === "user_id")?.value || "Guest";
		}, { message: "user_id cookie after UI login" })
		.toBe(encodeURIComponent(email));
}

export async function loginViaApi(page: Page, usr: string, pwd: string) {
	const response = await page.request.post("/api/method/login", { data: { usr, pwd } });
	expect(response.ok(), `browser login as ${usr}`).toBeTruthy();
}

export function drawer(page: Page) {
	return page.locator('[data-shop="cart-drawer"]');
}

export async function expectDrawerOpen(page: Page) {
	await expect(drawer(page)).toHaveAttribute("data-open", "true");
}

export async function closeDrawer(page: Page) {
	await page.locator('[data-shop="drawer-close"]').click();
	await expect(drawer(page)).toHaveAttribute("data-open", "false");
}

export async function addToCartViaPDP(page: Page, slug: string, { close = true } = {}) {
	await page.goto(`/product/${slug}`);
	await page.locator('[data-shop="add-to-cart"]').click();
	await expectDrawerOpen(page);
	if (close) await closeDrawer(page);
}

export function drawerItem(page: Page, name: string) {
	return drawer(page).locator(".drawer-item", { hasText: name });
}

export async function drawerQty(page: Page, name: string): Promise<number> {
	return parseInt(await drawerItem(page, name).locator(".drawer-qty > span").innerText(), 10);
}

export async function setDrawerQty(page: Page, name: string, target: number) {
	for (;;) {
		const qty = await drawerQty(page, name);
		if (qty === target) return;
		const step = qty < target ? 1 : -1;
		await drawerItem(page, name).locator(`[data-drawer-step="${step}"]`).click();
		await expect(drawerItem(page, name).locator(".drawer-qty > span")).toHaveText(
			String(qty + step)
		);
	}
}

export function parseMoney(text: string): number {
	return parseFloat(text.replace(/[^\d.]/g, ""));
}

export function formatINR(amount: number): string {
	return `₹ ${amount.toLocaleString("en-IN", {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	})}`;
}

export async function drawerTotal(page: Page): Promise<number> {
	return parseMoney(await drawer(page).locator('[data-shop="drawer-total"]').innerText());
}

export async function fillCheckout(page: Page, buyer: Buyer) {
	await page.fill('[name="email"]', buyer.email);
	await page.fill('[name="full_name"]', buyer.full_name);
	await page.fill('[name="phone"]', buyer.phone);
	await page.fill('[name="address_line1"]', buyer.address_line1);
	await page.fill('[name="city"]', buyer.city);
	await page.fill('[name="state"]', buyer.state);
	await page.fill('[name="pincode"]', buyer.pincode);
}

export async function submitCheckout(page: Page, method: "cod" | "gateway" = "cod") {
	await page.locator(`input[name="payment_method"][value="${method}"]`).check();
	await page.locator('[data-shop="checkout-form"] [type="submit"]').click();
}

export async function placeCodOrder(page: Page, buyer: Buyer): Promise<string> {
	await page.goto("/checkout");
	await fillCheckout(page, buyer);
	await submitCheckout(page, "cod");
	await page.waitForURL(/order-confirmation/);
	return page.url().match(/order-confirmation\/([^?]+)/)?.[1] || "";
}

export async function clearCart(page: Page) {
	await page.request.post("/api/method/shop.storefront.cart.clear", { data: {} });
}

export function summaryCard(page: Page) {
	return page
		.locator("div")
		.filter({ has: page.getByRole("heading", { name: "Order summary" }) })
		.filter({ hasText: "Subtotal" })
		.last();
}

export function summaryValue(page: Page, label: string) {
	return summaryCard(page)
		.getByText(label, { exact: true })
		.locator("xpath=following-sibling::*[1]");
}

export async function applyCoupon(page: Page, code: string) {
	const form = page.locator('[data-shop="coupon-form"]');
	await form.locator('[name="code"]').fill(code);
	await form.locator('[type="submit"]').click();
}

/** frappe-ui selects are custom listboxes, so pick by the label the trigger currently shows. */
export async function chooseOption(page: Page, current: string, option: string) {
	await page.locator('[data-slot="trigger"]', { hasText: current }).first().click();
	await page.getByRole("option", { name: option, exact: true }).click();
}

/** The saved toast lingers between sections, so wait for the write itself to land. */
export async function saveSettingsSection(page: Page, section: Locator) {
	await Promise.all([
		page.waitForResponse(
			(response) => response.url().includes("save_settings") && response.status() === 200
		),
		section.getByRole("button", { name: "Save" }).click(),
	]);
	await expect(page.getByText("Settings saved").first()).toBeVisible();
}

export async function confirmDialog(page: Page, buttonLabel: string) {
	await page.getByRole("dialog").getByRole("button", { name: buttonLabel, exact: true }).click();
}
