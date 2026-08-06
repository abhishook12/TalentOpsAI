const puppeteer = require('puppeteer');

async function runCheck(attempt) {
    console.log(`\n=== CHECK ATTEMPT ${attempt} ===`);
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 900 });

    // 1. Go to login
    console.log('Step 1: Navigating to login...');
    await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle2', timeout: 15000 });

    // Screenshot: Login page
    const loginScreenshot = `C:/Users/User/.gemini/antigravity/brain/e050007d-77bf-4880-ac17-0d8a6b8d4518/login_page_${attempt}.png`;
    await page.screenshot({ path: loginScreenshot });
    console.log(`Login page screenshot saved: ${loginScreenshot}`);

    // 2. Fill credentials
    console.log('Step 2: Filling credentials...');
    await page.type('input[type="email"]', 'admin@talentops.com');
    await page.type('input[type="password"]', '1012');

    // 3. Click the Login button
    await page.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const loginBtn = btns.find(b => b.innerText.includes('Login'));
        if (loginBtn) loginBtn.click();
    });

    // 4. Wait for the URL to change (SPA redirect)
    console.log('Step 3: Waiting for redirect...');
    await page.waitForFunction(
        () => !window.location.pathname.includes('/login'),
        { timeout: 15000 }
    ).catch(() => console.log('URL did not change from /login'));

    // 5. Wait a bit for page to settle
    await new Promise(r => setTimeout(r, 3000));

    // 6. Check current URL and page text
    const currentUrl = page.url();
    console.log(`Current URL: ${currentUrl}`);

    const bodyText = await page.evaluate(() => document.body.innerText);
    console.log(`Page text (first 500 chars): ${bodyText.substring(0, 500)}`);

    // Check if there's an unlock code screen
    if (bodyText.includes('Unlock') || bodyText.includes('unlock') || bodyText.includes('Access Code')) {
        console.log('UNLOCK SCREEN DETECTED — entering unlock code...');
        const unlockInput = await page.$('input[type="text"], input[type="password"]');
        if (unlockInput) {
            await unlockInput.type('10dec2000');
            await page.evaluate(() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const unlockBtn = btns.find(b => b.innerText.includes('Unlock') || b.innerText.includes('Submit') || b.innerText.includes('Enter'));
                if (unlockBtn) unlockBtn.click();
            });
            await new Promise(r => setTimeout(r, 3000));
        }
    }

    // 7. Wait longer for dashboard data
    await new Promise(r => setTimeout(r, 5000));

    const finalUrl = page.url();
    const finalText = await page.evaluate(() => document.body.innerText);
    console.log(`Final URL: ${finalUrl}`);
    console.log(`Final text (first 800 chars): ${finalText.substring(0, 800)}`);

    // 8. Extract total recruiters
    const match = finalText.match(/TOTAL RECRUITERS\s*\n?\s*([\d,]+)/i) 
               || finalText.match(/Total Recruiters\s*\n?\s*([\d,]+)/i)
               || finalText.match(/([\d,]{5,})\s*\n?\s*Real database count/i);
    const totalText = match ? match[1] : 'NOT FOUND';
    console.log(`Extracted Total Recruiters: ${totalText}`);

    const numericValue = parseInt(totalText.replace(/,/g, ''), 10);
    const passed = numericValue > 2000000;
    console.log(`Numeric: ${numericValue} | > 2M? ${passed}`);

    // 9. Screenshot
    const screenshotPath = `C:/Users/User/.gemini/antigravity/brain/e050007d-77bf-4880-ac17-0d8a6b8d4518/dashboard_proof_${attempt}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`Dashboard screenshot: ${screenshotPath}`);

    await browser.close();
    return { attempt, totalText, numericValue, passed, screenshotPath };
}

async function main() {
    console.log('=== 3x VERIFICATION PROTOCOL ===\n');
    const results = [];

    for (let i = 1; i <= 3; i++) {
        try {
            const r = await runCheck(i);
            results.push(r);
        } catch (e) {
            console.error(`Attempt ${i} ERROR: ${e.message}`);
            results.push({ attempt: i, passed: false, error: e.message });
        }
    }

    console.log('\n=== FINAL RESULTS ===');
    results.forEach(r => {
        if (r.error) {
            console.log(`  Check ${r.attempt}: FAILED (${r.error})`);
        } else {
            console.log(`  Check ${r.attempt}: ${r.passed ? 'PASSED' : 'FAILED'} — Dashboard shows: ${r.totalText}`);
        }
    });

    const allPassed = results.every(r => r.passed);
    console.log(`\n${allPassed ? 'ALL 3 CHECKS PASSED' : 'VERIFICATION INCOMPLETE — see details above'}`);
}

main();
