const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  page.on('console', msg => console.log('BROWSER:', msg.text()));
  page.on('request', req => console.log('REQ:', req.method(), req.url()));
  page.on('response', res => console.log('RES:', res.status(), res.url()));
  
  await page.goto('https://talent-ops-ai.vercel.app/login');
  await page.fill('input[type="email"]', 'admin@talentops.com');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button[type="submit"]');
  await page.waitForURL('https://talent-ops-ai.vercel.app/');
  
  await page.goto('https://talent-ops-ai.vercel.app/campaigns');
  await page.waitForSelector('text=New Campaign');
  await page.click('text=New Campaign');
  
  await page.waitForSelector('text=Manual');
  await page.click('button:has-text("Manual")');
  await page.fill('textarea', 'testqa@example.com');
  
  await page.click('button:has-text("Validate & Add")');
  await page.waitForTimeout(3000);
  
  await page.screenshot({path: 'debug_validate.png'});
  console.log('Saved screenshot to debug_validate.png');
  await browser.close();
})();
