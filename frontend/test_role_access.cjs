const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  let browser;
  try {
    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    console.log('Testing standard user...');
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', 'test_user@example.com');
    await page.fill('input[type="password"]', 'User123!@#');
    await page.click('button[type="submit"]');
    
    // Wait for the main layout to appear
    await page.waitForSelector('.cc-shell', { timeout: 10000 });
    
    // Explicitly wait a moment for react to render
    await page.waitForTimeout(2000);

    // Check dashboard contents
    const content = await page.content();
    await page.screenshot({ path: 'C:\\\\Users\\\\User\\\\.gemini\\\\antigravity\\\\brain\\\\8ca93279-e790-4ae4-b3a8-41b138956926\\\\standard_user_dashboard.png' });
    
    if (content.includes("Import Data")) {
      throw new Error('Standard user should not see Import Data button');
    }
    
    if (!content.includes("Awaiting an administrator to import the initial dataset")) {
      throw new Error('Standard user should see awaiting administrator text');
    }

    // Check topbar avatar navigation
    await page.click('button[title="Account"]');
    
    // Wait for URL to contain /profile
    await page.waitForURL('**/profile', { timeout: 5000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'C:\\\\Users\\\\User\\\\.gemini\\\\antigravity\\\\brain\\\\8ca93279-e790-4ae4-b3a8-41b138956926\\\\standard_user_profile.png' });
    console.log('Standard user test passed.');

    await context.close();
  } catch (err) {
    console.error('Error in standard user test:', err);
    if (browser) await browser.close();
    process.exit(1);
  }

  try {
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();

    console.log('Testing admin user...');
    await page2.goto('http://localhost:5173/login');
    await page2.fill('input[type="email"]', 'admin@talentops.ai');
    await page2.fill('input[type="password"]', 'Admin123!@#');
    await page2.click('button[type="submit"]');
    
    // Wait for the main layout to appear
    await page2.waitForSelector('.cc-shell', { timeout: 10000 });
    
    // Explicitly wait a moment for react to render
    await page2.waitForTimeout(2000);

    // Check dashboard contents
    const content2 = await page2.content();
    await page2.screenshot({ path: 'C:\\\\Users\\\\User\\\\.gemini\\\\antigravity\\\\brain\\\\8ca93279-e790-4ae4-b3a8-41b138956926\\\\admin_dashboard.png' });
    
    if (!content2.includes("Import Data")) {
      throw new Error('Admin user should see Import Data button');
    }

    // Check topbar avatar navigation
    await page2.click('button[title="Account"]'); 
    
    // Wait for URL to contain /admin
    await page2.waitForURL('**/admin', { timeout: 5000 });
    await page2.waitForTimeout(1000);
    await page2.screenshot({ path: 'C:\\\\Users\\\\User\\\\.gemini\\\\antigravity\\\\brain\\\\8ca93279-e790-4ae4-b3a8-41b138956926\\\\admin_terminal.png' });
    console.log('Admin user test passed.');

    await context2.close();
  } catch (err) {
    console.error('Error in admin user test:', err);
    if (browser) await browser.close();
    process.exit(1);
  }

  await browser.close();
  console.log('All tests passed successfully!');
})();
