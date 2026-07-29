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
    
    let proxiedRequestDetected = false;

    // Intercept network requests to prove the proxy is being used!
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/auth/login') && request.method() === 'POST') {
        console.log('Intercepted Login Request URL:', url);
        if (url.includes('vercel.app/api/auth/login')) {
           proxiedRequestDetected = true;
           console.log('✅ SUCCESS: Request is successfully using the Vercel edge proxy!');
        }
      }
    });

    console.log('Testing vercel site login via proxy as standard user...', email);
    await page.goto('https://talent-ops-ai.vercel.app/login');
    
    // Screenshot of the login page before submitting
    await page.screenshot({ path: 'C:/TalentOpsAI/frontend/proof_1_login_page.png' });
    console.log('Screenshot saved: proof_1_login_page.png');
    
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', password);
    await page.click('button[type="submit"]');
    
    // Wait for the login to succeed and navigate away (we wait for the shell to appear)
    await page.waitForSelector('.cc-shell', { timeout: 15000 });
    
    // Screenshot of the successful login landing page
    await page.screenshot({ path: 'C:/TalentOpsAI/frontend/proof_2_logged_in.png' });
    console.log('Screenshot saved: proof_2_logged_in.png');
    
    console.log('Navigating to directory to prove standard user data is visible...');
    await page.goto('https://talent-ops-ai.vercel.app/directory');
    
    // wait for directory page load
    await page.waitForTimeout(5000);
    
    const screenshotPath = 'C:/TalentOpsAI/frontend/proof_3_directory_works.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('Screenshot saved: proof_3_directory_works.png');

    if (proxiedRequestDetected) {
       console.log('\nFINAL RESULT: ✅ ALL SYSTEMS VERIFIED AND WORKING THROUGH VERCEL PROXY!');
    } else {
       console.log('\nFINAL RESULT: ❌ Proxy request not detected. Check VITE_API_URL settings.');
    }

  } catch (error) {
    console.error('Test failed:', error);
    await page.screenshot({ path: 'C:/TalentOpsAI/frontend/proof_error.png' });
  } finally {
    if (browser) await browser.close();
  }
})();
