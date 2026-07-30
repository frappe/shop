import { expect, test, type Page } from "@playwright/test";

const SHOTS =
	"/private/tmp/claude-501/-Users-sps-work-benches-develop-apps-builder/2199826f-0d58-4691-92d1-640fafee7e04/scratchpad";
const TS = Date.now();
const NEW_PRODUCT = `UI Variant Test ${TS}`;
const SIMPLE_PRODUCT = `UI Variant Test ${TS} Simple`;

test.use({ viewport: { width: 1440, height: 900 } });
test.describe.configure({ mode: "serial", timeout: 120000 });

async function login(page: Page) {
	const res = await page.request.post("/api/method/login", {
		data: { usr: "Administrator", pwd: "admin" },
	});
	expect(res.ok()).toBeTruthy();
	await page.request.post("/api/method/frappe.client.set_value", {
		data: {
			doctype: "Shop Settings",
			name: "Shop Settings",
			fieldname: "onboarding_complete",
			value: 1,
		},
	});
}

async function openProduct(page: Page, search: string, name: string) {
	await page.goto(`/shop/products?search=${encodeURIComponent(search)}`);
	const row = page.locator("tr", { hasText: name }).first();
	await row.waitFor();
	await row.locator("td").nth(1).click();
	const dialog = page.getByRole("dialog");
	await expect(dialog.getByRole("heading", { name: "Variants" })).toBeVisible();
	return dialog;
}

async function scrollToVariants(dialog: ReturnType<Page["getByRole"]>) {
	await dialog
		.locator("section")
		.filter({ hasText: "Variants" })
		.last()
		.evaluate((el) => el.scrollIntoView({ block: "end" }));
	await new Promise((resolve) => setTimeout(resolve, 150));
}

async function closeDialog(page: Page) {
	await page.keyboard.press("Escape");
	await expect(page.getByRole("dialog")).toHaveCount(0);
}

test("a. existing variant product", async ({ page }) => {
	await login(page);
	await page.goto("/shop/products");
	await page.locator("tr", { hasText: "Crew Neck T-Shirt" }).first().waitFor();
	await page.screenshot({ path: `${SHOTS}/e-products-list.png` });
	let dialog = await openProduct(page, "Crew", "Crew Neck T-Shirt");

	const rows = dialog.locator("tbody tr");
	await expect(rows).toHaveCount(6);
	await expect(dialog.getByText("Small / Black")).toBeVisible();
	await scrollToVariants(dialog);
	await page.screenshot({ path: `${SHOTS}/a-variants-panel.png` });

	const row = dialog.locator("tr", { hasText: "SHOP-DEMO-001-S-BLA" });
	const price = row.locator("input").first();
	await price.fill("949");
	await price.press("Enter");
	await expect(page.getByText("Price set to 949")).toBeVisible();

	const availability = row.getByRole("switch");
	await availability.click();
	await expect(page.getByText("Variant is hidden")).toBeVisible();
	await availability.click();
	await expect(page.getByText("Variant is available")).toBeVisible();
	await expect(availability).toHaveAttribute("aria-checked", "true");

	await closeDialog(page);
	dialog = await openProduct(page, "Crew", "Crew Neck T-Shirt");
	const reopened = dialog.locator("tr", { hasText: "SHOP-DEMO-001-S-BLA" });
	await expect(reopened.locator("input").first()).toHaveValue("949");

	// restore the demo price
	await reopened.locator("input").first().fill("899");
	await reopened.locator("input").first().press("Enter");
	await expect(page.getByText("Price set to 899")).toBeVisible();
	await closeDialog(page);
});

test("b. create a product with options", async ({ page }) => {
	await login(page);
	await page.goto("/shop/products");
	await page.getByRole("button", { name: "Add product" }).first().click();
	const dialog = page.getByRole("dialog");
	await dialog.getByLabel("Product name").fill(NEW_PRODUCT);

	const optionsSection = dialog
		.locator("section")
		.filter({ has: page.getByRole("heading", { name: "Options" }) });
	await optionsSection.getByRole("switch").click();

	const inputs = optionsSection.locator("input");
	await inputs.nth(0).fill("Size");
	await inputs.nth(1).fill("Small");
	await inputs.nth(1).press("Enter");
	await inputs.nth(1).fill("Large");
	await inputs.nth(1).press("Enter");

	await optionsSection.getByRole("button", { name: "Add option" }).click();
	await inputs.nth(2).fill("Colour");
	await inputs.nth(3).fill("Black");
	await inputs.nth(3).press("Enter");
	await expect(optionsSection.getByText("This will create 2 combinations")).toBeVisible();

	await dialog.getByLabel("Price per variant").fill("555");
	await dialog.getByLabel("Opening stock per variant").fill("2");
	await optionsSection.scrollIntoViewIfNeeded();
	await page.screenshot({ path: `${SHOTS}/b-create-with-options.png` });

	await dialog.getByRole("button", { name: "Create", exact: true }).click();
	await expect(page.getByText("Product created")).toBeVisible({ timeout: 30000 });

	const created = await openProduct(page, NEW_PRODUCT, NEW_PRODUCT);
	await expect(created.locator("tbody tr")).toHaveCount(2);
	await expect(created.getByText("Small / Black")).toBeVisible();
	await expect(created.getByText("Large / Black")).toBeVisible();
	await scrollToVariants(created);
	await page.screenshot({ path: `${SHOTS}/b-created-variants.png` });
	await closeDialog(page);
});

