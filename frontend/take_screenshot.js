const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900 });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/c9d995cc-1a85-47be-bceb-73bfdb116fb9/dashboard_refresh_proof.png' });
  await browser.close();
})();
