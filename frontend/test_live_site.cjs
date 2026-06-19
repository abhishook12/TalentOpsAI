const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Navigating to live site...');
  await page.goto('https://talent-ops-ai.vercel.app/admin', { waitUntil: 'domcontentloaded' });
  
  // Wait a couple seconds to let React render
  await new Promise(r => setTimeout(r, 3000));

  // If redirected to login
  if (page.url().includes('/admin-login')) {
    console.log('Logging in...');
    await page.type('input[type="password"]', '1012');
    await page.click('button[type="submit"]');
    await new Promise(r => setTimeout(r, 5000));
  }

  console.log('Currently at:', page.url());
  
  // Wait for dashboard to load completely by waiting for the number to be > 0 or loading to finish
  console.log('Waiting for data to load...');
  await page.waitForFunction(() => {
    // This assumes there's an element showing the count. It might take a few seconds to fetch.
    const elements = document.querySelectorAll('div, span, h1, h2, h3, h4, p');
    for (let el of elements) {
      if (el.innerText && el.innerText.includes('99,088')) return true;
      if (el.innerText && el.innerText.includes('Total Recruiters') && el.innerText.match(/\d+,\d+/)) return true;
    }
    return false;
  }, { timeout: 15000 }).catch(() => console.log('Data wait timeout, taking screenshot anyway'));

  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: 'live_dashboard_screenshot.jpg' });
  console.log('Took dashboard screenshot');
  
  try {
    // Click review panel button
    await page.waitForSelector('button[title="Open the review queue"]', { timeout: 5000 });
    await page.click('button[title="Open the review queue"]');
    console.log('Clicked Review Panel button');
    
    // Wait for the modal and specifically for it to STOP saying "Loading"
    await new Promise(r => setTimeout(r, 4000));
    
    await page.screenshot({ path: 'live_review_panel_screenshot.jpg' });
    console.log('Took review panel screenshot');
    
    const modalContent = await page.evaluate(() => {
      const modal = document.querySelector('div[style*="z-index: 1990"]');
      return modal ? modal.innerText : 'Modal not found';
    });
    console.log('Modal text:', modalContent.replace(/\n/g, ' '));
    
  } catch (e) {
    console.log('Could not find Review Panel button', e);
  }

  await browser.close();
})();
