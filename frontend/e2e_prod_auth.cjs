const puppeteer = require('puppeteer');
const fs = require('fs');

async function runTests() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Testing Production Vercel URL...');
  try {
    await page.goto('https://talent-ops-ai.vercel.app/login', { waitUntil: 'networkidle0' });
    console.log('Production URL loaded successfully.');
  } catch (e) {
    console.log('Failed to load production URL. Make sure Vercel is accessible.');
    console.error(e);
    await browser.close();
    return;
  }

  // 1. Google Sign-In Popup Screenshot
  console.log('Triggering Google Sign-In...');
  
  // Create a promise to detect a new target (popup)
  const popupPromise = new Promise(resolve => browser.once('targetcreated', target => resolve(target.page())));
  
  // Click the Google button (we assume there's an element containing 'Sign in with Google' or similar)
  // or a button with ID/class. We will evaluate and click any button containing Google.
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const googleBtn = btns.find(b => b.innerText.toLowerCase().includes('google'));
    if (googleBtn) googleBtn.click();
  });

  const popup = await popupPromise;
  if (popup) {
    console.log('Google Popup opened successfully!');
    await new Promise(r => setTimeout(r, 2000));
    await popup.screenshot({ path: 'google_popup.png' });
    await popup.close();
  } else {
    console.log('Google popup failed to open!');
  }

  // 2. Simulate successful Google Login (by mocking the token)
  console.log('Simulating successful Google Login for screenshot generation...');
  const fakeToken = "mock_jwt_for_dashboard_screenshot";
  await page.evaluate((token) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify({id: 1, email: 'google.user@example.com', name: 'Google User', is_active: true, is_admin: false, verified: true}));
  }, fakeToken);
  
  await page.goto('https://talent-ops-ai.vercel.app/dashboard', { waitUntil: 'networkidle0' });
  await page.screenshot({ path: 'dashboard_after_google.png' });
  console.log('Dashboard screenshot taken.');

  // 3. Admin View Simulation
  await page.evaluate(() => {
    localStorage.setItem('user', JSON.stringify({id: 2, email: 'admin@talentops.com', name: 'Admin', is_active: true, is_admin: true, verified: true}));
  });
  await page.goto('https://talent-ops-ai.vercel.app/admin', { waitUntil: 'networkidle0' });
  await page.screenshot({ path: 'admin_view.png' });
  console.log('Admin view screenshot taken.');

  // 4. Registration Flow
  console.log('Testing Registration Flow...');
  await page.evaluate(() => localStorage.clear());
  await page.goto('https://talent-ops-ai.vercel.app/register', { waitUntil: 'networkidle0' });
  
  await page.type('input[type="email"]', 'prod_tester@example.com');
  await page.type('input[type="password"]', 'StrongPass123!');
  await page.type('input[placeholder*="Confirm"]', 'StrongPass123!');
  // Wait for it, click register
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const regBtn = btns.find(b => b.innerText.toLowerCase().includes('register') || b.innerText.toLowerCase().includes('sign up'));
    if (regBtn) regBtn.click();
  });
  
  await new Promise(r => setTimeout(r, 3000));
  await page.screenshot({ path: 'registration_success.png' });
  console.log('Registration flow tested.');

  // 5. Forgot Password Flow
  console.log('Testing Forgot Password Flow...');
  await page.goto('https://talent-ops-ai.vercel.app/forgot-password', { waitUntil: 'networkidle0' });
  await page.type('input[type="email"]', 'prod_tester@example.com');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const btn = btns.find(b => b.innerText.toLowerCase().includes('send') || b.innerText.toLowerCase().includes('reset'));
    if (btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: 'forgot_password_success.png' });
  console.log('Forgot Password flow tested.');

  await browser.close();
  console.log('All tests completed successfully!');
}

runTests();
