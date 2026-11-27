import { test, expect } from '@playwright/test'

const BREAKPOINTS = [320, 360, 375, 390, 414, 480, 600, 768, 820, 1024, 1180, 1280, 1440, 1920, 2560, 3840]
const PUBLIC_ROUTES = ['/login', '/forgot-password', '/download-scout']
const AUTH_ROUTES = ['/', '/recruiters', '/candidates', '/analytics', '/search']

test.describe('Responsive Layout - Device Native Public Pages', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  for (const route of PUBLIC_ROUTES) {
    test(`No horizontal overflow on device viewport - ${route}`, async ({ page }) => {
      await page.goto(route)
      await page.waitForLoadState('domcontentloaded')
      await page.waitForTimeout(500)

      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2)
    })
  }
})

test.describe('Responsive Layout - Breakpoint Matrix (320px to 3840px)', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('All 16 breakpoints pass zero horizontal overflow on /login and /download-scout', async ({ page }, testInfo) => {
    if (testInfo.project.name !== 'Desktop Chrome') {
      test.skip(true, 'Full 16-breakpoint sweep runs on Desktop Chrome; device projects test native viewports')
    }
    test.setTimeout(90_000)

    for (const route of ['/login', '/download-scout']) {
      for (const bp of BREAKPOINTS) {
        await page.setViewportSize({ width: bp, height: 900 })
        await page.goto(route)
        await page.waitForLoadState('domcontentloaded')
        await page.waitForTimeout(250)

        const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
        const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
        expect(scrollWidth, `Overflow at ${bp}px on ${route}`).toBeLessThanOrEqual(clientWidth + 2)

        await page.screenshot({
          path: `../reports/screenshots/${route.replace(/\//g, '_')}-${bp}px.png`,
          fullPage: false,
        })
      }
    }
  })

  test('WCAG Reflow 400% zoom equivalent (320px CSS width) has zero horizontal overflow', async ({ page }, testInfo) => {
    if (testInfo.project.name !== 'Desktop Chrome') {
      test.skip(true, 'Reflow sweep runs on Desktop Chrome')
    }
    await page.setViewportSize({ width: 320, height: 640 })
    for (const route of PUBLIC_ROUTES) {
      await page.goto(route)
      await page.waitForLoadState('domcontentloaded')
      await page.waitForTimeout(300)
      const sw = await page.evaluate(() => document.documentElement.scrollWidth)
      const cw = await page.evaluate(() => document.documentElement.clientWidth)
      expect(sw, `400% reflow failed on ${route}`).toBeLessThanOrEqual(cw + 2)
    }
  })
})

test.describe('Responsive Layout - Device Native Auth Pages', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  for (const route of AUTH_ROUTES) {
    test(`No overflow on device viewport - ${route}`, async ({ page }) => {
      await page.goto(route)
      await page.waitForLoadState('domcontentloaded')
      await page.waitForTimeout(600)

      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2)
    })
  }
})

test.describe('Mobile Navigation', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  test('Mobile hamburger opens/closes sidebar and handles Escape', async ({ page }) => {
    const vp = page.viewportSize()
    if (!vp || vp.width >= 900) {
      test.skip(true, 'Desktop viewport shows persistent sidebar')
    }

    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(500)

    const hamburger = page.getByRole('button', { name: /open navigation/i })
    await expect(hamburger).toBeVisible()
    await hamburger.click()

    const sidebar = page.locator('#sidebar-nav')
    await expect(sidebar).toBeVisible()

    // Close via X button
    await page.getByRole('button', { name: /close navigation/i }).click()
    await expect(sidebar).not.toBeVisible()

    // Reopen and close via Escape
    await hamburger.click()
    await expect(sidebar).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(sidebar).not.toBeVisible()
  })
})

test.describe('Input Font Size (iOS zoom prevention)', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Auth inputs have font-size >= 16px', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForSelector('input[type="email"]')

    const inputs = page.locator('input[type="email"], input[type="password"], input[type="text"]')
    const count = await inputs.count()

    for (let i = 0; i < count; i++) {
      const fontSize = await inputs.nth(i).evaluate((el) => parseFloat(window.getComputedStyle(el).fontSize))
      expect(fontSize, `Input #${i} font-size should be >= 16px`).toBeGreaterThanOrEqual(16)
    }
  })
})
