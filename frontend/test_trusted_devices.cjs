const { chromium } = require('playwright');

(async () => {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();

    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', 'admin@talentops.ai');
    await page.fill('input[type="password"]', 'Admin123!@#');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.cc-shell', { timeout: 15000 });

    console.log('Navigating to Admin Terminal Trusted Devices...');
    await page.goto('http://localhost:5173/admin');
    await page.waitForTimeout(2000);
    
    // Click "Trusted Devices" tab in the admin sidebar if necessary
    // In our case, maybe it's already there or we need to click it.
    // The TrustedDevices is mounted at /admin/trusted-devices or via router lazy loading.
    // Let's just go to the route directly.
    await page.goto('http://localhost:5173/admin/trusted-devices');
    await page.waitForTimeout(3000);
    
    // Take Check 1 Screenshot: Main Page Load
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_trusted_main.png' });
    console.log('✅ Check 1 (Main Page Render) complete');
    
    // Select the first device to show bulk actions
    await page.evaluate(() => {
        const checkbox = document.querySelector('.td-table input[type="checkbox"]');
        if(checkbox) checkbox.click();
    });
    await page.waitForTimeout(1000);
    
    // Take Check 2 Screenshot: Bulk actions appearing
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_trusted_bulk.png' });
    console.log('✅ Check 2 (Bulk Selection Bar) complete');

    // Click Trust on the bulk action bar
    await page.evaluate(() => {
        const trustBtn = document.querySelector('.td-bulk-btn.trust');
        if(trustBtn) trustBtn.click();
    });
    await page.waitForTimeout(1000);

    // Take Check 3 Screenshot: Action Modal
    await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/scratch/proof_trusted_modal.png' });
    console.log('✅ Check 3 (Action Modal) complete');

    console.log('SUCCESS: All checks saved.');
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    if (browser) await browser.close();
  }
})();
