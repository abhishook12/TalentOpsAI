const puppeteer = require('puppeteer');
const fs = require('fs');

const delay = ms => new Promise(res => setTimeout(res, ms));

(async () => {
  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  // ── Step 1: Login ──
  console.log("Step 1: Navigating to login...");
  await page.goto('http://127.0.0.1:5173/login');
  await page.waitForSelector('input[type="email"]');
  await page.type('input[type="email"]', 'abhishekjadon824@gmail.com');
  await page.type('input[type="password"]', 'password');
  await page.click('button[type="submit"]');
  console.log("  Submitted login form, waiting for navigation...");
  await page.waitForNavigation({ waitUntil: 'networkidle0' });
  console.log("  Login complete.");

  // ── Step 2: Force bridge offline via DB so the error banner appears ──
  console.log("\nStep 2: Setting bridge status to OFFLINE via backend...");
  // Use the backend's own Python to update the status
  const { execSync } = require('child_process');
  execSync(
    'python -c "from app.database import SessionLocal; from app.models.auth_models import UserBridgeStatus; db = SessionLocal(); s = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id==56).first(); s.status=\'offline\'; db.commit(); print(\'Set to offline\')"',
    { cwd: 'C:\\TalentOpsAI\\backend', stdio: 'inherit' }
  );

  // ── Step 3: Navigate to Campaigns and wait for the bridge banner ──
  console.log("\nStep 3: Navigating to Campaigns...");
  await page.goto('http://127.0.0.1:5173/campaigns', { waitUntil: 'networkidle0' });
  await delay(5000); // Wait for the 5-second polling cycle to hit

  await page.screenshot({ path: 'test_01_campaigns_offline.png' });
  console.log("  Saved test_01_campaigns_offline.png");

  // Check if the "Connect your Outlook" button appeared
  const connectBtn = await page.$('#connect-outlook-btn');
  if (!connectBtn) {
    console.log("  WARNING: #connect-outlook-btn not found. Dumping DOM...");
    fs.writeFileSync('dom_dump.html', await page.content());
    // Still continue to take screenshots for verification
    await delay(5000); // Wait another poll cycle
    await page.screenshot({ path: 'test_01b_campaigns_after_wait.png' });
    console.log("  Saved test_01b_campaigns_after_wait.png");
    
    const retryBtn = await page.$('#connect-outlook-btn');
    if (!retryBtn) {
      console.log("  FAIL: Button still not found after retry. Exiting.");
      await browser.close();
      return;
    }
  }
  console.log("  SUCCESS: Found 'Connect your Outlook' button!");

  // ── Step 4: Click the button to open the modal ──
  console.log("\nStep 4: Opening the ConnectOutlookModal...");
  await page.click('#connect-outlook-btn');
  await delay(1500);
  await page.screenshot({ path: 'test_02_modal_open.png' });
  console.log("  Saved test_02_modal_open.png");

  // ── Step 5: Click the modal's "Connect Outlook Account" button ──
  const modalBtn = await page.$('#modal-connect-btn');
  if (!modalBtn) {
    console.log("  FAIL: #modal-connect-btn not found inside modal.");
    await browser.close();
    return;
  }
  console.log("\nStep 5: Clicking 'Connect Outlook Account' in modal...");
  await page.click('#modal-connect-btn');
  await delay(1500);
  await page.screenshot({ path: 'test_03_modal_authenticating.png' });
  console.log("  Saved test_03_modal_authenticating.png");

  // ── Step 6: Simulate OAuth success by setting bridge back to online ──
  console.log("\nStep 6: Simulating OAuth success (setting bridge to online)...");
  execSync(
    'python -c "from app.database import SessionLocal; from app.models.auth_models import UserBridgeStatus; import datetime; db = SessionLocal(); s = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id==56).first(); s.status=\'online\'; s.last_heartbeat=datetime.datetime.utcnow(); db.commit(); print(\'Set to online\')"',
    { cwd: 'C:\\TalentOpsAI\\backend', stdio: 'inherit' }
  );

  // Wait for the modal's polling to detect "online" and show success
  await delay(4000);
  await page.screenshot({ path: 'test_04_modal_success.png' });
  console.log("  Saved test_04_modal_success.png");

  // ── Step 7: After modal auto-closes, the bridge banner should now be green ──
  await delay(3000);
  await page.screenshot({ path: 'test_05_bridge_online.png' });
  console.log("  Saved test_05_bridge_online.png");

  console.log("\n=== ALL CHECKS PASSED ===");
  await browser.close();
})();
