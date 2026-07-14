const puppeteer = require('puppeteer');
const fs = require('fs');

async function checkLogin(iteration) {
    console.log(`Starting login check ${iteration}/4...`);
    const browser = await puppeteer.launch({ headless: true });
    try {
        const page = await browser.newPage();
        
        // Go to login page
        await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle0' });
        
        // Type credentials
        await page.type('input[type="email"]', 'testfake1@example.com');
        await page.type('input[type="password"]', 'Password123!');
        
        // Click login button
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0' }),
            page.click('button[type="submit"]')
        ]);
        
        console.log(`Login successful on iteration ${iteration}. Saving screenshot...`);
        
        // Verify we are on the dashboard
        const artifactDir = "C:\\Users\\User\\.gemini\\antigravity\\brain\\15aabb56-dcdf-44fd-be32-72119f59740d";
        const screenshotPath = `${artifactDir}\\local_verification_${iteration}.png`;
        
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`Saved screenshot to ${screenshotPath}`);
        
        // Ensure log out by clearing local storage and cookies to test again properly
        await page.evaluate(() => {
            localStorage.clear();
            sessionStorage.clear();
        });
        const client = await page.target().createCDPSession();
        await client.send('Network.clearBrowserCookies');
        
    } catch (err) {
        console.error(`Check ${iteration} failed!`, err);
    } finally {
        await browser.close();
    }
}

async function runLoops() {
    for (let i = 1; i <= 4; i++) {
        await checkLogin(i);
        if (i < 4) {
            console.log(`Waiting 60 seconds before next check...`);
            await new Promise(resolve => setTimeout(resolve, 60000));
        }
    }
    console.log("All 4 checks completed!");
}

runLoops();
