const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const TEST_EMAIL = 'admin@talentops.com';
const TEST_PASS = '1012';

async function runTest(iteration) {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
        console.log(`[Run ${iteration}] Logging in...`);
        await page.goto(`${BASE_URL}/login`);
        await page.fill('input[type="email"]', TEST_EMAIL);
        await page.fill('input[type="password"]', TEST_PASS);
        await page.click('button[type="submit"]');
        await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
        
        console.log(`[Run ${iteration}] Navigating to /recruiters...`);
        await page.goto(`${BASE_URL}/recruiters`);
        
        // Wait for a recruiter to appear in the table or the table to load
        await page.waitForSelector('text=Recruiters', { state: 'visible', timeout: 5000 });
        
        // Check for the crash text "Component crashed"
        const crash = await page.$('text=Component crashed');
        if (crash) {
            throw new Error('Component crashed detected!');
        }

        console.log(`[Run ${iteration}] SUCCESS: Recruiters page loaded without crashing.`);
    } catch (err) {
        console.error(`[Run ${iteration}] Test Failed:`, err);
        process.exit(1);
    } finally {
        await browser.close();
    }
}

async function verify3Times() {
    console.log("Starting 3-time verification...");
    for (let i = 1; i <= 3; i++) {
        await runTest(i);
    }
    console.log("All 3 verification runs passed!");
}

verify3Times();
