const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  await page.goto('http://localhost:5173/login');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'login_fix_proof_1.png' });
  
  await page.goto('http://localhost:5173/register');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'register_fix_proof_1.png' });
  
  await browser.close();
})();
