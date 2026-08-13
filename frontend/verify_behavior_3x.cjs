const { chromium } = require('playwright');

async function testBehavioralPersistence(iteration) {
  console.log(`\n--- Starting Behavioral Verification Run ${iteration} ---`);
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Test 1: Campaigns Persistence
    console.log(`[Run ${iteration}] Navigating directly to Campaigns (auth bypassed locally)...`);
    await page.goto('http://localhost:5173/campaigns');
    
    // Wait for the search input to be visible
    await page.waitForSelector('input[placeholder*="Search"]', { timeout: 15000 });
    
    // Set some state
    const testQuery = `Test_Query_${iteration}`;
    await page.fill('input[placeholder*="Search"]', testQuery);
    console.log(`[Run ${iteration}] Set Campaigns search query to: ${testQuery}`);
    
    // Navigate away to Dashboard using sidebar
    console.log(`[Run ${iteration}] Navigating away to Dashboard...`);
    await page.click('a[href="/"]');
    
    // Wait until we are on dashboard (e.g. Activity or recent campaigns)
    await page.waitForTimeout(1000); 
    
    // Navigate back to Campaigns
    console.log(`[Run ${iteration}] Navigating back to Campaigns...`);
    await page.click('a[href="/campaigns"]');
    await page.waitForSelector('input[placeholder*="Search"]', { timeout: 15000 });
    
    // Verify state persisted
    const restoredQuery = await page.$eval('input[placeholder*="Search"]', el => el.value);
    if (restoredQuery !== testQuery) {
      throw new Error(`Campaigns state lost! Expected "${testQuery}", got "${restoredQuery}"`);
    }
    console.log(`[Run ${iteration}] ✅ Campaigns search state correctly persisted!`);

    // Test 2: Ctrl+K fix verification
    console.log(`[Run ${iteration}] Verifying Ctrl+K fix...`);
    await page.focus('input[placeholder*="Search"]');
    await page.keyboard.press('Control+K');
    
    // Wait a brief moment to see if palette opens
    await page.waitForTimeout(500);
    
    // The Command Palette should NOT be open
    const paletteVisible = await page.isVisible('text=Search commands');
    if (paletteVisible) {
      throw new Error("Command Palette opened while focused on an input field!");
    }
    console.log(`[Run ${iteration}] ✅ Ctrl+K correctly ignored inside inputs!`);

    await page.screenshot({ path: `C:/Users/User/.gemini/antigravity/brain/be5e058f-502c-416d-a76d-db5d160f0985/.user_uploaded/behavior_check_${iteration}.png` });
    console.log(`[Run ${iteration}] ✅ Full Behavioral Verification successful`);
    return true;
  } catch (err) {
    console.error(`[Run ${iteration}] ❌ Verification failed:`, err.message);
    await page.screenshot({ path: `C:/Users/User/.gemini/antigravity/brain/be5e058f-502c-416d-a76d-db5d160f0985/.user_uploaded/behavior_error_${iteration}.png` });
    return false;
  } finally {
    await browser.close();
  }
}

async function main() {
  let successCount = 0;
  for (let i = 1; i <= 3; i++) {
    const success = await testBehavioralPersistence(i);
    if (success) successCount++;
  }

  if (successCount === 3) {
    console.log('\n✅ All 3 behavioral verification runs completed successfully!');
  } else {
    console.log(`\n❌ Only ${successCount}/3 runs successful.`);
    process.exit(1);
  }
}

main();
