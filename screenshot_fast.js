const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('https://talent-ops-ai.vercel.app');
  await page.fill('input[type="email"]', 'admin@example.com');
  await page.fill('input[type="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard');
  await page.goto('https://talent-ops-ai.vercel.app/campaigns');
  await page.waitForSelector('text=New Campaign');
  await page.waitForTimeout(4000); // Let data load
  await page.screenshot({ path: 'campaigns_fast.png', fullPage: true });
  await browser.close();
})();
