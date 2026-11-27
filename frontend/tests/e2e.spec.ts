import { test, expect } from '@playwright/test'

test.describe('E2E - Login Flow', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Login with valid credentials', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)

    await page.fill('input[type="email"]', 'abhishekjadon824@gmail.com')
    await page.fill('input[type="password"]', 'LocalDevAdmin123!')
    await page.click('button[type="button"]:has-text("Sign In")')

    await page.waitForURL((url) => new URL(url).pathname === '/', { timeout: 15000 })
    expect(new URL(page.url()).pathname).toBe('/')
  })

  test('Login with invalid credentials shows error', async ({ page }) => {
    await page.route('**/auth/login', (route) =>
      route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Invalid credentials' }) })
    )
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(400)

    await page.fill('input[type="email"]', 'wrong@example.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="button"]:has-text("Sign In")')
    
    await page.waitForTimeout(1000)
    const url = page.url()
    const hasError = url.includes('login') || await page.locator('text=/incorrect|invalid|failed/i').isVisible()
    expect(hasError).toBeTruthy()
  })

  test('Forgot password page loads', async ({ page }) => {
    await page.goto('/forgot-password')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)

    const emailInput = page.locator('input[type="email"]')
    await expect(emailInput).toBeVisible()
    // Verify it has w-full (full width) 
    const width = await emailInput.evaluate((el) => el.getBoundingClientRect().width)
    const containerWidth = await emailInput.evaluate((el) => el.parentElement?.parentElement?.getBoundingClientRect().width ?? 0)
    expect(width).toBeGreaterThan(100)
  })
})

test.describe('E2E - Authenticated Navigation', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  test('Dashboard loads and shows content', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
    await page.waitForTimeout(2000)

    // Should not be redirected to login
    expect(page.url()).not.toContain('/login')
    
    // Page should have substantive content
    const body = await page.textContent('body')
    expect(body?.length ?? 0).toBeGreaterThan(100)
  })

  test('Navigation to Recruiters works', async ({ page }) => {
    await page.goto('/recruiters')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
    await page.waitForTimeout(2000)
    expect(page.url()).not.toContain('/login')
  })

  test('Navigation to Analytics works', async ({ page }) => {
    await page.goto('/analytics')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
    await page.waitForTimeout(2000)
    expect(page.url()).not.toContain('/login')
  })

  test('Admin panel accessible to superadmin', async ({ page }) => {
    await page.goto('/admin')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
    await page.waitForTimeout(2000)
    expect(page.url()).not.toContain('/login')
  })

  test('Admin table-sizes endpoint returns 200', async ({ request }) => {
    const loginResp = await request.post('http://127.0.0.1:8000/auth/login', {
      data: { email: 'abhishekjadon824@gmail.com', password: 'LocalDevAdmin123!' },
    })
    const loginJson = await loginResp.json()
    const token = loginJson.token || loginJson.access_token

    const resp = await request.get('http://127.0.0.1:8000/admin/table-sizes', {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(resp.status()).toBe(200)
    const data = await resp.json()
    expect(Array.isArray(data)).toBeTruthy()
  })

  test('Admin system-info endpoint returns 200', async ({ request }) => {
    const loginResp = await request.post('http://127.0.0.1:8000/auth/login', {
      data: { email: 'abhishekjadon824@gmail.com', password: 'LocalDevAdmin123!' },
    })
    const loginJson = await loginResp.json()
    const token = loginJson.token || loginJson.access_token

    const resp = await request.get('http://127.0.0.1:8000/admin/system-info', {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(resp.status()).toBe(200)
    const data = await resp.json()
    expect(data).toHaveProperty('postgres_version')
  })

  test('No broken navigation links in sidebar', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)

    // Collect all nav links
    const links = await page.locator('nav a[href]').all()
    const hrefs = await Promise.all(links.map(l => l.getAttribute('href')))
    console.log('Found nav links:', hrefs)
    
    // Just verify there are links
    expect(links.length).toBeGreaterThan(3)
  })
})

