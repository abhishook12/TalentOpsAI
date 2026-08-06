const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Set a mock token to bypass auth
  await page.goto('http://127.0.0.1:5173/login');
  await page.evaluate(() => {
    localStorage.setItem('auth_token', 'mock_token');
    localStorage.setItem('user', JSON.stringify({ id: 1, name: 'Test User' }));
  });
  
  await page.goto('http://127.0.0.1:5173/campaigns');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'campaigns_fix_proof_1.png' });
  
  await browser.close();
})();
