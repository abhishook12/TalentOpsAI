import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText));

  await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
  
  for (let i = 1; i <= 4; i++) {
    console.log(`Taking screenshot ${i}...`);
    
    // Attempt to hover over the map near bottom center (approximate Texas location)
    // To trigger the tooltip and verify the flipping behavior.
    const mapContainer = await page.$('.rsm-svg');
    if (mapContainer) {
      const box = await mapContainer.boundingBox();
      if (box) {
        await page.mouse.move(box.x + box.width * 0.48, box.y + box.height * 0.85);
        await new Promise(r => setTimeout(r, 500)); // wait for transition
      }
    }
    
    await page.screenshot({ path: `../.agents/screenshot_${i}.png`, fullPage: true });
    if (i < 4) {
      console.log('Waiting 60 seconds...');
      await new Promise(r => setTimeout(r, 60000));
    }
  }
  
  console.log('Done!');
  await browser.close();
})();
