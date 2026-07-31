import { chromium } from "@playwright/test";

const BASE = "http://shop.localhost:8000";
const OUT = "/private/tmp/claude-501/-Users-sps-work-benches-develop-apps-builder/2199826f-0d58-4691-92d1-640fafee7e04/scratchpad/audit-store";

const browser = await chromium.launch();

// Desktop PDP: load-state viewport, colour swatch click, sticky bar check
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(BASE + "/product/crew-neck-t-shirt", { waitUntil: "networkidle" });
  await page.screenshot({ path: `${OUT}/vp-pdp-load-desktop.png` });

  const imgBefore = await page.evaluate(() => document.querySelector("main img, img")?.src);
  const black = page.locator("button", { hasText: /^Black$/ }).first();
  await black.click();
  await page.waitForTimeout(900);
  const imgAfter = await page.evaluate(() => document.querySelector("main img, img")?.src);
  console.log("colour swatch img changed:", imgBefore !== imgAfter, "\n before:", imgBefore, "\n after:", imgAfter);
  await page.screenshot({ path: `${OUT}/vp-pdp-black-desktop.png` });
  await page.screenshot({ path: `${OUT}/pdp-tshirt-colour-swatch-desktop.png`, fullPage: true });

  // sticky bar geometry + visibility at load
  const sticky = await page.evaluate(() => {
    const els = [...document.querySelectorAll("*")].filter((e) => {
      const s = getComputedStyle(e);
      return (s.position === "fixed" || s.position === "sticky") && e.offsetHeight > 30 && e.offsetHeight < 200 && e.getBoundingClientRect().top > 500;
    });
    return els.map((e) => ({ cls: e.className.toString().slice(0, 80), rect: e.getBoundingClientRect().toJSON(), pos: getComputedStyle(e).position }));
  });
  console.log("sticky candidates:", JSON.stringify(sticky, null, 1));

  // scroll to reviews, check overlap
  await page.evaluate(() => window.scrollTo(0, 1400));
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/vp-pdp-reviews-desktop.png` });

  // scroll to bottom
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/vp-pdp-bottom-desktop.png` });
  await ctx.close();
}

// Mobile PDP load + bottom + drawer detail
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.goto(BASE + "/product/crew-neck-t-shirt", { waitUntil: "networkidle" });
  await page.screenshot({ path: `${OUT}/vp-pdp-load-mobile.png` });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/vp-pdp-bottom-mobile.png` });

  // header overflow check
  const nav = await page.evaluate(() => {
    const links = [...document.querySelectorAll("header a, nav a")].map((a) => ({ t: a.textContent.trim().replace(/\s+/g, " "), r: a.getBoundingClientRect().toJSON() }));
    return links.filter((l) => l.r.width);
  });
  console.log("mobile nav rects:", JSON.stringify(nav.slice(0, 10), null, 1));
  await ctx.close();
}

// empty search results state
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(BASE + "/products?search=zzzz", { waitUntil: "networkidle" });
  await page.screenshot({ path: `${OUT}/products-empty-desktop.png`, fullPage: true });
  // empty cart state
  await page.goto(BASE + "/cart", { waitUntil: "networkidle" });
  await page.screenshot({ path: `${OUT}/cart-empty-desktop.png`, fullPage: true });
  // checkout with empty cart
  await page.goto(BASE + "/checkout", { waitUntil: "networkidle" });
  await page.screenshot({ path: `${OUT}/checkout-empty-desktop.png`, fullPage: true });
  await ctx.close();
}

await browser.close();
console.log("DETAIL DONE");
