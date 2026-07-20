import { chromium } from 'playwright';
import fs from 'fs';

async function profileRoute(page, url, name) {
  console.log(`Profiling ${name} at ${url}...`);
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  
  // Wait for network idle or 5 seconds max
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  
  const metrics = await page.evaluate(() => {
    const perfData = window.performance.getEntriesByType("navigation")[0];
    const paintData = window.performance.getEntriesByType("paint");
    
    let fcp = 0;
    for (const entry of paintData) {
      if (entry.name === 'first-contentful-paint') {
        fcp = entry.startTime;
      }
    }
    
    return {
      loadEventEnd: perfData ? perfData.loadEventEnd : 0,
      fcp: fcp,
      domInteractive: perfData ? perfData.domInteractive : 0
    };
  });
  
  console.log(`--- ${name} ---`);
  console.log(`FCP: ${metrics.fcp.toFixed(2)} ms`);
  console.log(`DOM Interactive: ${metrics.domInteractive.toFixed(2)} ms`);
  console.log(`Full Load: ${metrics.loadEventEnd.toFixed(2)} ms`);
  console.log('\n');
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Login first
  await page.goto('http://localhost:5173/login');
  await page.fill('input[type="email"]', 'admin@talentops.com');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000); // wait for login
  
  console.log("=== FRONTEND UI PROFILING ===");
  
  await profileRoute(page, 'http://localhost:5173/', 'Dashboard');
  await profileRoute(page, 'http://localhost:5173/recruiters', 'Recruiters');
  await profileRoute(page, 'http://localhost:5173/campaigns', 'Campaigns');
  await profileRoute(page, 'http://localhost:5173/analytics', 'Analytics');
  
  await browser.close();
})();
