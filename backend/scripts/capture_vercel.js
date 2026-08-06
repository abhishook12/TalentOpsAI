const puppeteer = require('puppeteer');

(async () => {
    console.log("Launching headless browser...");
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();
    
    // Set viewport to 1080p
    await page.setViewport({ width: 1920, height: 1080 });
    
    console.log("Navigating to https://talent-ops-ai.vercel.app ...");
    await page.goto('https://talent-ops-ai.vercel.app', { waitUntil: 'networkidle2' });
    
    console.log("Checking if we are on the login page...");
    // Check if there is an email input
    const emailInput = await page.$('input[type="email"]');
    if (emailInput) {
        console.log("Login page detected. Attempting to log in...");
        await page.type('input[type="email"]', 'admin@talentops.com');
        
        // Wait for a bit, then type password
        const passwordInput = await page.$('input[type="password"]');
        if (passwordInput) {
            await page.type('input[type="password"]', 'admin123456');
        }
        
        // Find login button and click
        const buttons = await page.$$('button');
        for (const btn of buttons) {
            const text = await page.evaluate(el => el.innerText, btn);
            if (text.toLowerCase().includes('sign in') || text.toLowerCase().includes('login') || text.toLowerCase().includes('continue')) {
                console.log("Clicking login button...");
                await btn.click();
                break;
            }
        }
        
        // Wait for dashboard to load
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 }).catch(e => console.log("Navigation timeout, proceeding..."));
    }
    
    console.log("Waiting for data to load on the dashboard...");
    let found = false;
    for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 10000));
        
        const bodyText = await page.evaluate(() => document.body.innerText);
        if (bodyText.includes('351,228')) {
            console.log("SUCCESS! Found the number 351,228 on the page.");
            found = true;
            break;
        }
        
        console.log("Not found yet, clicking Refresh Data...");
        const buttons = await page.$$('button');
        for (const btn of buttons) {
            const text = await page.evaluate(el => el.innerText, btn);
            if (text && text.includes('Refresh Data')) {
                await btn.click();
                break;
            }
        }
    }
    
    console.log("Taking screenshot...");
    const screenshotPath = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\e050007d-77bf-4880-ac17-0d8a6b8d4518\\vercel_real_proof_final.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });

    await browser.close();
    console.log(`Screenshot saved to ${screenshotPath}`);
})();
