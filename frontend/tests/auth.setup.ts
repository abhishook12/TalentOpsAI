import { test as setup, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const authFile = path.join(__dirname, '../playwright/.auth/admin.json')

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login')
  await page.waitForLoadState('domcontentloaded')

  await page.fill('input[type="email"]', 'abhishekjadon824@gmail.com')
  await page.fill('input[type="password"]', 'LocalDevAdmin123!')
  await page.click('button[type="button"]:has-text("Sign In")')

  await page.waitForURL((url) => new URL(url).pathname === '/', { timeout: 15_000 })
  await expect(page.locator('body')).not.toBeEmpty()

  fs.mkdirSync(path.dirname(authFile), { recursive: true })
  await page.context().storageState({ path: authFile })
})
