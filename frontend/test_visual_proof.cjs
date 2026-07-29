const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();

    console.log('Testing local dev server... Make sure it is running!');
    await page.goto('http://localhost:5173/login');
    
    // Login
    await page.fill('input[type="email"]', 'admin@talentops.ai');
    await page.fill('input[type="password"]', 'Admin123!@#');
    await page.click('button[type="submit"]');
    
    // Wait for dashboard to load
    await page.waitForSelector('.cc-shell', { timeout: 15000 });
    console.log('Logged in successfully.');
    
    // Switch to Light Theme
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'light');
    });

    console.log('Navigating to Activity Log...');
    await page.goto('http://localhost:5173/activity');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_activity_log_light.png' });
    console.log('Saved: proof_activity_log_light.png');

    console.log('Navigating to Profile...');
    await page.goto('http://localhost:5173/profile');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_profile_light.png' });
    console.log('Saved: proof_profile_light.png');

    console.log('Navigating to US Heatmap (Directory)...');
    await page.goto('http://localhost:5173/directory');
    await page.waitForTimeout(2000);
    
    // Hover over a state if possible, let's just screenshot
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_heatmap_light.png' });
    console.log('Saved: proof_heatmap_light.png');
    
    console.log('Testing Campaign Progress in Dark Theme...');
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.goto('http://localhost:5173/campaigns');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_campaigns_dark.png' });
    console.log('Saved: proof_campaigns_dark.png');

    console.log('SUCCESS: All screenshots saved.');
  } catch (error) {
    console.error('Test failed:', error);
    if (browser) {
      const page = await browser.contexts()[0]?.pages()[0];
      if (page) await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_error.png' });
    }
  } finally {
    if (browser) await browser.close();
  }
})();
