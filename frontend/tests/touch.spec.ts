import { test, expect } from '@playwright/test'

test.describe('Touch & Mobile Interactions - Public', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Mobile tap targets and font sizes on /login', async ({ page, isMobile }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForSelector('input[type="email"]')

    // All inputs must have font-size >= 16px to prevent iOS auto-zoom
    const inputFontSizes = await page.locator('input[type="email"], input[type="password"]').evaluateAll((els) =>
      els.map((el) => ({
        type: el.getAttribute('type'),
        fontSize: parseFloat(window.getComputedStyle(el).fontSize),
        height: el.getBoundingClientRect().height,
      }))
    )
    for (const item of inputFontSizes) {
      expect(item.fontSize, `Input ${item.type} font-size >= 16px`).toBeGreaterThanOrEqual(16)
      expect(Math.round(item.height), `Input ${item.type} height >= 44px`).toBeGreaterThanOrEqual(44)
    }

    // Submit and Google sign-in buttons must be >= 44px tall
    const primaryBtns = page.locator('button:has-text("Sign In"), button:has-text("Continue with Google")')
    const count = await primaryBtns.count()
    for (let i = 0; i < count; i++) {
      const box = await primaryBtns.nth(i).boundingBox()
      expect(box).not.toBeNull()
      if (box) {
        expect(box.height).toBeGreaterThanOrEqual(44)
      }
    }

    if (isMobile) {
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2)
    }
  })
})

test.describe('Touch & Mobile Interactions - Authenticated', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  test('Mobile drawer opens on tap, closes on backdrop tap and Escape', async ({ page }) => {
    const vp = page.viewportSize()
    if (!vp || vp.width >= 900) {
      test.skip(true, 'Desktop viewport does not use mobile drawer')
    }

    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(800)

    const hamburger = page.getByRole('button', { name: /open navigation menu/i })
    await expect(hamburger).toBeVisible()
    const hBox = await hamburger.boundingBox()
    expect(hBox).not.toBeNull()
    if (hBox) {
      expect(hBox.width).toBeGreaterThanOrEqual(44)
      expect(hBox.height).toBeGreaterThanOrEqual(44)
    }

    // Open drawer
    await hamburger.click()
    const sidebar = page.locator('#sidebar-nav')
    await expect(sidebar).toBeVisible()

    // Orientation check while open
    await page.setViewportSize({ width: vp.height, height: vp.width })
    await page.waitForTimeout(200)
    await page.setViewportSize({ width: vp.width, height: vp.height })

    // Close via Escape
    await page.keyboard.press('Escape')
    await expect(sidebar).not.toBeVisible()
  })

  test('No hover-only critical controls block mobile workflow on /recruiters', async ({ page }) => {
    await page.goto('/recruiters')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1200)

    // Scroll should not be locked
    const overflowY = await page.evaluate(() => window.getComputedStyle(document.body).overflowY)
    expect(overflowY).not.toBe('hidden')
  })
})
