import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "./tmp-verify",
	timeout: 60000,
	retries: 0,
	workers: 1,
	use: {
		baseURL: process.env.SHOP_BASE_URL || "http://shop.localhost:8000",
		screenshot: "only-on-failure",
	},
	projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
