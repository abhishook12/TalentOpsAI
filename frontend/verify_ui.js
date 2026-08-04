import puppeteer from 'puppeteer';
import path from 'path';
import fs from 'fs';

const url = 'http://localhost:5173/campaigns';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  await page.setViewport({ width: 1280, height: 800 });

  // Pass 1
  console.log('Running Check 1...');
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.screenshot({ path: 'check1_campaigns.png' });
  
  // Pass 2
  console.log('Running Check 2 (Clicking New Campaign)...');
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const newBtn = buttons.find(b => b.textContent.includes('New Campaign'));
    if (newBtn) newBtn.click();
  });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: 'check2_wizard.png' });

  // Pass 3
  console.log('Running Check 3 (Transition to Compose)...');
  await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const nextBtn = buttons.find(b => b.textContent.includes('Continue'));
    if (nextBtn) nextBtn.click();
  });
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: 'check3_compose.png' });

  await browser.close();
  console.log('All 3 checks complete!');
})();
