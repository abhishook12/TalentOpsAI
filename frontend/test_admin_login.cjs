const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ 
        headless: 'new', 
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        defaultViewport: { width: 1366, height: 768 }
    });
    const page = await browser.newPage();
    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const prodUrl = 'https://talent-ops-ai.vercel.app';
    const screenshotDir = 'C:/Users/User/.gemini/antigravity/brain/af41bbca-eae6-4fe8-82b8-160609b01afb/';
    const testEmail = 'uat_test_1784228866643@talentops.com';

    try {
        console.log(`[1] Logging in as Admin...`);
        await page.goto(`${prodUrl}/login`, { waitUntil: 'networkidle0' });
        await wait(2000);
        
        await page.type('input[type="email"]', 'admin@talentops.com');
        await page.type('input[type="password"]', 'adminpassword');
        
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(e => console.log("Nav timeout ok.")),
            page.click('button[type="submit"]')
        ]);
        await wait(4000);
        
        console.log("[2] Checking Visitor Analytics...");
        await page.goto(`${prodUrl}/admin/visitor-analytics`, { waitUntil: 'networkidle0' });
        await wait(5000);
        await page.screenshot({ path: `${screenshotDir}uat_11_admin_analytics_dashboard.png`, fullPage: true });
        
        // Click Sessions tab
        await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const sessBtn = btns.find(b => b.textContent.includes('Sessions'));
            if (sessBtn) sessBtn.click();
        });
        await wait(4000);
        await page.screenshot({ path: `${screenshotDir}uat_12_admin_analytics_sessions.png`, fullPage: true });
        
        const pageText = await page.evaluate(() => document.body.innerText);
        if (pageText.includes(testEmail)) {
            console.log("✅ Admin Visitor Analytics recorded the test user!");
        } else {
            console.log("❌ Admin Visitor Analytics DID NOT record the test user.");
        }
    } catch(e) {
        console.error(e);
    } finally {
        await browser.close();
    }
})();
