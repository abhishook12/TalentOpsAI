import { test, expect } from '@playwright/test';

// We bypass the external API by intercepting network requests or relying on the frontend's mock logic if any,
// but for E2E we usually want the real backend running. In a CI environment, we will boot both.

test.describe('Critical Regression Paths', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/login');
  });

  test('Search persistence across navigation (Regression)', async ({ page }) => {
    // Since we are running the local server, we might hit auth walls.
    // If auth is required, we need to mock it or login.
    // For this test, let's assume we have a way to mock the auth response or we login.
    
    // We will intercept the auth check to force a logged-in state
    await page.route('**/api/users/me', async (route) => {
      const json = { id: 1, email: 'test@example.com', role: 'admin' };
      await route.fulfill({ json });
    });
    
    await page.route('**/api/campaigns*', async (route) => {
      await route.fulfill({ json: [] });
    });

    await page.route('**/api/kpis*', async (route) => {
      await route.fulfill({ json: { counts: { all: 0, active: 0, draft: 0, paused: 0, completed: 0, failed: 0 } } });
    });

    // Go to campaigns bypassing login redirect logic
    await page.goto('/campaigns');

    // Type a search query
    const searchInput = page.locator('input[placeholder="Search..."]');
    await searchInput.waitFor({ state: 'visible' });
    await searchInput.fill('Regression Test Campaign');
    await expect(searchInput).toHaveValue('Regression Test Campaign');

    // Navigate away
    await page.click('text=Dashboard');
    await page.waitForURL('**/'); // dashboard route

    // Navigate back
    await page.click('text=Campaigns');
    await page.waitForURL('**/campaigns');

    // Verify search query persisted
    await expect(page.locator('input[placeholder="Search..."]')).toHaveValue('Regression Test Campaign');
  });
});
