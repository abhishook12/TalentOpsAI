import { test, expect } from '@playwright/test';

test.describe('Continuous Smoke Tests - Critical Paths', () => {
  // Use the baseURL configured in playwright.config.js
  // Default: http://localhost:5173

  test('Application Starts and Loads Login Page', async ({ page, baseURL }) => {
    // Application Starts
    const response = await page.goto('/login');
    
    // Assert 200 OK
    expect(response?.status()).toBe(200);
    
    // Check for login elements
    await expect(page.locator('text=Login to TalentOps')).toBeVisible();
  });

  test('Login Works and Dashboard Loads', async ({ page }) => {
    await page.goto('/login');
    
    // Enter credentials
    await page.locator('input[type="email"]').fill('admin@talentops.com');
    await page.locator('input[type="password"]').fill('1012');
    
    // Click login
    await page.locator('button:has-text("Login to TalentOps")').click();
    
    // Wait for Dashboard to load (look for specific dashboard text/elements)
    await expect(page.locator('text=Dashboard').first()).toBeVisible({ timeout: 15000 });
    
    // Verify session token is set (mocked or real depending on backend)
    const token = await page.evaluate(() => localStorage.getItem('session_token') || sessionStorage.getItem('session_token'));
    expect(token).toBeTruthy();
  });

  test('APIs Respond', async ({ request, baseURL }) => {
    // If testing against Vercel/Render, the APIs might be on a different URL, but locally it should be proxied
    // We can test a public API endpoint if available, or the version endpoint
    let apiBase = baseURL;
    if (baseURL?.includes('talent-ops-ai.vercel.app')) {
       apiBase = 'https://talentopsai-1.onrender.com';
    } else {
       apiBase = 'http://localhost:8000'; // Default local backend port
    }

    const versionResponse = await request.get(`${apiBase}/version`);
    expect(versionResponse.ok()).toBeTruthy();
  });
});
