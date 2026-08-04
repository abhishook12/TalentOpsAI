const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: 'dark'
  });
  
  const page = await context.newPage();
  
  try {
    // Set auth to bypass login
    await page.addInitScript(() => {
      window.localStorage.setItem('theme', 'dark');
      window.localStorage.setItem('force_bypass_auth', 'true');
    });
    
    console.log("Navigating to Dashboard...");
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 15000 });
    
    await page.waitForTimeout(3000);
    
    const screenshotPath = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\e050007d-77bf-4880-ac17-0d8a6b8d4518\\dashboard_verified.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    
    console.log("Screenshot saved at:", screenshotPath);
  } catch (error) {
    console.error("Failed:", error);
  } finally {
    await browser.close();
  }
})();
