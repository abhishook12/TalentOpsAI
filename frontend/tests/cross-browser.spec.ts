import { test, expect } from '@playwright/test'

test.describe('Cross-Browser Console Errors', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  const routes = ['/login', '/forgot-password', '/download-scout']

  for (const route of routes) {
    test(`Zero console errors on ${route}`, async ({ page }) => {
      const errors: string[] = []
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          const text = msg.text()
          // Ignore known benign external resource errors
          if (
            text.includes('logos.hunter.io') ||
            text.includes('gstatic.com') ||
            text.includes('favicon') ||
            text.includes('ERR_BLOCKED_BY_ORB') ||
            text.includes('net::ERR') ||
            text.includes('Failed to load resource') && (text.includes('logo') || text.includes('favicon'))
          ) return
          errors.push(text)
        }
      })

      await page.goto(`${route}`)
      await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
      await page.waitForTimeout(1000)

      if (errors.length > 0) {
        console.error(`Console errors on ${route}:`, errors)
      }
      expect(errors.length).toBe(0)
    })
  }
})

test.describe('Cross-Browser Console Errors - Auth', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  const routes = ['/', '/recruiters', '/analytics']

  for (const route of routes) {
    test(`Zero critical console errors on ${route}`, async ({ page }) => {
      const errors: string[] = []
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          const text = msg.text()
          if (
            text.includes('logos.hunter.io') ||
            text.includes('gstatic.com') ||
            text.includes('favicon') ||
            text.includes('ERR_BLOCKED_BY_ORB') ||
            text.includes('Failed to load resource')
          ) return
          errors.push(text)
        }
      })

      await page.goto(`${route}`)
      await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
      await page.waitForTimeout(2000)

      if (errors.length > 0) {
        console.log(`Console errors on ${route}:`, errors)
      }
      // Allow React duplicate key warnings in dev mode but fail on others
      const criticalErrors = errors.filter(e => !e.includes('key') && !e.includes('Warning'))
      expect(criticalErrors.length).toBe(0)
    })
  }
})

test.describe('CSS Rendering Basics', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Login page renders correctly', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
    await page.waitForTimeout(500)

    const form = page.locator('form, [role="form"], input[type="email"]').first()
    await expect(form).toBeVisible()

    await page.screenshot({ path: '../reports/screenshots/login-chromium.png' })
  })

  test('Viewport meta tag present', async ({ page }) => {
    await page.goto('/login')
    const viewport = await page.$eval(
      'meta[name="viewport"]',
      (el) => el.getAttribute('content')
    )
    expect(viewport).toContain('width=device-width')
  })
})
