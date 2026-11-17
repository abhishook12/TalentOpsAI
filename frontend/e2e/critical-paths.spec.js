import { test, expect } from '@playwright/test';

// We bypass the external API by intercepting network requests or relying on the frontend's mock logic if any,
// but for E2E we usually want the real backend running. In a CI environment, we will boot both.

test.describe('Critical Regression Paths', () => {
  test('Search persistence across navigation (Regression)', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('auth_session', JSON.stringify({
        id: 1,
        email: 'test@example.com',
        first_name: 'Test',
        role: 'admin',
      }));
    });

    await page.route('**:8000/auth/me', async (route) => {
      await route.fulfill({ json: {
        authenticated: true,
        user: { id: 1, email: 'test@example.com', first_name: 'Test', role: 'admin' },
      }});
    });

    await page.route('**:8000/campaigns**', async (route) => {
      await route.fulfill({ json: [] });
    });

    await page.route('**/api/kpis*', async (route) => {
      await route.fulfill({ json: { counts: { all: 0, active: 0, draft: 0, paused: 0, completed: 0, failed: 0 } } });
    });

    await page.goto('/campaigns');

    const searchInput = page.getByPlaceholder(/Search old campaigns/i);
    await searchInput.waitFor({ state: 'visible' });
    await searchInput.fill('Regression Test Campaign');
    await expect(searchInput).toHaveValue('Regression Test Campaign');

    await page.goto('/');
    await page.goto('/campaigns');

    await expect(page.getByPlaceholder(/Search old campaigns/i)).toHaveValue('Regression Test Campaign');
  });
});