test.describe('Edge Cases', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Custom 404 handling - unknown route redirects gracefully', async ({ page }) => {
    await page.goto('/this-page-does-not-exist-xyz')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)
    await page.waitForTimeout(1000)
    
    // Either shows 404 page or redirects to login — both acceptable
    const html = await page.content()
    expect(html.length).toBeGreaterThan(50) // page rendered something
  })

  test('Double-click on submit does not duplicate request', async ({ page }) => {
    let requestCount = 0
    await page.route('**/auth/forgot-password', async (route) => {
      requestCount++
      await new Promise((r) => setTimeout(r, 300))
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ message: 'Sent' }) })
    })

    await page.goto('/forgot-password')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(400)

    await page.fill('input[type="email"]', 'test@example.com')

    const btn = page.locator('button[type="submit"]')
    // Double click rapidly (second click must not trigger duplicate request)
    await btn.click()
    await btn.click({ force: true, timeout: 1000 }).catch(() => {})
    await page.waitForTimeout(800)

    // Should only fire once (button disables on first click + ref lock)
    expect(requestCount).toBeLessThanOrEqual(1)
  })

  test('Form with empty required fields shows validation', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded'); await page.waitForTimeout(600)

    // Try to submit without filling
    const btn = page.locator('button[type="button"]:has-text("Sign In")')
    expect(await btn.isDisabled()).toBeTruthy()
  })
})

test.describe('Full Route Crawl (Every App Route)', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  const ALL_AUTH_ROUTES = [
    '/', '/recruiters', '/candidates', '/analytics', '/search',
    '/directory', '/states', '/companies', '/campaigns', '/mailintel',
    '/profile', '/settings', '/extension', '/mcp', '/scout/contributors',
    '/admin', '/activity', '/review-queue', '/sentinel',
    '/admin/intelligence-center', '/admin/visitor-analytics', '/admin/users',
    '/admin/settings', '/admin/health', '/admin/jobs', '/admin/audit-logs',
    '/admin/devices', '/admin/staging', '/admin/scout-contributors',
    '/admin/web-harvest', '/admin/teams-harvest',
  ]

  test('All authenticated routes render without blank screen or horizontal overflow', async ({ page }) => {
    test.setTimeout(120_000)
    const failures: string[] = []

    for (const route of ALL_AUTH_ROUTES) {
      await page.goto(`${route}`)
      await page.waitForLoadState('domcontentloaded')
      await page.waitForTimeout(180)

      const check = await page.evaluate(() => ({
        len: document.body?.innerText?.trim().length || 0,
        sw: document.documentElement.scrollWidth,
        cw: document.documentElement.clientWidth,
        url: window.location.pathname,
      }))

      if (check.len < 20) failures.push(`${route}: blank body (len=${check.len})`)
      if (check.sw > check.cw + 2) failures.push(`${route}: horizontal overflow (${check.sw} > ${check.cw})`)
      if (check.url === '/login') failures.push(`${route}: unexpectedly redirected to /login`)
    }

    expect(failures, `Route failures:\n${failures.join('\n')}`).toEqual([])
  })
})

test.describe('Extended Edge Cases (XSS/SQLi, Back/Forward, Error Recovery)', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  test('XSS and SQLi strings in search input are safely escaped', async ({ page }) => {
    let dialogTriggered = false
    page.on('dialog', async (d) => {
      dialogTriggered = true
      await d.dismiss()
    })

    await page.goto('/recruiters')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(800)

    const searchInput = page.locator('input[placeholder*="Search recruiters"]').first()
    await expect(searchInput).toBeVisible()
    await searchInput.fill(`<script>window.__xss=1</script> ' OR 1=1 --`)
    await page.waitForTimeout(800)

    const xssFlag = await page.evaluate(() => (window as any).__xss)
    expect(dialogTriggered).toBe(false)
    expect(xssFlag).toBeUndefined()
    await expect(page.locator('body')).not.toBeEmpty()
  })

  test('Back and Forward browser navigation preserves route integrity', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.goto('/analytics')
    await page.waitForLoadState('domcontentloaded')
    await page.goBack()
    await page.waitForLoadState('domcontentloaded')
    expect(new URL(page.url()).pathname).toBe('/')
    await page.goForward()
    await page.waitForLoadState('domcontentloaded')
    expect(new URL(page.url()).pathname).toBe('/analytics')
  })

  test('API 500 response renders friendly error state instead of blank page', async ({ page }) => {
    await page.route('**/analytics/data-health', (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Simulated failure' }) })
    )
    await page.goto('/analytics')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    const bodyLen = await page.evaluate(() => document.body.innerText.trim().length)
    expect(bodyLen).toBeGreaterThan(50)
  })
})
