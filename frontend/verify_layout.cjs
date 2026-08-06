const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:5173/register');
  await page.waitForTimeout(1000);
  
  // Find First Name label and input
  const labelBox = await page.evaluate(() => {
    const label = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('First name'));
    return label ? label.getBoundingClientRect() : null;
  });
  
  const inputBox = await page.evaluate(() => {
    const input = document.querySelector('input[placeholder="First name"]');
    return input ? input.getBoundingClientRect() : null;
  });
  
  console.log('Label Box:', labelBox);
  console.log('Input Box:', inputBox);
  
  if (labelBox && inputBox) {
    if (labelBox.bottom <= inputBox.top) {
      console.log('SUCCESS: Label is strictly above Input (No vertical overlap)');
    } else {
      console.log('ERROR: Label overlaps or is below Input vertically');
    }
    
    if (labelBox.left === inputBox.left) {
      console.log('SUCCESS: Label and Input are left-aligned');
    } else {
      console.log('ERROR: Label and Input are NOT left-aligned');
    }
  } else {
    console.log('ERROR: Elements not found');
  }
  
  await browser.close();
})();
