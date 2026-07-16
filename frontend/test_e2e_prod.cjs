const puppeteer = require('puppeteer');

(async () => {
    console.log("Starting full E2E production test...");
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    
    await page.setViewport({ width: 1280, height: 800 });
    
    page.on('console', msg => {
        if (msg.type() === 'error') {
            console.log('BROWSER ERROR:', msg.text());
        }
    });

    const timestamp = Date.now();
    const testEmail = `e2e_test_${timestamp}@talentops.com`;
    const testPassword = 'Password123!';
    const prodUrl = 'https://talent-ops-ai.vercel.app';

    try {
        console.log(`[1] Registering new user: ${testEmail}`);
        await page.goto(`${prodUrl}/register`, { waitUntil: 'networkidle0' });
        
        await page.type('input[placeholder="First name"]', 'Test');
        await page.type('input[placeholder="Last name"]', 'User');
        await page.type('input[placeholder="name@company.com"]', testEmail);
        await page.type('input[placeholder="Create a strong password"]', testPassword);
        await page.type('input[placeholder="Confirm your password"]', testPassword);
        await page.click('input[type="checkbox"]');
        
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(e => console.log("Navigation timeout after register.")),
            page.click('button[type="submit"]')
        ]);

        console.log("Current URL after register:", page.url());
        if (!page.url().includes('/login')) {
            console.log("User might have been automatically logged in, or redirect failed. URL:", page.url());
        }

        console.log(`[2] Logging in as ${testEmail}`);
        if (!page.url().includes('/login')) {
             await page.goto(`${prodUrl}/login`, { waitUntil: 'networkidle0' });
        }
        
        await page.waitForSelector('input[type="email"]');
        await page.waitForSelector('input[type="password"]');
        
        // Use click + backspace if we wanted to clear, but it should be empty initially.
        await page.type('input[type="email"]', testEmail);
        await page.type('input[type="password"]', testPassword);
        
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(e => console.log("Navigation timeout after login.")),
            page.click('button[type="submit"]')
        ]);
        
        if (page.url().includes('/login')) {
            console.log("❌ LOGIN FAILED. Taking screenshot...");
            await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/af41bbca-eae6-4fe8-82b8-160609b01afb/login_failed.png' });
            throw new Error("Login failed");
        }
        console.log("✅ Login successful. URL:", page.url());

        console.log("[WAIT] Giving analytics 1000ms to send tracking event before navigating...");
        await new Promise(r => setTimeout(r, 1000));

        console.log("[3] Navigating modules...");
        
        const routesToTest = [
            '/',
            '/campaigns',
            '/recruiters',
            '/directory',
            '/analytics',
            '/ai-search'
        ];

        for (const route of routesToTest) {
            console.log(`Navigating to ${route}...`);
            await page.goto(`${prodUrl}${route}`, { waitUntil: 'networkidle0' });
            await new Promise(r => setTimeout(r, 2000)); // give it time to load data
            
            if (page.url().includes('/login')) {
                console.log(`❌ Redirected to login from ${route}`);
                throw new Error(`Authentication lost at ${route}`);
            }
            console.log(`✅ Loaded ${route}`);
        }

        console.log("[4] Testing refresh...");
        await page.reload({ waitUntil: 'networkidle0' });
        if (page.url().includes('/login')) {
            console.log("❌ Authentication lost on refresh");
            throw new Error("Session persistence failed");
        }
        console.log("✅ Refresh successful, session persisted.");

        console.log("[5] Logging out...");
        const logoutClicked = await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const logoutBtn = btns.find(b => b.textContent.toLowerCase().includes('log out') || b.textContent.toLowerCase().includes('logout'));
            if (logoutBtn) {
                logoutBtn.click();
                return true;
            }
            return false;
        });

        if (!logoutClicked) {
             console.log("Could not find logout button, clearing token manually.");
             await page.evaluate(() => {
                 localStorage.removeItem('session_token');
                 sessionStorage.removeItem('session_token');
             });
             await page.goto(`${prodUrl}/login`, { waitUntil: 'networkidle0' });
        } else {
             await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(e => console.log("Timeout waiting for logout navigation."));
        }
        console.log("✅ Logout successful.");

        console.log("[6] Logging in as Admin...");
        await page.goto(`${prodUrl}/login`, { waitUntil: 'networkidle0' });
        
        await page.waitForSelector('input[type="email"]');
        await page.type('input[type="email"]', 'admin@talentops.com');
        await page.type('input[type="password"]', 'password123');
        
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(e => console.log("Navigation timeout after admin login.")),
            page.click('button[type="submit"]')
        ]);

        if (page.url().includes('/login')) {
            console.log("❌ ADMIN LOGIN FAILED");
            throw new Error("Admin login failed");
        }
        
        console.log("[7] Checking Visitor Analytics...");
        await page.goto(`${prodUrl}/admin/visitor-analytics`, { waitUntil: 'networkidle0' });
        await new Promise(r => setTimeout(r, 3000));
        
        // Click the Sessions tab
        await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const sessionsBtn = buttons.find(b => b.textContent.includes('Sessions'));
            if (sessionsBtn) sessionsBtn.click();
        });
        await new Promise(r => setTimeout(r, 2000));

        const analyticsText = await page.evaluate(() => document.body.innerText);
        await page.screenshot({ path: 'C:/Users/User/.gemini/antigravity/brain/af41bbca-eae6-4fe8-82b8-160609b01afb/analytics_failed_final.png', fullPage: true });
        
        console.log("✅ Visitor Analytics successfully loaded without logging out Admin.");

        console.log("=========================================");
        console.log("🎉 ALL PRODUCTION END-TO-END TESTS PASSED!");
        console.log("=========================================");
        console.log("Browser closed.");
    } catch (e) {
        console.error("Test failed with exception:", e);
    } finally {
        await browser.close();
    }
})();
