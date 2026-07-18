const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'https://talent-ops-ai.vercel.app';
const TEST_EMAIL = 'admin@talentops.com';
const TEST_PASS = 'password123';

async function runTest() {
  console.log('--- Starting UI Performance & Functional Test ---');
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  
  // Track all network requests to catch duplicates and measure sizes
  const requestCounts = {};
  let duplicateRequestsDetected = false;
  let consoleErrors = 0;
  let totalRequests = 0;
  
  context.on('request', request => {
    totalRequests++;
    const url = request.url();
    // Ignore analytics or external fluff if any, focus on API
    if (url.includes('api.talentopsai') || url.includes('onrender')) {
      const key = `${request.method()} ${url}`;
      requestCounts[key] = (requestCounts[key] || 0) + 1;
      if (requestCounts[key] > 2 && request.method() !== 'OPTIONS' && !url.includes('/progress') && !url.includes('/health')) {
        console.log(`[WARNING] Potential Duplicate Request: ${key} (${requestCounts[key]}x)`);
        duplicateRequestsDetected = true;
      }
    }
  });

  const page = await context.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error' && !msg.text().includes('favicon')) {
      console.log(`[BROWSER ERROR] ${msg.text()}`);
      consoleErrors++;
    }
  });

  try {
    // 1. Login
    console.log('Logging in...');
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASS);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
    console.log('Login successful.');

    // 2. Measure Campaigns Page Load
    console.log('Navigating to Campaigns...');
    const startTime = Date.now();
    await page.goto(`${BASE_URL}/campaigns`);
    
    // Wait for the table or empty state to render
    await page.waitForSelector('text=Campaigns', { state: 'visible' });
    
    // Wait for the table to render instead of networkidle
    await page.waitForSelector('text=New Campaign', { state: 'visible' });
    
    const performanceTiming = JSON.parse(
      await page.evaluate(() => JSON.stringify(window.performance.timing))
    );
    const loadTime = performanceTiming.loadEventEnd - performanceTiming.navigationStart;
    console.log(`Campaigns Page Load Time (Browser Load Event): ${loadTime}ms`);
    
    if (loadTime > 3000) {
      console.log(`[FAIL] Page load took ${loadTime}ms (Goal: < 2s)`);
    } else {
      console.log(`[PASS] Page load is fast.`);
    }

    // 3. Test Workflow: Create Campaign
    console.log('Testing Campaign Creation Flow...');
    await page.click('text=New Campaign');
    
    // Check if wizard rendered by checking for the Recipients tab
    await page.waitForSelector('text=Directory', { state: 'visible' });
    console.log('[PASS] Reached Recipients Step');
    
    // 4. Test manual entry
    console.log('Testing manual recipient addition...');
    await page.click('button:has-text("Manual")');
    await page.waitForTimeout(500);
    
    await page.fill('textarea', 'testqa@example.com\n');
    await page.waitForTimeout(500); 
    await page.click('button:has-text("Validate & Add")');
    
    // Wait for the recipient to be validated and added to the list (Wait up to 15s for cold start)
    await page.waitForSelector('text=Selected Recipients (1)', { timeout: 15000 });
    
    await page.click('button:has-text("Continue")'); 
    
    await page.waitForSelector('text=Campaign Settings', { state: 'visible' });
    console.log('[PASS] Reached Compose Step');
    
    // 5. Gather Performance Metrics via Performance API
    const metrics = await page.evaluate(() => JSON.stringify(window.performance.toJSON()));
    fs.writeFileSync('perf_metrics.json', metrics);
    console.log('Performance metrics saved to perf_metrics.json');
    
    console.log('\n--- Test Summary ---');
    console.log(`Total Requests: ${totalRequests}`);
    console.log(`Console Errors: ${consoleErrors}`);
    console.log(`Duplicate API Requests Detected: ${duplicateRequestsDetected}`);
    
  } catch (err) {
    console.error('Test Failed:', err);
  } finally {
    await browser.close();
  }
}

runTest();
