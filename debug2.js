const puppeteer = require('puppeteer-core');

(async () => {
    const browser = await puppeteer.launch({
        executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        headless: false
    });
    const page = await browser.newPage();
    const testEmail = "qa_test_1784341253419@example.com";
    await page.goto('https://talent-ops-mlavc9nqi-abhishek-s-projects10.vercel.app/login?redirect=%2F');
    const wait = (ms) => new Promise(res => setTimeout(res, ms));
    await wait(2000);
    
    // Clear and type
    await page.click('input[type="email"]', { clickCount: 3 });
    await page.keyboard.press('Backspace');
    await page.type('input[type="email"]', testEmail);

    await page.click('input[type="password"]', { clickCount: 3 });
    await page.keyboard.press('Backspace');
    await page.type('input[type="password"]', 'StrongPass1!');

    await page.screenshot({ path: 'before_login_submit.png' });
    
    await page.click('button[type="submit"]');

    // Wait and check error
    await wait(3000);
    await page.screenshot({ path: 'after_login_submit.png' });
    const errorEl = await page.$('.text-red-500');
    if (errorEl) {
        const text = await page.evaluate(el => el.textContent, errorEl);
        console.log("Login result URL:", page.url(), "Error:", text);
    } else {
        const url = page.url();
        console.log("No error found, URL:", url);
        if (url !== 'https://talent-ops-mlavc9nqi-abhishek-s-projects10.vercel.app/') {
            const body = await page.evaluate(() => document.body.innerHTML);
            console.log("Body length:", body.length);
        }
    }
    await browser.close();
})();
