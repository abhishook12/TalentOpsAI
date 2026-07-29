const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  let browser;
  try {
    const email = 'test_final_user_1785265458@example.com';
    const password = 'User123!@#';

    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    console.log('Testing vercel site as standard user...', email);
    await page.goto('https://talent-ops-ai.vercel.app/login');
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', password);
    await page.click('button[type="submit"]');
    
    // Wait for the shell or for a successful login indicator
    await page.waitForSelector('.cc-shell', { timeout: 15000 });
    
    console.log('Navigating to directory...');
    await page.goto('https://talent-ops-ai.vercel.app/directory');
    
    // wait for directory page load
    await page.waitForTimeout(5000);
    
    const screenshotPath = 'C:/TalentOpsAI/frontend/vercel_directory_proof.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('Screenshot saved to: ' + screenshotPath);

    // Get text under search company
    try {
        const companiesText = await page.innerText('.cc-panel:has-text("1. Search Company")');
        console.log('Companies block text: ', companiesText.substring(0, 500));
    } catch(e) {}

    // Get text under recruiters
    try {
        const recruitersText = await page.innerText('.cc-panel:has-text("2. Find Recruiters")');
        console.log('Recruiters block text: ', recruitersText.substring(0, 500));
    } catch(e) {}

  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    if (browser) await browser.close();
  }
})();
