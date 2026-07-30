import { expect, test, type Browser, type Page } from "@playwright/test";

import { adminApi, loginViaApi, type AdminApi } from "../tests/personas/helpers";

const SHOTS = process.env.SHOT_DIR as string;
const STAMP = Date.now();
const NEW_NAME = `Page Editor Test ${STAMP}`;

test.describe.configure({ mode: "serial" });

let page: Page;
let api: AdminApi;

function card(name: string) {
	return page.locator("section").filter({ has: page.getByRole("heading", { name, exact: true }) });
}

function header() {
	return page.locator("main header");
}

function saveButton() {
	return header().getByRole("button", { name: "Save", exact: true });
}

async function newPage(browser: Browser) {
	const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const p = await context.newPage();
	await loginViaApi(p, "Administrator", "admin");
	return p;
}

test.beforeAll(async ({ browser }) => {
	page = await newPage(browser);
	api = await adminApi();
});

test.afterAll(async () => {
	await api.dispose();
	await page.context().close();
});

test("a. a product row opens the two column editor page", async () => {
	await page.goto("/shop/products");
	await page.getByRole("row", { name: /Ceramic Mug/ }).click();
	await page.waitForURL("**/shop/products/ceramic-mug");

	await expect(page.getByRole("heading", { name: "Ceramic Mug", level: 1 })).toBeVisible();
	await expect(page.getByLabel("Product name")).toHaveValue("Ceramic Mug");
	await expect(page.getByLabel("Slug")).toHaveValue("ceramic-mug");
	for (const name of ["Basics", "Media", "Variants", "Pricing", "Highlights"])
		await expect(card(name)).toBeVisible();
	for (const name of ["Status", "Organization", "Inventory", "Danger zone"])
		await expect(card(name)).toBeVisible();
	await expect(saveButton()).toBeDisabled();
});

test("b. editing the short description enables save and persists", async () => {
	const value = `Editor page check ${STAMP}`;
	await page.getByLabel("Short description").fill(value);
	await expect(saveButton()).toBeEnabled();
	await expect(header().getByText("Unsaved changes")).toBeVisible();

	await saveButton().click();
	await expect(page.getByText("Product saved").first()).toBeVisible();
	await expect(saveButton()).toBeDisabled();

	await page.reload();
	await expect(page.getByLabel("Short description")).toHaveValue(value);
});

test("c. unpublishing from the right rail hides the product on the storefront", async () => {
	await card("Status").getByRole("switch", { name: "Published" }).click();
	await saveButton().click();
	await expect(page.getByText("Product saved").first()).toBeVisible();

	const hidden = await page.request.get("/product/ceramic-mug");
	expect(hidden.status(), "unpublished PDP status").toBe(404);
	const list = await (await page.request.get("/products")).text();
	expect(list).not.toContain("/product/ceramic-mug");

	await card("Status").getByRole("switch", { name: "Published" }).click();
	await saveButton().click();
	await expect(page.getByText("Product saved").first()).toBeVisible();
	await expect
		.poll(async () => (await page.request.get("/product/ceramic-mug")).status())
		.toBe(200);
});

test("d. the inventory card sets stock for a simple product", async () => {
	const inventory = card("Inventory");
	const original = Number(await inventory.locator("input[type=number]").inputValue());
	const target = original + 7;

	await inventory.locator("input[type=number]").fill(String(target));
	await inventory.getByRole("button", { name: "Set stock" }).click();
	await expect(page.getByText(`Stock set to ${target}`).first()).toBeVisible();

	await page.goto("/shop/inventory?");
	await page.getByPlaceholder("Search by item or product").fill("Ceramic Mug");
	await expect(page.getByRole("row", { name: /Ceramic Mug/ }).first()).toContainText(
		String(target)
	);

	await page.goto("/shop/products/ceramic-mug");
	await card("Inventory").locator("input[type=number]").fill(String(original));
	await card("Inventory").getByRole("button", { name: "Set stock" }).click();
	await expect(page.getByText(`Stock set to ${original}`).first()).toBeVisible();
});

test("e. add product creates from the page and delete removes it", async () => {
	await page.goto("/shop/products");
	await page.getByRole("link", { name: "Add product" }).click();
	await page.waitForURL("**/shop/products/new");

	await expect(page.getByRole("heading", { name: "New product", level: 1 })).toBeVisible();
	await page.getByLabel("Product name").fill(NEW_NAME);
	await card("Pricing").getByLabel("Price", { exact: true }).fill("199");
	await card("Inventory").getByLabel("Opening stock").fill("3");
	await page.screenshot({ path: `${SHOTS}/create-page.png`, fullPage: true });

	await header().getByRole("button", { name: "Create", exact: true }).click();
	await expect(page.getByText("Product created").first()).toBeVisible();
	await page.waitForURL(/\/shop\/products\/page-editor-test-\d+$/);
	await expect(page.getByRole("heading", { name: NEW_NAME, level: 1 })).toBeVisible();
	const editUrl = page.url();

	await page.goto(`/shop/products?search=Page Editor Test ${STAMP}`);
	await expect(page.getByRole("row", { name: new RegExp(NEW_NAME) })).toBeVisible();

	await page.goto(editUrl);
	await card("Danger zone").getByRole("button", { name: "Delete product" }).click();
	await page.getByRole("dialog").getByRole("button", { name: "Delete", exact: true }).click();
	await expect(page.getByText("Product deleted").first()).toBeVisible();
	await page.waitForURL("**/shop/products");

	await page.goto(`/shop/products?search=Page Editor Test ${STAMP}`);
	await expect(page.getByText("No products found")).toBeVisible();
});

test("f. screenshots of the editor surfaces", async () => {
	await page.goto("/shop/products/ceramic-mug");
	await expect(page.getByLabel("Product name")).toHaveValue("Ceramic Mug");
	await page.waitForTimeout(600);
	await page.screenshot({ path: `${SHOTS}/edit-top.png` });
	await page.evaluate(() => document.querySelector("main")?.scrollTo(0, 900));
	await page.waitForTimeout(400);
	await page.screenshot({ path: `${SHOTS}/edit-scrolled.png` });
	await page.screenshot({ path: `${SHOTS}/edit-full.png`, fullPage: true });

	await page.goto("/shop/products/crew-neck-t-shirt");
	await expect(card("Variants")).toBeVisible();
	await page.waitForTimeout(800);
	await page.screenshot({ path: `${SHOTS}/variant-full.png`, fullPage: true });
	await page.evaluate(() => document.querySelector("main")?.scrollTo(0, 800));
	await page.waitForTimeout(400);
	await page.screenshot({ path: `${SHOTS}/variant-scrolled.png` });
});
