const { chromium } = require('playwright');
const fs = require('fs');

async function testCampaignFlow(iteration) {
  console.log(`\n--- Starting Verification Run ${iteration} ---`);
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Go to localhost:5173 and login
    console.log(`[Run ${iteration}] Logging in...`);
    await page.goto('http://localhost:5173/login');
    await page.fill('input[type="email"]', 'playwright@talentops.ai');
    await page.fill('input[type="password"]', 'password123'); // playwright credentials
    await page.click('button:has-text("Login to TalentOps")');
    await page.waitForSelector('text=Dashboard', { timeout: 10000 });

    // 2. Navigate to Campaigns
    console.log(`[Run ${iteration}] Navigating to Campaigns...`);
    await page.click('a:has-text("Campaigns")');
    await page.waitForSelector('text=New Campaign');

    // 3. Create New Campaign
    console.log(`[Run ${iteration}] Creating new campaign...`);
    await page.click('button:has-text("New Campaign")');
    
    // Wait for the Drag & Drop area to appear
    await page.waitForSelector('text=Drag & Drop', { timeout: 10000 }).catch(() => {});
    
    // Switch to Paste Directly tab
    await page.click('button:has-text("Paste Directly")');
    await page.fill('textarea[placeholder*="john@example.com"]', 'test1@example.com\ntest2@example.com\ntest3@example.com');
    await page.click('button:has-text("Add 3 Recipients")');

    // Screenshot Recipients Step
    await page.screenshot({ path: `campaign_verification_run${iteration}_step1_recipients.png` });
    console.log(`[Run ${iteration}] Screenshot taken: Recipients Step`);

    // Go to Next Step (Compose)
    await page.click('button:has-text("Continue")');
    await page.waitForSelector('input[placeholder*="Subject"]');
    
    // Check Auto-Save Indicator
    // The indicator should be somewhere
    await page.screenshot({ path: `campaign_verification_run${iteration}_step2_compose.png` });
    console.log(`[Run ${iteration}] Screenshot taken: Compose Step`);

    // Fill Compose
    await page.fill('input[placeholder*="Subject"]', `Test Subject ${iteration}`);
    await page.click('button:has-text("Continue")');
    
    // 4. Preflight Validation
    console.log(`[Run ${iteration}] Waiting for Preflight Validation...`);
    await page.waitForSelector('text=Pre-Flight Validation', { timeout: 10000 });
    
    // Wait for the loader to disappear
    await page.waitForFunction(() => !document.querySelector('.animate-spin'));
    
    await page.screenshot({ path: `campaign_verification_run${iteration}_step3_preflight.png` });
    console.log(`[Run ${iteration}] Screenshot taken: Preflight Step`);

    console.log(`[Run ${iteration}] ✅ Verification successful`);
    return true;
  } catch (err) {
    console.error(`[Run ${iteration}] ❌ Verification failed:`, err.message);
    await page.screenshot({ path: `campaign_verification_run${iteration}_error.png` });
    return false;
  } finally {
    await browser.close();
  }
}

async function main() {
  let successCount = 0;
  for (let i = 1; i <= 3; i++) {
    const success = await testCampaignFlow(i);
    if (success) successCount++;
  }

  if (successCount === 3) {
    console.log('\n✅ All 3 verification runs completed successfully!');
  } else {
    console.log(`\n❌ Only ${successCount}/3 runs successful.`);
  }
}

main();
