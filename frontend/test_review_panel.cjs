const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.toString()));
  page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure().errorText));

  await page.goto('http://localhost:5173/admin', { waitUntil: 'networkidle0' });
  
  if (page.url().includes('/admin-login')) {
    await page.type('input[type="password"]', 'admin123'); // assuming standard dev password
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
  }

  console.log('Currently at:', page.url());
  
  try {
    await page.waitForSelector('button[title="Open the review queue"]', { timeout: 5000 });
    await page.click('button[title="Open the review queue"]');
    console.log('Clicked Review Panel button');
    
    // wait 5 seconds for it to load
    await new Promise(r => setTimeout(r, 5000));
    
    const modalContent = await page.evaluate(() => {
      const modal = document.querySelector('div[style*="z-index: 1990"]');
      return modal ? modal.innerText : 'Modal not found';
    });
    console.log('Modal text after 5 seconds:', modalContent.replace(/\n/g, ' '));
    
  } catch (e) {
    console.log('Could not find Review Panel button', e);
  }

  await browser.close();
})();
