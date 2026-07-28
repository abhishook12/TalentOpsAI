const { chromium } = require('playwright');
const path = require('path');

const OUT_DIR = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\8ca93279-e790-4ae4-b3a8-41b138956926';

async function run() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  
  // 1. Get Admin Token
  console.log('Logging in as admin...');
  const adminRes = await fetch('https://talentopsai-1.onrender.com/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@talentops.com', password: 'Password123!' })
  });
  const adminData = await adminRes.json();
  const adminToken = adminData.token;
  const adminUser = adminData.user;
  
  // 2. Create/Login as Test Regular User
  console.log('Logging in as test user...');
  const testEmail = 'test_regular_user@talentops.com';
  let testRes = await fetch('https://talentopsai-1.onrender.com/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: testEmail, password: 'Password123!' })
  });
  if (!testRes.ok) {
    console.log('Creating test user...');
    await fetch('https://talentopsai-1.onrender.com/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: testEmail, password: 'Password123!', full_name: 'Test User' })
    });
    testRes = await fetch('https://talentopsai-1.onrender.com/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: testEmail, password: 'Password123!' })
    });
  }
  const testData = await testRes.json();
  const testToken = testData.token;
  const testUser = testData.user;

  // TEST 1: Regular User Dashboard Access
  console.log('Testing Regular User Dashboard...');
  const context1 = await browser.newContext();
  const page1 = await context1.newPage();
  await page1.setViewportSize({ width: 1280, height: 720 });
  
  // Navigate to an arbitrary path to set origin
  await page1.goto('https://talent-ops-ai.vercel.app/login');
  
  // Inject session
  await page1.evaluate((data) => {
    localStorage.setItem('auth_session', JSON.stringify({
      token: data.token,
      user: data.user
    }));
  }, { token: testToken, user: testUser });
  
  // Navigate to Dashboard
  await page1.goto('https://talent-ops-ai.vercel.app/');
  
  // Wait for network idle or 3 seconds
  await page1.waitForTimeout(3000);
  
  // Take screenshot
  const ss1Path = path.join(OUT_DIR, 'regular_user_dashboard.png');
  await page1.screenshot({ path: ss1Path });
  console.log('Saved:', ss1Path);
  
  // TEST 2: Admin Directory State Search
  console.log('Testing Admin Directory...');
  const context2 = await browser.newContext();
  const page2 = await context2.newPage();
  await page2.setViewportSize({ width: 1280, height: 720 });
  
  await page2.goto('https://talent-ops-ai.vercel.app/login');
  
  await page2.evaluate((data) => {
    localStorage.setItem('auth_session', JSON.stringify({
      token: data.token,
      user: data.user
    }));
  }, { token: adminToken, user: adminUser });
  
  await page2.goto('https://talent-ops-ai.vercel.app/directory');
  
  // Wait for loading to finish
  await page2.waitForTimeout(5000);
  
  // Search for company
  console.log('Searching company...');
  await page2.fill('input[placeholder="Search company..."]', 'Intersect');
  await page2.waitForTimeout(2000); // Wait for debounce and search
  
  // Click state "CA - California"
  console.log('Clicking state CA...');
  await page2.evaluate(() => {
    const states = Array.from(document.querySelectorAll('div'));
    const ca = states.find(s => s.textContent.includes('CA - California'));
    if (ca) ca.click();
  });
  
  await page2.waitForTimeout(3000); // Wait for recruiters to load
  
  const ss2Path = path.join(OUT_DIR, 'admin_directory_fix.png');
  await page2.screenshot({ path: ss2Path });
  console.log('Saved:', ss2Path);
  
  await browser.close();
  console.log('All done!');
}

run().catch(console.error);
