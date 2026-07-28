const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  let browser;
  try {
    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    page.on('requestfailed', request => {
      console.log('Request failed:', request.url(), request.failure().errorText);
    });
    page.on('response', response => {
      if (response.url().includes('/login')) {
        console.log('Login response status:', response.status());
      }
    });

    console.log('Testing standard user...');
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', 'test_user@example.com');
    await page.fill('input[type="password"]', 'User123!@#');
    await page.click('button[type="submit"]');
    
    // Explicitly wait a moment
    await page.waitForTimeout(5000);
    
    console.log('Current URL:', page.url());

    await context.close();
  } catch (err) {
    console.error('Error in standard user test:', err);
    if (browser) await browser.close();
    process.exit(1);
  }
  await browser.close();
})();
