const puppeteer = require('puppeteer-core');

(async () => {
    const browser = await puppeteer.launch({
        executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        headless: false
    });
    const page = await browser.newPage();
    
    // Inject script to expose TanStack Router
    await page.goto('https://talent-ops-mlavc9nqi-abhishek-s-projects10.vercel.app/login?redirect=%2F', { waitUntil: 'networkidle0' });
    
    const searchVal = await page.evaluate(() => {
        return window.location.search;
    });
    console.log("Search string:", searchVal);

    // Let's just type the email to bypass any form issues, but click forgot password to see if it navigates!
    await page.click('a[href="/forgot-password"]');
    await page.waitForTimeout(1000);
    console.log("URL after clicking forgot password:", page.url());

    await browser.close();
})();
