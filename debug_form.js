const puppeteer = require('puppeteer');

const TARGET_URL = 'https://talent-ops-lp24stqwk-abhishek-s-projects10.vercel.app';

async function runAudit() {
    console.log(`Starting Production Audit against ${TARGET_URL}...`);
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
    page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));
    page.on('requestfailed', request => {
        console.log('BROWSER REQUEST FAILED:', request.url(), request.failure().errorText);
    });

    const timestamp = Date.now();
    const testEmail = `qa_test_${timestamp}@example.com`;
    const testPassword = 'Password123!';
    
    console.log('Test 1: Load Register Page');
    await page.goto(`${TARGET_URL}/register`);
    await page.waitForSelector('.auth-form');
    
    const inputs = await page.$$('input.auth-input');
    await inputs[0].type('QA');
    await inputs[1].type('Test');
    
    await page.type('input[type="email"]', testEmail);
    const pwdInputs = await page.$$('input[type="password"]');
    await pwdInputs[0].type(testPassword);
    await pwdInputs[1].type(testPassword);
    
    // Checkbox is usually type checkbox but it might be labeled
    await page.click('input[type="checkbox"]');
    
    // Now evaluate button state
    const buttonState = await page.evaluate(() => {
        const btn = document.querySelector('button[type="submit"]');
        return {
            disabled: btn.disabled,
            text: btn.innerText
        };
    });
    console.log('Button state:', buttonState);

    if (buttonState.disabled) {
        // Find what's missing
        const errorText = await page.evaluate(() => {
            const err = document.querySelector('.auth-error');
            return err ? err.innerText : 'No visible .auth-error';
        });
        console.log('Visible error:', errorText);
    } else {
        await page.click('button[type="submit"]');
        
        try {
            await page.waitForFunction(
                () => window.location.pathname === '/' || window.location.pathname === '/login' || document.querySelector('.auth-error') !== null,
                { timeout: 10000 }
            );
            
            const url = page.url();
            const err = await page.evaluate(() => {
                const e = document.querySelector('.auth-error');
                return e ? e.innerText : null;
            });
            console.log('Post-submit state. URL:', url, 'Error:', err);
        } catch(e) {
            console.log('Timeout waiting for redirect or error');
        }
    }
    
    await browser.close();
}

runAudit().catch(console.error);
