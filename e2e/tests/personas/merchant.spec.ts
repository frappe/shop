import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import {
	adminApi,
	closeDrawer,
	expectDrawerOpen,
	fillCheckout,
	loginViaApi,
	saveSettingsSection,
	submitCheckout,
	uniqueBuyer,
	type AdminApi,
} from "./helpers";

test.describe.configure({ mode: "serial" });

test.describe("Store owner end to end", () => {
	const ts = Date.now();
	const ITEM_CODE = `MERCH-TEST-${ts}`;
	const PRODUCT_NAME = "Merch Test Cap";
	let api: AdminApi;
	let admin: BrowserContext;
	let page: Page;
	let shopper: BrowserContext;
	let shopperPage: Page;
	let settings: Record<string, unknown>;
	let orderId = "";

	function storeSection() {
		return page.locator("section", { hasText: "How your store shows up to customers" });
	}

	async function deleteSeededItem() {
		const entries = await api.call<{ parent: string }[]>("frappe.client.get_list", {
			doctype: "Stock Entry Detail",
			filters: { item_code: ITEM_CODE },
			fields: ["parent"],
			parent: "Stock Entry",
			limit_page_length: 0,
		});
		for (const entry of new Set(entries.map((row) => row.parent))) {
			await api.call("frappe.client.cancel", { doctype: "Stock Entry", name: entry }).catch(() => {});
			await api.call("frappe.client.delete", { doctype: "Stock Entry", name: entry }).catch(() => {});
		}
		for (const doctype of ["Item Price", "Bin", "Item"]) {
			const filters = doctype === "Item" ? { name: ITEM_CODE } : { item_code: ITEM_CODE };
			const rows = await api.call<{ name: string }[]>("frappe.client.get_list", {
				doctype,
				filters,
				limit_page_length: 0,
			});
			for (const row of rows)
				await api.call("frappe.client.delete", { doctype, name: row.name }).catch(() => {});
		}
	}

	async function deleteMerchProducts() {
		const products = await api.call<{ name: string }[]>("frappe.client.get_list", {
			doctype: "Shop Product",
			filters: { product_name: PRODUCT_NAME },
		});
		for (const product of products) {
			const cartRows = await api.call<{ parent: string }[]>("frappe.client.get_list", {
				doctype: "Shop Cart Item",
				filters: { shop_product: product.name },
				fields: ["parent"],
				parent: "Shop Cart",
			});
			for (const row of new Set(cartRows.map((cartRow) => cartRow.parent)))
				await api.call("frappe.client.delete", { doctype: "Shop Cart", name: row });
			await api.call("frappe.client.delete", { doctype: "Shop Product", name: product.name });
		}
	}

	test.beforeAll(async ({ browser }) => {
		api = await adminApi();
		settings = await api.getSettings();
		await deleteMerchProducts();
		await api.setSettings({ onboarding_complete: 0 });

		admin = await browser.newContext();
		page = await admin.newPage();
		await loginViaApi(page, "Administrator", "admin");

		shopper = await browser.newContext();
		shopperPage = await shopper.newPage();
	});

	test.afterAll(async () => {
		try {
			await api.setSettings({
				store_name: settings?.store_name || "Frappe Shop",
				enable_cod: 1,
				onboarding_complete: 1,
			});
			await deleteMerchProducts();
			await deleteSeededItem();
		} finally {
			await api?.dispose();
			await admin?.close();
			await shopper?.close();
		}
	});

	test("incomplete onboarding redirects the SPA to the wizard", async () => {
		await page.goto("/shop");
		await page.waitForURL(/\/shop\/onboarding/);
		await expect(page.getByText("First, let's name your store")).toBeVisible();
	});

	test("completes the three onboarding steps without sample data", async () => {
		const storeName = page.getByLabel("Store name");
		await expect(storeName).toHaveValue(/./);
		await page.getByRole("button", { name: "Continue" }).click();

		await expect(page.getByText("Add your first products")).toBeVisible();
		const sampleToggle = page.getByRole("switch");
		if ((await sampleToggle.getAttribute("aria-checked")) === "true") await sampleToggle.click();
		await expect(sampleToggle).toHaveAttribute("aria-checked", "false");
		await page.getByRole("button", { name: "Continue" }).click();

		await expect(page.getByText("Set up payments")).toBeVisible();
		const codToggle = page.getByRole("switch");
		if ((await codToggle.getAttribute("aria-checked")) === "false") await codToggle.click();
		await page.getByRole("button", { name: "Finish" }).click();

		await page.waitForURL((url) => !url.pathname.includes("onboarding"));
		await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
		await expect(page.getByRole("heading", { name: "Needs attention" })).toBeVisible();
		await expect(page.getByRole("heading", { name: "Recent orders" })).toBeVisible();
	});

	test("seeds a sellable item with price and stock via the API", async () => {
		await api.call("frappe.client.insert", {
			doc: {
				doctype: "Item",
				item_code: ITEM_CODE,
				item_name: ITEM_CODE,
				item_group: "Products",
				stock_uom: "Nos",
				is_stock_item: 1,
			},
		});
		await api.call("frappe.client.insert", {
			doc: {
				doctype: "Item Price",
				price_list: "Standard Selling",
				item_code: ITEM_CODE,
				price_list_rate: 777,
			},
		});
		const stockEntry = await api.call<Record<string, unknown>>("frappe.client.insert", {
			doc: {
				doctype: "Stock Entry",
				stock_entry_type: "Material Receipt",
				company: settings.company,
				items: [
					{
						item_code: ITEM_CODE,
						qty: 5,
						t_warehouse: settings.default_warehouse,
						basic_rate: 300,
					},
				],
			},
		});
		await api.call("frappe.client.submit", { doc: stockEntry });
	});

	test("publishes the seeded item through Link existing item", async () => {
		await page.goto("/shop/products");
		await page.getByRole("link", { name: "Link existing item" }).click();
		await page.waitForURL(/\/shop\/products\/new/);

		await page.getByRole("button", { name: "Search items by name or code" }).click();
		await page.locator('input[role="combobox"]').fill(ITEM_CODE);
		await page.getByRole("option", { name: ITEM_CODE }).click();

		await page.getByLabel("Product name").fill(PRODUCT_NAME);
		await expect(page.getByRole("switch", { name: "Published" })).toHaveAttribute("aria-checked", "true");
		await page.getByRole("button", { name: "Create" }).click();
		await page.waitForURL(/\/shop\/products\/[^/]+$/, { timeout: 20000 });

		await page.goto("/shop/products");
		await expect(page.locator("table")).toContainText(PRODUCT_NAME);
	});

	test("the storefront lists the new product", async () => {
		await shopperPage.goto("/products?search=Merch");
		await expect(
			shopperPage.locator('a[href*="/product/merch-test-cap"]').first()
		).toBeVisible();
	});

	test("a fresh PDP has no reviews summary but offers the review form", async () => {
		await shopperPage.goto("/product/merch-test-cap");
		await expect(shopperPage.locator("body")).toContainText(PRODUCT_NAME);
		await expect(shopperPage.locator("body")).toContainText("₹ 777.00");
		await expect(shopperPage.locator('a[href="#reviews"]')).toHaveCount(0);
		await expect(shopperPage.locator('[data-shop="review-form"]')).toBeAttached();
		await expect(shopperPage.locator('[data-shop="review-signin"]')).toBeVisible();
	});

	test("a guest buys the new product with COD", async () => {
		await shopperPage.locator('[data-shop="add-to-cart"]').click();
		await expectDrawerOpen(shopperPage);
		await closeDrawer(shopperPage);
		await shopperPage.goto("/checkout");
		await fillCheckout(shopperPage, uniqueBuyer("merch-buyer"));
		await submitCheckout(shopperPage, "cod");
		await shopperPage.waitForURL(/order-confirmation/);
		orderId = shopperPage.url().match(/order-confirmation\/([^?]+)/)?.[1] || "";
		expect(orderId).toBeTruthy();
	});

	test("the order shows up first in the SPA and can be cancelled", async () => {
		await page.goto("/shop/orders");
		await expect(page.locator("tbody tr").first()).toContainText(orderId);
		await page.locator("tbody tr").first().click();
		await page.waitForURL(new RegExp(`/shop/orders/${orderId}`));

		await page.getByRole("button", { name: "Cancel", exact: true }).click();
		const dialog = page.getByRole("dialog");
		await expect(dialog.getByText("This will cancel")).toBeVisible();
		await dialog.getByRole("button", { name: "Cancel order" }).click();
		await expect(page.getByText("Cancelled").first()).toBeVisible();
	});

	test("renaming the store updates the storefront", async () => {
		await page.goto("/shop/settings");
		const storeName = page.getByLabel("Store name");
		await expect(storeName).toHaveValue(/./);
		await storeName.fill("Persona Test Store");
		await saveSettingsSection(page, storeSection());

		await shopperPage.goto("/");
		await expect(shopperPage.locator("body")).toContainText("Persona Test Store");
	});

	test("disabling COD leaves only online payment at checkout", async () => {
		const payments = page.locator("section", { hasText: "Choose how customers pay at checkout" });
		const codToggle = payments.getByRole("switch", { name: "Cash on Delivery" });
		await expect(codToggle).toHaveAttribute("aria-checked", "true");
		await codToggle.click();
		await saveSettingsSection(page, payments);

		await shopperPage.request.post("/api/method/shop.storefront.cart.add_item", {
			data: { item_code: "SHOP-DEMO-003" },
		});
		await shopperPage.goto("/checkout");
		await expect(shopperPage.getByText("Pay Online")).toBeVisible();
		await expect(shopperPage.getByText("Cash on Delivery")).toHaveCount(0);
	});

	test("restores the store settings", async () => {
		await api.setSettings({
			store_name: settings?.store_name || "Frappe Shop",
			enable_cod: 1,
			onboarding_complete: 1,
		});
		await shopperPage.goto("/checkout");
		await expect(shopperPage.getByText("Cash on Delivery")).toBeVisible();
		await shopperPage.goto("/");
		await expect(shopperPage.locator("body")).toContainText(
			String(settings?.store_name || "Frappe Shop")
		);
	});
});
