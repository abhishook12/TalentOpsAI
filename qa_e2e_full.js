const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://talent-ops-ai.vercel.app';
const TEST_EMAIL = 'admin@talentops.com';
const TEST_PASS = 'password123';
const RECIPIENT_EMAIL = 'admin@talentops.com';
const ARTIFACTS_DIR = path.join(process.env.USERPROFILE || 'C:\\Users\\User', '.gemini', 'antigravity', 'brain', 'af41bbca-eae6-4fe8-82b8-160609b01afb');

async function runTest() {
    console.log('--- Starting Full E2E Production Verification ---');
    console.log(`Time: ${new Date().toISOString()}`);
    console.log(`URL: ${BASE_URL}`);
    
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    
    let networkLogs = [];
    let consoleLogs = [];
    
    page.on('request', req => networkLogs.push(`REQ: ${req.method()} ${req.url()}`));
    page.on('response', res => networkLogs.push(`RES: ${res.status()} ${res.url()}`));
    page.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`));
    
    const takeScreenshot = async (name) => {
        const filepath = path.join(ARTIFACTS_DIR, `${name}.png`);
        await page.screenshot({ path: filepath });
        console.log(`Screenshot saved: ${name}.png`);
    };

    try {
        // 1. Login
        console.log('Logging in...');
        await page.goto(`${BASE_URL}/login`);
        await page.waitForTimeout(2000);
        await takeScreenshot('01_login_page');
        
        await page.fill('input[type="email"]', TEST_EMAIL);
        await page.fill('input[type="password"]', TEST_PASS);
        await page.click('button[type="submit"]');
        await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
        console.log('Login successful.');
        await takeScreenshot('02_dashboard');
        
        // 2. Navigate to Campaigns
        console.log('Navigating to Campaigns...');
        await page.goto(`${BASE_URL}/campaigns`);
        await page.waitForSelector('text=New Campaign', { state: 'visible' });
        await takeScreenshot('03_campaigns_list');
        
        // 3. Create New Campaign
        console.log('Starting Campaign Wizard...');
        await page.click('text=New Campaign');
        await page.waitForSelector('text=Manual', { state: 'visible' });
        await takeScreenshot('04_wizard_start');
        
        // 4. Add Recipient
        console.log('Adding recipient...');
        await page.click('button:has-text("Manual")');
        await page.waitForTimeout(500);
        await page.fill('textarea', RECIPIENT_EMAIL);
        await page.waitForTimeout(500);
        await page.click('button:has-text("Validate & Add")');
        
        // Wait for validation to complete
        await page.waitForSelector('text=Selected Recipients (1)', { timeout: 15000 });
        await takeScreenshot('05_recipient_validated');
        
        await page.click('button:has-text("Continue")');
        
        // 5. Compose
        console.log('Composing email...');
        await page.waitForSelector('text=Campaign Settings', { state: 'visible' });
        await takeScreenshot('06_compose_start');
        
        // Fill subject
        const uniqueSubject = `E2E Production Test ${Date.now()}: {{FirstName}}`;
        const subjectInput = await page.$('input[placeholder*="subject"]');
        if (subjectInput) {
            await subjectInput.fill(uniqueSubject);
        } else {
            // fallback
            await page.fill('input[type="text"]', uniqueSubject);
        }
        
        // Fill body (contenteditable in Tiptap)
        await page.click('.tiptap');
        await page.keyboard.type('Hello {{FirstName}},\n\nThis is an automated E2E test verifying the campaign system on production.\n\nBest,\nQA Bot');
        
        await takeScreenshot('07_compose_filled');
        await page.click('button:has-text("Continue")');
        
        // 6. Preview & Preflight
        console.log('Previewing campaign...');
        await page.waitForSelector('text=Launch Campaign', { state: 'visible' });
        await page.waitForTimeout(2000); // let preflight finish
        await takeScreenshot('08_preview');
        
        // 7. Launch
        console.log('Launching campaign...');
        await page.click('button:has-text("Launch Campaign")');
        await page.waitForTimeout(3000);
        await takeScreenshot('09_launched');
        
        // Wait for it to switch to progress/send step
        console.log('Checking progress...');
        await page.waitForSelector('text=Delivery Logs', { timeout: 15000 });
        await takeScreenshot('10_delivery_logs');
        
        console.log('Waiting for campaign to send (up to 30s)...');
        await page.waitForTimeout(15000);
        await takeScreenshot('11_delivery_progress');
        
        fs.writeFileSync(path.join(ARTIFACTS_DIR, 'test_subject.txt'), uniqueSubject);
        
        // Save logs
        fs.writeFileSync(path.join(ARTIFACTS_DIR, 'e2e_network.log'), networkLogs.join('\n'));
        fs.writeFileSync(path.join(ARTIFACTS_DIR, 'e2e_console.log'), consoleLogs.join('\n'));
        console.log('Logs saved.');
        console.log('--- E2E Test Completed Successfully ---');
        
    } catch (err) {
        console.error('Test Failed:', err);
        await takeScreenshot('ERROR_STATE');
        fs.writeFileSync(path.join(ARTIFACTS_DIR, 'e2e_network.log'), networkLogs.join('\n'));
        fs.writeFileSync(path.join(ARTIFACTS_DIR, 'e2e_console.log'), consoleLogs.join('\n'));
        process.exit(1);
    } finally {
        await browser.close();
    }
}

runTest();
