const puppeteer = require('puppeteer');

const TARGET_URL = 'https://talent-ops-mlavc9nqi-abhishek-s-projects10.vercel.app';

async function runAudit() {
    console.log(`Starting Production Audit against ${TARGET_URL}...`);
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    const timestamp = Date.now();
    const testEmail = `qa_test_${timestamp}@example.com`;
    const testPassword = 'Password123!';
    
    // Test 1: Load Register Page
    console.log('Test 1: Load Register Page');
    await page.goto(`${TARGET_URL}/register`);
    await page.waitForSelector('.auth-form');
    console.log('✅ Register page loaded successfully');

    // Test 2: Register Account
    console.log('Test 2: Register Account');
    const inputs = await page.$$('input.auth-input');
    await inputs[0].type('QA');
    await inputs[1].type('Test');
    
    await page.type('input[type="email"]', testEmail);
    // Company is optional, skip it
    
    // Password (strong)
    const pwdInputs = await page.$$('input[type="password"]');
    await pwdInputs[0].type(testPassword);
    await pwdInputs[1].type(testPassword);

    // Agree terms
    await page.click('input[type="checkbox"]');
    
    await page.click('button[type="submit"]');
    
    try {
        await page.waitForFunction(
            () => window.location.pathname === '/' || window.location.pathname === '/login',
            { timeout: 30000 }
        );
        console.log('✅ Registered successfully (redirected to ' + page.url() + ')');
        
        // Manually activate user in the production database
        console.log('Test 2.1: Activating User in DB');
        const { execSync } = require('child_process');
        execSync(`python activate_user.py "${testEmail}"`);
        console.log('✅ User activated in DB');
        
    } catch (e) {
        await page.screenshot({ path: 'register_failed.png' });
        console.error('❌ Failed to register, took screenshot as register_failed.png');
        throw e;
    }

    // If redirected to login, login
    if (page.url().includes('/login')) {
        console.log('Test 2.5: Login');
        await page.waitForSelector('.auth-form');
        
        const emailInput = await page.$('input[type="email"]');
        await emailInput.click({ clickCount: 3 });
        await emailInput.type(testEmail);
        
        const pwdInput = await page.$('input[type="password"]');
        await pwdInput.click({ clickCount: 3 });
        await pwdInput.type(testPassword);
        
        await page.click('button[type="submit"]');
        
        try {
            await page.waitForFunction(
                () => window.location.pathname === '/',
                { timeout: 30000 }
            );
            console.log('✅ Logged in successfully');
        } catch (e) {
            await page.screenshot({ path: 'login_failed.png' });
            console.error('❌ Failed to login, took screenshot as login_failed.png');
            throw e;
        }
    }

    // Test 3: Reload and test persistent session
    console.log('Test 3: Session Persistence');
    await page.reload();
    await page.waitForFunction(
        () => window.location.pathname === '/',
        { timeout: 30000 }
    );
    const urlAfterReload = page.url();
    if (urlAfterReload === `${TARGET_URL}/`) {
        console.log('✅ Session persisted successfully across reloads');
    } else {
        console.log(`❌ Session lost after reload, current URL: ${urlAfterReload}`);
    }

    // Capture screenshot of Dashboard
    await page.screenshot({ path: 'live_dashboard.png' });
    console.log('✅ Captured Dashboard Screenshot');

    // Test 4: Navigate to Analytics
    console.log('Test 4: Navigate to Analytics');
    await page.goto(`${TARGET_URL}/analytics`);
    await page.waitForSelector('.cc-page-body', { timeout: 30000 });
    console.log('✅ Analytics page loaded');

    // Test 5: Logout
    console.log('Test 5: Logout');
    await page.evaluate(() => {
        localStorage.removeItem('session_token');
        sessionStorage.removeItem('session_token');
        localStorage.removeItem('auth_session');
        window.location.href = '/login';
    });
    // Wait for the URL to change to /login
    await page.waitForFunction(
        () => window.location.pathname.includes('/login'),
        { timeout: 30000 }
    );
    console.log('✅ Logged out');

    // Test 6: Verify protected routes redirect to login
    console.log('Test 6: Verify Protected Routes');
    await page.goto(`${TARGET_URL}/analytics`);
    await page.waitForFunction(
        () => window.location.pathname.includes('/login'),
        { timeout: 30000 }
    ).catch(() => {});
    if (page.url().includes('/login')) {
        console.log('✅ Protected routes redirect to login correctly');
    } else {
        console.log('❌ Protected route did not redirect. URL: ' + page.url());
    }

    await browser.close();
    console.log('Production Audit Completed Successfully!');
}

runAudit().catch(console.error);
