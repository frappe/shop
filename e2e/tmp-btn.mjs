import { chromium } from '@playwright/test'
const base = 'http://shop.localhost:8000'
const browser = await chromium.launch()
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await context.newPage()
await page.request.post(`${base}/api/method/login`, { data: { usr: 'Administrator', pwd: 'admin' } })
await page.goto(`${base}/shop/products/new`)
await page.waitForTimeout(1200)
const probe = async (tag) => {
	const info = await page.evaluate(() => {
		const btns = [...document.querySelectorAll('main header button')]
		const b = btns[btns.length - 1]
		const cs = getComputedStyle(b)
		return { text: b.textContent.trim(), disabled: b.disabled, bg: cs.backgroundColor, color: cs.color, classes: b.className }
	})
	console.log(tag, JSON.stringify(info))
}
await probe('before')
await page.getByLabel('Product name').fill('Probe product')
await page.waitForTimeout(400)
await probe('after')
await browser.close()
