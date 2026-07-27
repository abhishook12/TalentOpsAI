const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  // Set local storage to mock a logged-in session so we don't get redirected to login
  await page.goto('http://localhost:5173/');
  await page.evaluate(() => {
    localStorage.setItem('auth_token', 'dummy_token'); // Mock auth if needed
    localStorage.setItem('theme', 'dark'); // Force dark mode for cool UI
  });

  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:5173/sentinel', { waitUntil: 'networkidle0' });
  
  // Take screenshot
  await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/sentinel_screenshot.png' });
  
  await browser.close();
})();
