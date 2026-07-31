import { chromium } from "@playwright/test";

const BASE = "http://shop.localhost:8000";
const OUT = "/private/tmp/claude-501/-Users-sps-work-benches-develop-apps-builder/2199826f-0d58-4691-92d1-640fafee7e04/scratchpad/audit-store";

async function robustGoto(page, url) {
  for (let i = 0; i < 4; i++) {
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
      const title = await page.title();
      if (title !== "Not Found" && title !== "") return true;
      console.log(`retry ${i} for ${url} (title=${title})`);
    } catch (e) {
      console.log(`retry ${i} for ${url}: ${e.message.slice(0, 60)}`);
    }
    await page.waitForTimeout(1500);
  }
  return false;
}

const browser = await chromium.launch();

// desktop tshirt PDP
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await robustGoto(page, BASE + "/product/crew-neck-t-shirt");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/pdp-tshirt-desktop.png`, fullPage: true });
  console.log("pdp-tshirt-desktop done, title:", await page.title());
  await ctx.close();
}

// mobile: about, tshirt pdp + swatch, cart drawer, order confirmation
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  await robustGoto(page, BASE + "/about");
  await page.screenshot({ path: `${OUT}/about-mobile.png`, fullPage: true });
  console.log("about-mobile title:", await page.title());

  await robustGoto(page, BASE + "/product/crew-neck-t-shirt");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/pdp-tshirt-mobile.png`, fullPage: true });
  const swatches = page.locator("[data-attribute] button, [class*=swatch], button[data-value]");
  const count = await swatches.count();
  console.log("mobile swatch candidates:", count);
  if (count > 1) {
    await swatches.nth(1).click().catch((e) => console.log("swatch fail", e.message.slice(0, 60)));
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${OUT}/pdp-tshirt-swatch-mobile.png`, fullPage: true });
  }

  await robustGoto(page, BASE + "/product/ceramic-mug");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/pdp-mug-mobile.png`, fullPage: true });
  const addBtn = page.locator("button", { hasText: /add to cart/i }).first();
  if (await addBtn.count()) {
    await addBtn.click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${OUT}/cart-drawer-mobile.png` });
    await page.screenshot({ path: `${OUT}/cart-drawer-mobile-full.png`, fullPage: true });
    console.log("mobile drawer captured");
  } else console.log("no add btn mobile");

  const addRes = await page.request.post(BASE + "/api/method/shop.storefront.cart.add_item", {
    data: { item_code: "SHOP-DEMO-004" }, headers: { "Content-Type": "application/json" },
  });
  console.log("add_item:", addRes.status());
  const orderRes = await page.request.post(BASE + "/api/method/shop.storefront.checkout.place_order", {
    data: {
      customer: { email: `audit-${Date.now()}@example.test`, full_name: "Audit Shopper" },
      address: { address_line1: "1 Audit Way", city: "Bengaluru", state: "Karnataka", pincode: "560001" },
      payment_method: "cod",
    }, headers: { "Content-Type": "application/json" },
  });
  const j = await orderRes.json();
  const confUrl = j.message?.confirmation_url;
  console.log("conf url:", confUrl);
  if (confUrl) {
    await robustGoto(page, BASE + confUrl);
    await page.waitForTimeout(600);
    await page.screenshot({ path: `${OUT}/order-confirmation-mobile.png`, fullPage: true });
    console.log("order-confirmation-mobile title:", await page.title());
  }
  await ctx.close();
}

await browser.close();
console.log("RETRY DONE");
