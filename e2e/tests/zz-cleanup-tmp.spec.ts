import { expect, request as playwrightRequest, test } from "@playwright/test";

test.setTimeout(300000);

test("cleanup UI Variant Test leftovers", async () => {
	const ctx = await playwrightRequest.newContext({
		baseURL: process.env.SHOP_BASE_URL || "http://shop.localhost:8000",
	});
	async function call<T>(method: string, args: Record<string, unknown>): Promise<T> {
		const res = await ctx.post(`/api/method/${method}`, { data: args });
		if (!res.ok()) throw new Error(`${method}: ${res.status()} ${(await res.text()).slice(0, 200)}`);
		return (await res.json()).message;
	}
	await call("login", { usr: "Administrator", pwd: "admin" });

	const products = await call<{ name: string }[]>("frappe.client.get_list", {
		doctype: "Shop Product",
		filters: { product_name: ["like", "UI Variant Test%"] },
		fields: ["name"],
		limit_page_length: 0,
	});
	for (const row of products) await call("shop.api.products.delete_product", { name: row.name });

	const items = await call<{ name: string; variant_of: string | null }[]>(
		"frappe.client.get_list",
		{
			doctype: "Item",
			filters: { item_name: ["like", "UI Variant Test%"] },
			fields: ["name", "variant_of"],
			limit_page_length: 0,
		}
	);
	const codes = items.map((item) => item.name);

	if (codes.length) {
		const rows = await call<{ parent: string }[]>("frappe.client.get_list", {
			doctype: "Stock Entry Detail",
			parent: "Stock Entry",
			filters: { item_code: ["in", codes] },
			fields: ["parent"],
			limit_page_length: 0,
		});
		for (const entry of new Set(rows.map((row) => row.parent))) {
			const lines = await call<{ item_code: string }[]>("frappe.client.get_list", {
				doctype: "Stock Entry Detail",
				parent: "Stock Entry",
				filters: { parent: entry },
				fields: ["item_code"],
				limit_page_length: 0,
			});
			if (lines.some((line) => !codes.includes(line.item_code))) continue;
			const status = await call<{ docstatus: number }>("frappe.client.get_value", {
				doctype: "Stock Entry",
				filters: { name: entry },
				fieldname: "docstatus",
			});
			if (status.docstatus === 1)
				await call("frappe.client.cancel", { doctype: "Stock Entry", name: entry });
			await call("frappe.client.delete", { doctype: "Stock Entry", name: entry });
		}
	}

	for (const row of [...items].sort((a, b) => (a.variant_of ? 0 : 1) - (b.variant_of ? 0 : 1))) {
		const prices = await call<{ name: string }[]>("frappe.client.get_list", {
			doctype: "Item Price",
			filters: { item_code: row.name },
			fields: ["name"],
			limit_page_length: 0,
		});
		for (const price of prices)
			await call("frappe.client.delete", { doctype: "Item Price", name: price.name });
		await call("frappe.client.delete", { doctype: "Item", name: row.name });
	}

	const attributeUsed = await call<{ name: string }[]>("frappe.client.get_list", {
		doctype: "Item Variant Attribute",
		parent: "Item",
		filters: { attribute: "Material" },
		fields: ["name"],
		limit_page_length: 0,
	});
	if (!attributeUsed.length)
		await call("frappe.client.delete", { doctype: "Item Attribute", name: "Material" });

	const leftItems = await call<unknown[]>("frappe.client.get_list", {
		doctype: "Item",
		filters: { item_name: ["like", "UI Variant Test%"] },
		fields: ["name"],
		limit_page_length: 0,
	});
	const leftProducts = await call<unknown[]>("frappe.client.get_list", {
		doctype: "Shop Product",
		filters: { product_name: ["like", "UI Variant Test%"] },
		fields: ["name"],
		limit_page_length: 0,
	});
	expect(leftItems).toHaveLength(0);
	expect(leftProducts).toHaveLength(0);
	await ctx.dispose();
});
