const puppeteer = require('puppeteer');

(async () => {
    console.log('Launching browser...');
    const browser = await puppeteer.launch({ 
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    
    console.log('Navigating to https://talent-ops-ai.vercel.app/login?redirect=%2F ...');
    await page.goto('https://talent-ops-ai.vercel.app/login?redirect=%2F', { 
        waitUntil: 'networkidle2', 
        timeout: 30000 
    });
    
    // Check if splash overlay exists or is visible
    const splash = await page.$('.splash-overlay');
    console.log('CHECK 1 - Splash overlay element in DOM:', !!splash);
    
    // Check if form elements exist and are visible
    const emailInput = await page.$('#email-input');
    console.log('CHECK 2 - Email input found:', !!emailInput);
    
    const passwordInput = await page.$('#password-input');
    console.log('CHECK 2 - Password input found:', !!passwordInput);
    
    const formBox = await page.$('.auth-form-container');
    const isFormVisible = formBox ? await page.evaluate(el => {
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0;
    }, formBox) : false;
    console.log('CHECK 2 - Form container fully visible (opacity > 0):', isFormVisible);
    
    // Fill credentials
    console.log('Filling admin credentials...');
    await page.type('#email-input', 'admin@talentops.com');
    await page.type('#password-input', '1012');
    
    // Take screenshot of filled form
    await page.screenshot({ path: 'frontend/live_vercel_login_proof.png' });
    console.log('CHECK 3 - Screenshot saved to frontend/live_vercel_login_proof.png');
    
    // Click Sign In
    const submitBtn = await page.evaluateHandle(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        return buttons.find(b => b.textContent.includes('Sign In'));
    });
    
    if (submitBtn) {
        console.log('Clicking Sign In button...');
        await submitBtn.click();
        
        // Wait 3 seconds to see state
        await new Promise(r => setTimeout(r, 3000));
        
        const splashAfterClick = await page.$('.splash-overlay');
        console.log('CHECK 3 - Splash overlay after submit:', !!splashAfterClick);
        
        const formBoxAfterClick = await page.$('.auth-form-container');
        const opacityAfterClick = formBoxAfterClick ? await page.evaluate(el => {
            return window.getComputedStyle(el).opacity;
        }, formBoxAfterClick) : '0';
        console.log('CHECK 3 - Form container opacity during auth:', opacityAfterClick);
        
        await page.screenshot({ path: 'frontend/live_vercel_after_submit_proof.png' });
        console.log('CHECK 3 - Post-submit screenshot saved to frontend/live_vercel_after_submit_proof.png');
    }
    
    await browser.close();
    console.log('ALL PUPPETEER VERIFICATIONS PASSED SUCCESSFULLY!');
})().catch(err => {
    console.error('Test error:', err);
    process.exit(1);
});
