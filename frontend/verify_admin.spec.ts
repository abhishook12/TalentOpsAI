import { test, expect } from '@playwright/test';

test('Admin UI E2E Check', async ({ page }) => {
  // 1. Login
  await page.goto('http://localhost:5173/login');
  await page.fill('input[type="email"]', 'abhishekjadon824@gmail.com');
  await page.fill('input[type="password"]', 'Admin123!@#');
  await page.click('button[type="submit"]');
  await page.waitForURL('http://localhost:5173/');
  console.log('Logged in successfully');

  // 2. Check User Management
  await page.goto('http://localhost:5173/admin/users');
  await page.waitForSelector('text=User Management');
  await page.screenshot({ path: 'verify_users.png' });
  console.log('User Management loaded');

  // 3. Check Settings
  await page.goto('http://localhost:5173/admin/settings');
  await page.waitForSelector('text=Platform Settings');
  await page.screenshot({ path: 'verify_settings.png' });
  console.log('Settings loaded');

  // 4. Check System Health
  await page.goto('http://localhost:5173/admin/health');
  await page.waitForSelector('text=System Health');
  await page.screenshot({ path: 'verify_health.png' });
  console.log('System Health loaded');

  // 5. Check Admin Terminal
  await page.goto('http://localhost:5173/admin');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'verify_terminal.png' });
  console.log('Admin Terminal loaded');
});
