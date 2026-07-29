import { expect, test } from "@playwright/test";

const BUYER = {
	email: `buyer-${Date.now()}@example.com`,
	full_name: "Ada Buyer",
	phone: "9876543210",
	address_line1: "42 Test Lane",
	city: "Bengaluru",
	state: "Karnataka",
	pincode: "560001",
};

test.describe("storefront", () => {
	test("home renders store and products", async ({ page }) => {
		await page.goto("/");
		await expect(page.locator("body")).toContainText("Demo Shop");
		await expect(page.locator('a[href*="/product/"]').first()).toBeVisible();
	});

	test("listing shows products and search works", async ({ page }) => {
		await page.goto("/products");
		await expect(page.locator('a[href*="/product/ceramic-mug"]').first()).toBeVisible();
		await page.goto("/products?search=mug");
		await expect(page.locator('a[href*="/product/ceramic-mug"]').first()).toBeVisible();
		await expect(page.locator('a[href*="/product/zip-hoodie"]')).toHaveCount(0);
	});

	test("filter presets narrow the listing", async ({ page }) => {
		await page.goto("/products?price=0-500");
		await expect(page.locator('a[href*="/product/enamel-pin-set"]').first()).toBeVisible();
		await expect(page.locator('a[href*="/product/ceramic-mug"]')).toHaveCount(0);
		await page.goto("/products?collection=stationery&sort=price_desc");
		await expect(page.locator('a[href*="/product/oak-desk-organizer"]').first()).toBeVisible();
		await expect(page.locator('a[href*="/product/ceramic-mug"]')).toHaveCount(0);
	});

	test("default pages render", async ({ page }) => {
		for (const path of ["/about", "/contact", "/faq"]) {
			await page.goto(path);
			await expect(page.locator("h1").first()).toBeVisible();
		}
	});

	test("full purchase flow: PDP, variant, cart, checkout, confirmation", async ({ page }) => {
		await page.goto("/product/crew-neck-t-shirt");
		await expect(page.locator("body")).toContainText("Crew Neck T-Shirt");

		const medium = page.locator('[data-shop="variant-option"][data-value="Medium"]');
		await medium.click();
		await expect(medium).toHaveAttribute("data-selected", "true");

		const buy = page.locator('[data-shop="add-to-cart"]');
		await expect(buy).toBeEnabled();
		await buy.click();
		await expect(page.locator('[data-shop="cart-count"]').first()).toHaveText("1");

		await page.goto("/cart");
		await expect(page.locator("body")).toContainText("Crew Neck T-Shirt");
		await page.locator('[data-shop="qty-inc"]').first().click();
		await page.waitForLoadState("networkidle");
		await expect(page.locator("body")).toContainText("2");

		await page.goto("/checkout");
		await page.fill('[name="email"]', BUYER.email);
		await page.fill('[name="full_name"]', BUYER.full_name);
		await page.fill('[name="phone"]', BUYER.phone);
		await page.fill('[name="address_line1"]', BUYER.address_line1);
		await page.fill('[name="city"]', BUYER.city);
		await page.fill('[name="state"]', BUYER.state);
		await page.fill('[name="pincode"]', BUYER.pincode);
		await page.locator('[data-shop="checkout-form"] [type="submit"]').click();

		await page.waitForURL(/order-confirmation/);
		await expect(page.locator("body")).toContainText("Crew Neck T-Shirt");
		const orderId = page.url().match(/order-confirmation\/([^?]+)/)?.[1];
		expect(orderId).toBeTruthy();

		const api = await page.request.get(
			`/api/method/shop.storefront.orders.get_order_summary?name=${orderId}&token=${await token(page)}`
		);
		expect(api.ok()).toBeTruthy();
	});
});

async function token(page): Promise<string> {
	const cookies = await page.context().cookies();
	return cookies.find((c) => c.name === "shop_cart_token")?.value || "";
}
