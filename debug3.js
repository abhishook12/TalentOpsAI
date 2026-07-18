const puppeteer = require('puppeteer-core');

(async () => {
    const browser = await puppeteer.launch({
        executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        headless: false
    });
    const page = await browser.newPage();
    const testEmail = "qa_test_1784341253419@example.com";
    await page.goto('https://talent-ops-mlavc9nqi-abhishek-s-projects10.vercel.app/login?redirect=%2F', { waitUntil: 'networkidle0' });
    
    await page.type('input[type="email"]', testEmail);
    await page.type('input[type="password"]', 'StrongPass1!');
    
    console.log("Button before click:", await page.$eval('button[type="submit"]', el => el.textContent));

    await page.click('button[type="submit"]');

    const wait = (ms) => new Promise(res => setTimeout(res, ms));
    await wait(3000);

    console.log("Button after click:", await page.$eval('button[type="submit"]', el => el.textContent).catch(e => "No button"));

    const errorEl = await page.$('.auth-error');
    if (errorEl) {
        const text = await page.evaluate(el => el.textContent, errorEl);
        console.log("Login result URL:", page.url(), "Error:", text);
    } else {
        console.log("No error found, URL:", page.url());
    }

    await browser.close();
})();
