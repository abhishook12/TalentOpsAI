const { chromium } = require('playwright');
const axios = require('axios');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Set auth token
  await page.goto('http://127.0.0.1:5173/login');
  await page.evaluate(() => {
    localStorage.setItem('auth_token', 'mock_token');
    localStorage.setItem('user', JSON.stringify({ id: 1, name: 'Test User' }));
  });
  
  // Intercept the prepare-preview API call to see the response
  page.on('response', async response => {
    if (response.url().includes('prepare-preview')) {
      console.log('prepare-preview response:', await response.json());
    }
  });

  await page.goto('http://127.0.0.1:5173/campaigns');
  await page.waitForTimeout(1000);
  
  // Click 'New Campaign' button
  await page.click('button:has-text("New Campaign")');
  await page.waitForTimeout(500);
  
  // Now on Recipients step. Add a valid recipient
  // Wait, let's just intercept the API directly instead of full UI automation if UI is too complex,
  // but let's try UI.
  // Wait, I can just write a python script to simulate the API calls!
  console.log('UI automation is hard for drag/drop recipients.');
  await browser.close();
})();
