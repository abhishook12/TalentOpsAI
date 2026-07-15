const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\af41bbca-eae6-4fe8-82b8-160609b01afb';
const BASE_URL = 'http://localhost:5173';

(async () => {
  console.log("Starting QA Automation...");
  const browser = await puppeteer.launch({
    headless: "new",
    defaultViewport: { width: 1440, height: 900 }
  });
  const page = await browser.newPage();

  // Handle console messages
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(`[Browser Console Error] ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    errors.push(`[Page Exception] ${err.message}`);
  });

  const failedRequests = [];
  page.on('requestfailed', request => {
    failedRequests.push(`[Network Failure] ${request.url()} - ${request.failure().errorText}`);
  });

  console.log("Navigating to index and bypassing login...");
  await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
  
  await page.evaluate(() => {
    localStorage.setItem('auth_session', JSON.stringify({
      user_id: 1,
      email: 'admin@talentops.ai',
      first_name: 'System',
      last_name: 'Admin',
      role: 'admin',
      token: 'mock-token-for-qa'
    }));
    sessionStorage.setItem('talentops_sid', 'qa-session-id-123');
  });

  console.log("Testing Health Dashboard...");
  await page.goto(`${BASE_URL}/admin/health`, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'qa_health_dashboard.png'), fullPage: true });

  console.log("Testing Analytics Dashboard...");
  await page.goto(`${BASE_URL}/analytics`, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'qa_analytics_dashboard.png'), fullPage: true });

  console.log("Testing Campaigns Page (to verify Lazy Loading)...");
  await page.goto(`${BASE_URL}/campaigns`, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'qa_campaigns_page.png'), fullPage: true });

  console.log("Writing QA Report...");
  const report = {
    errors,
    failedRequests,
    timestamp: new Date().toISOString(),
    status: errors.length === 0 && failedRequests.length === 0 ? "PASSED" : "FAILED"
  };
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'qa_results.json'), JSON.stringify(report, null, 2));

  console.log("QA Automation Complete.");
  await browser.close();
})();
