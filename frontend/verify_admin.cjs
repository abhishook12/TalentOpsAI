const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: 'dark' // prefer dark mode
  });
  
  const page = await context.newPage();
  
  try {
    // Set theme to dark in localStorage before navigating so it loads in dark mode
    await page.addInitScript(() => {
      window.localStorage.setItem('theme', 'dark');
      window.localStorage.setItem('talentops_auth', JSON.stringify({ user: { id: 1, role: 'admin' }, token: 'mock' }));
    });
    
    console.log("Navigating to Admin Dashboard...");
    await page.goto('http://localhost:5173/admin', { waitUntil: 'networkidle', timeout: 15000 });
    
    // Wait for the UI to settle
    await page.waitForTimeout(2000);
    
    const screenshotPath = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\e050007d-77bf-4880-ac17-0d8a6b8d4518\\admin_verified.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    
    console.log("Screenshot saved at:", screenshotPath);
    
  } catch (error) {
    console.error("Verification failed:", error);
  } finally {
    await browser.close();
  }
})();
