import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "./tests",
	timeout: 30000,
	retries: 0,
	workers: 1,
	use: {
		baseURL: process.env.SHOP_BASE_URL || "http://shop.localhost:8000",
		screenshot: "only-on-failure",
	},
	projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
