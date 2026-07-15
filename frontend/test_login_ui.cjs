const puppeteer = require('puppeteer');

(async () => {
    console.log("Starting browser...");
    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    
    await page.setViewport({ width: 1280, height: 800 });
    
    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));

    try {
        console.log("Navigating directly to protected route (/admin/visitor-analytics)...");
        await page.goto('http://localhost:5173/admin/visitor-analytics', { waitUntil: 'networkidle0' });
        
        console.log("Current URL after direct access attempt:", page.url());
        
        // Take a screenshot to see what is being rendered
        await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/af41bbca-eae6-4fe8-82b8-160609b01afb/debug_redirect.png' });

        if (!page.url().includes('/login')) {
            console.log("BUG: Not redirected to login with redirect param! URL is:", page.url());
            return;
        }
        console.log("Successfully redirected to login page with redirect param.");

        console.log("Typing credentials...");
        await page.type('input[type="email"]', 'admin@talentops.com');
        await page.type('input[type="password"]', 'password123');

        console.log("Clicking sign in...");
        
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(e => console.log("No navigation event.")),
            page.click('button[type="submit"]')
        ]);
        
        console.log("Current URL after login:", page.url());
        
        if (page.url().includes('/login')) {
            console.log("Failed to login! Stopping.");
            return;
        }

        if (page.url().includes('/admin/visitor-analytics')) {
            console.log("SUCCESS: Deep linking worked! Returned to /admin/visitor-analytics after login.");
        } else {
            console.log("BUG: Did not return to visitor analytics. URL is:", page.url());
        }

    } catch (e) {
        console.error("Test failed with exception:", e);
    } finally {
        await browser.close();
        console.log("Browser closed.");
    }
})();


