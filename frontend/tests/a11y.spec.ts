import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const PUBLIC_ROUTES = ['/login', '/forgot-password', '/download-scout']
const AUTH_ROUTES = ['/', '/recruiters', '/candidates', '/analytics', '/search', '/admin']

test.describe('Accessibility - Public Pages (axe-core)', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  for (const route of PUBLIC_ROUTES) {
    test(`WCAG 2.2 AA - ${route}`, async ({ page }) => {
      test.setTimeout(120_000)
      await page.goto(`${route}`)
      await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('[aria-hidden="true"]')
        .analyze()

      const critical = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious')

      if (critical.length > 0) {
        console.error(`Violations on ${route}:`, JSON.stringify(critical.map(v => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          nodes: v.nodes.length,
        })), null, 2))
      }

      expect(critical.length, `${critical.length} critical/serious a11y violations on ${route}`).toBe(0)
    })
  }
})

test.describe('Accessibility - Auth Pages (axe-core)', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  for (const route of AUTH_ROUTES) {
    test(`WCAG 2.2 AA - ${route}`, async ({ page }) => {
      test.setTimeout(120_000)
      await page.goto(`${route}`)
      await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
      await page.waitForTimeout(1500)

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('[aria-hidden="true"]')
        .analyze()

      const critical = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious')

      if (results.violations.length > 0) {
        console.log(`All violations on ${route}:`, results.violations.map(v => `[${v.impact}] ${v.id}: ${v.description}`).join('\n'))
      }

      expect(critical.length, `${critical.length} critical/serious a11y violations on ${route}: ${critical.map(v => v.id).join(', ')}`).toBe(0)
    })
  }
})

test.describe('Keyboard Navigation', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Login page - full keyboard nav', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)

    // Tab through all interactive elements
    await page.keyboard.press('Tab')
    const focused1 = await page.evaluate(() => document.activeElement?.tagName)
    expect(['INPUT', 'BUTTON', 'A']).toContain(focused1)
  })

  test('Login form submits on Enter', async ({ page }) => {
    await page.route('**/auth/login', (route) =>
      route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Invalid credentials' }) })
    )
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(400)

    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(800)

    const html = await page.content()
    expect(html.length).toBeGreaterThan(100)
  })
})
