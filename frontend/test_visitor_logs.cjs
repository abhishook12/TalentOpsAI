const { chromium } = require('playwright');

(async () => {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();

    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', 'admin@talentops.ai');
    await page.fill('input[type="password"]', 'Admin123!@#');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.cc-shell', { timeout: 15000 });
    
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'light');
    });

    console.log('Navigating to Activity Log...');
    await page.goto('http://localhost:5173/activity');
    await page.waitForTimeout(1000);
    // Click "Visitor Traffic" tab
    await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const visitorBtn = buttons.find(b => b.textContent.includes('Visitor Traffic'));
        if(visitorBtn) visitorBtn.click();
    });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_visitor_traffic_light.png' });

    console.log('Navigating to Admin Terminal Visitor Log Book...');
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark'); // Admin is dark
    });
    await page.goto('http://localhost:5173/admin');
    await page.waitForTimeout(2000);
    // Click "Visitor Log Book" tab
    await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const logBtn = buttons.find(b => b.textContent.includes('Visitor Log Book'));
        if(logBtn) logBtn.click();
    });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_admin_visitor_log.png' });
    
    console.log('SUCCESS');
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    if (browser) await browser.close();
  }
})();
