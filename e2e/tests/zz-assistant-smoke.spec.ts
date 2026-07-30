import { expect, test } from "@playwright/test";

import { loginViaApi } from "./personas/helpers";

const SHOTS = "/private/tmp/claude-501/-Users-sps-work-benches-develop-apps-builder/2199826f-0d58-4691-92d1-640fafee7e04/scratchpad/shots";

test("assistant renders", async ({ page }) => {
	const errors: string[] = [];
	page.on("pageerror", (error) => errors.push(String(error)));
	await loginViaApi(page, "Administrator", "admin");
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto("/shop/assistant");
	await expect(page.getByRole("heading", { name: "What should we do with the store?" })).toBeVisible();
	await page.screenshot({ path: `${SHOTS}/00-smoke.png` });
	await page.locator('[data-shop="agent-input"]').fill("hello there\nsecond line");
	await expect(page.locator('[data-shop="agent-send"]')).toBeEnabled();
	await page.screenshot({ path: `${SHOTS}/00-composer.png` });
	console.log("PAGE ERRORS:", JSON.stringify(errors));
});