test("b2. add options to a fresh simple product, then edit them", async ({ page }) => {
	await login(page);
	await page.goto("/shop/products");
	await page.getByRole("button", { name: "Add product" }).first().click();
	let dialog = page.getByRole("dialog");
	await dialog.getByLabel("Product name").fill(SIMPLE_PRODUCT);
	await dialog.getByLabel("Price", { exact: true }).fill("300");
	await dialog.getByRole("button", { name: "Create", exact: true }).click();
	await expect(page.getByText("Product created")).toBeVisible({ timeout: 30000 });

	dialog = await openProduct(page, SIMPLE_PRODUCT, SIMPLE_PRODUCT);
	await expect(dialog.getByText("This product has one version")).toBeVisible();
	await scrollToVariants(dialog);
	await page.screenshot({ path: `${SHOTS}/b2-add-options-empty-state.png` });

	await dialog.getByRole("button", { name: "Add options" }).click();
	const variants = dialog
		.locator("section")
		.filter({ has: page.getByRole("heading", { name: "Variants" }) });
	const inputs = variants.locator("input");
	await inputs.nth(0).fill("Material");
	await inputs.nth(1).fill("Cotton");
	await inputs.nth(1).press("Enter");
	await inputs.nth(1).fill("Linen");
	await inputs.nth(1).press("Enter");
	await scrollToVariants(dialog);
	await page.screenshot({ path: `${SHOTS}/b2-options-editor.png` });
	await dialog.getByRole("button", { name: "Save options" }).click();
	await expect(page.getByText("Options saved")).toBeVisible({ timeout: 30000 });
	await expect(variants.locator("tbody tr")).toHaveCount(2);

	// editing options asks for confirmation before rebuilding
	await dialog.getByRole("button", { name: "Edit options" }).click();
	await variants.locator("input").nth(1).fill("Silk");
	await variants.locator("input").nth(1).press("Enter");
	await dialog.getByRole("button", { name: "Save options" }).click();
	await page
		.getByRole("dialog")
		.getByRole("button", { name: "Update options", exact: true })
		.click();
	await expect(page.getByText("Options saved")).toBeVisible({ timeout: 30000 });
	await expect(variants.locator("tbody tr")).toHaveCount(3);
	await closeDialog(page);
});

test("b3. missing combinations banner generates the gap", async ({ page }) => {
	await login(page);
	const product = await page.request.post("/api/method/frappe.client.get_list", {
		data: {
			doctype: "Shop Product Option",
			filters: { parent: `${SIMPLE_PRODUCT.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` },
			fields: ["name", "values"],
			parent: "Shop Product",
		},
	});
	const rows = (await product.json()).message as { name: string; values: string }[];
	expect(rows.length).toBe(1);
	await page.request.post("/api/method/shop.api.variants.save_attribute", {
		data: { attribute: "Material", values: ["Cotton", "Linen", "Silk", "Denim"] },
	});
	await page.request.post("/api/method/frappe.client.set_value", {
		data: {
			doctype: "Shop Product Option",
			name: rows[0].name,
			fieldname: "values",
			value: `${rows[0].values}, Denim`,
		},
	});

	const dialog = await openProduct(page, SIMPLE_PRODUCT, SIMPLE_PRODUCT);
	const generate = dialog.getByRole("button", { name: /Generate 1 missing/ });
	await expect(generate).toBeVisible();
	await scrollToVariants(dialog);
	await page.screenshot({ path: `${SHOTS}/b3-missing-combinations.png` });
	await generate.click();
	await expect(page.getByText("Missing combinations created")).toBeVisible({ timeout: 30000 });
	await expect(dialog.locator("tbody tr")).toHaveCount(4);
	await closeDialog(page);
});

test("c. simple product with stock cannot add options", async ({ page }) => {
	await login(page);
	const dialog = await openProduct(page, "Mug", "Ceramic Mug");
	await expect(dialog.getByText("Options cannot be added now")).toBeVisible();
	await scrollToVariants(dialog);
	await page.screenshot({ path: `${SHOTS}/c-cannot-add-options.png` });
	await closeDialog(page);
});

test("d. delete the test products through the UI", async ({ page }) => {
	await login(page);
	for (const name of [SIMPLE_PRODUCT, NEW_PRODUCT]) {
		await page.goto(`/shop/products?search=${encodeURIComponent(name)}`);
		const row = page.locator("tr", { hasText: name }).first();
		await row.waitFor();
		await row.locator("td").last().getByRole("button").click();
		await page.getByRole("menuitem", { name: "Delete" }).click();
		await page.getByRole("dialog").getByRole("button", { name: "Delete", exact: true }).click();
		await expect(page.getByText("Product deleted")).toBeVisible();
	}
});
