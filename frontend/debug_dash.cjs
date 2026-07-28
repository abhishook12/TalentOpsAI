const { chromium } = require('playwright');

(async () => {
  let browser;
  try {
    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    page.on('response', async response => {
      if (response.url().includes('/analytics/data-quality')) {
        console.log('Data quality response:', await response.text());
      }
    });

    console.log('Testing standard user...');
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', 'test_user@example.com');
    await page.fill('input[type="password"]', 'User123!@#');
    await page.click('button[type="submit"]');
    
    // Explicitly wait a moment
    await page.waitForSelector('.cc-shell', { timeout: 10000 });
    await page.waitForTimeout(2000);
    
    const content = await page.content();
    if (content.includes("Awaiting an administrator")) {
      console.log("Found awaiting text");
    } else {
      console.log("Did not find awaiting text");
    }
    await context.close();
  } catch (err) {
    console.error('Error:', err);
  }
  if (browser) await browser.close();
})();
