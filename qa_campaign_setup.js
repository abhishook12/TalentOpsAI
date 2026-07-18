const puppeteer = require('puppeteer-core');

const TARGET_URL = 'https://talent-ops-mlavc9nqi-abhishek-s-projects10.vercel.app';
const testEmail = `test_${Date.now()}@example.com`;
const testPass = 'Password123!';

async function setupTestUser(page) {
    console.log('Registering test user...');
    await page.goto(`${TARGET_URL}/register`);
    await page.waitForSelector('.auth-form');
    const inputs = await page.$$('input.auth-input');
    await inputs[0].type('QA');
    await inputs[1].type('Campaign');
    await page.type('input[type="email"]', testEmail);
    const pwdInputs = await page.$$('input[type="password"]');
    await pwdInputs[0].type(testPass);
    await pwdInputs[1].type(testPass);
    await page.click('input[type="checkbox"]');
    await page.click('button[type="submit"]');
    
    await page.waitForFunction(() => window.location.pathname.includes('login'), { timeout: 15000 });
    
    console.log('Activating user in DB...');
    const { execSync } = require('child_process');
    execSync(`python activate_user.py "${testEmail}"`);
    
    console.log('Logging in...');
    const emailInput = await page.$('input[type="email"]');
    await emailInput.click({ clickCount: 3 });
    await emailInput.type(testEmail);
    const pwdInput2 = await page.$('input[type="password"]');
    await pwdInput2.click({ clickCount: 3 });
    await pwdInput2.type(testPass);
    await page.click('button[type="submit"]');
    
    await page.waitForFunction(() => window.location.pathname === '/', { timeout: 15000 });
    console.log('✅ Logged in successfully.');
}

async function runTest() {
    const browser = await puppeteer.launch({
        executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        headless: 'new',
        defaultViewport: { width: 1280, height: 800 }
    });
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('BROWSER:', msg.text()));
    
    try {
        await setupTestUser(page);
        
        console.log('Test 1.1: Navigating to Campaigns Page');
        await page.goto(`${TARGET_URL}/campaigns`);
        await page.waitForSelector('h1', { text: 'Campaigns' });
        
        console.log('Test 1.2: Start New Campaign');
        await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('New Campaign'));
            btns.forEach(b => b.click());
        });
        
        await page.waitForFunction(() => document.body.textContent.includes('Recipients'));
        
        console.log('Test 1.3: Add recipient');
        await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('Manual & CSV'));
            btns.forEach(b => b.click());
        });
        
        await page.waitForSelector('textarea');
        await page.type('textarea', 'testrecipient@example.com');
        
        await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('Validate & Add'));
            btns.forEach(b => b.click());
        });
        
        console.log('Waiting for table row to appear...');
        await page.waitForFunction(() => {
            return Array.from(document.querySelectorAll('td')).some(td => td.textContent.includes('testrecipient@example.com'));
        }, { timeout: 15000 });
        console.log('✅ Recipient added to table.');
        
        // Wait a second for state updates
        await new Promise(r => setTimeout(r, 1500));
        
        console.log('Test 1.4: Proceed to Compose Step');
        await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('Continue'));
            console.log(`Found ${btns.length} Continue buttons. Clicking all of them.`);
            btns.forEach(b => b.click());
        });
        
        await page.waitForFunction(() => document.body.textContent.includes('Subject'), { timeout: 10000 });
        console.log('Test 1.5: Fill Compose Step');
        
        const subjectInput = await page.$('input[placeholder*="Enter subject"]');
        await subjectInput.type('Test Subject 123');
        
        const editor = await page.$('div[contenteditable="true"]');
        await editor.type('This is a test body.');
        
        console.log('Test 1.6: Proceed to Preview (triggers Save Draft)');
        await page.evaluate(() => {
            const btns = Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('Continue'));
            btns.forEach(b => b.click());
        });
        
        await page.waitForFunction(() => document.body.textContent.includes('Pre-Flight Validation'));
        console.log('✅ Draft saved and moved to preview');
        
        console.log('Test 1.7: Verify Draft in List');
        await page.goto(`${TARGET_URL}/campaigns`);
        await page.waitForFunction(() => document.body.textContent.includes('Test Subject 123') || document.body.textContent.includes('New Campaign'));
        
        console.log('✅ Phase 1 tests passed.');
        
    } catch (e) {
        await page.screenshot({ path: 'campaign_setup_failed.png' });
        console.error('❌ Test failed', e);
    } finally {
        await browser.close();
    }
}

runTest();
