import { chromium } from '@playwright/test'

const base = 'http://shop.localhost:8000'
const browser = await chromium.launch()
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await context.newPage()
await page.request.post(`${base}/api/method/login`, { data: { usr: 'Administrator', pwd: 'admin' } })
await page.goto(`${base}/shop/products/ceramic-mug`)
await page.waitForTimeout(1500)

const read = async () =>
	page.evaluate(() => {
		const box = (sel) => {
			const el = document.querySelector(sel)
			if (!el) return null
			const r = el.getBoundingClientRect()
			return { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height) }
		}
		const main = document.querySelector('main')
		const grid = document.querySelector('main > div > .grid')
			const rail = grid.children[1]
		const railStyle = rail ? getComputedStyle(rail) : null
		return {
			scrollTop: main.scrollTop,
			mainTop: Math.round(main.getBoundingClientRect().top),
			header: box('main header'),
			mainCol: box('main > div > .grid > div:nth-child(1)'),
			rail: rail
				? {
						top: Math.round(rail.getBoundingClientRect().top),
						position: railStyle.position,
						topValue: railStyle.top,
					}
				: null,
		}
	})

console.log('initial', JSON.stringify(await read(), null, 1))
await page.evaluate(() => document.querySelector('main').scrollTo(0, 300))
await page.waitForTimeout(300)
console.log('scrolled', JSON.stringify(await read(), null, 1))
await page.screenshot({ path: process.env.SHOT_DIR + '/edit-mid-scroll.png' })
await browser.close()
