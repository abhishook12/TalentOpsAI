const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const ARTIFACTS_DIR = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\af41bbca-eae6-4fe8-82b8-160609b01afb';
const BASE_URL = 'http://localhost:5173';

async function run() {
    const browser = await puppeteer.launch({ headless: "new", defaultViewport: { width: 1280, height: 800 } });
    const page = await browser.newPage();
    
    console.log("Taking screenshot of Login Page...");
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' });
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'auth_login_page.png') });
    
    console.log("Taking screenshot of Register Page...");
    await page.goto(`${BASE_URL}/register`, { waitUntil: 'networkidle2' });
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'auth_register_page.png') });
    
    console.log("Taking screenshot of Forgot Password Page...");
    await page.goto(`${BASE_URL}/forgot-password`, { waitUntil: 'networkidle2' });
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'auth_forgot_password_page.png') });

    console.log("Taking screenshot of Reset Password Page...");
    await page.goto(`${BASE_URL}/reset-password`, { waitUntil: 'networkidle2' });
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'auth_reset_password_page.png') });

    console.log("Taking screenshot of Verify Email Page...");
    await page.goto(`${BASE_URL}/verify-email`, { waitUntil: 'networkidle2' });
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'auth_verify_email_page.png') });
    
    console.log("Filling out registration...");
    await page.goto(`${BASE_URL}/register`, { waitUntil: 'networkidle2' });
    await page.type('input[placeholder="First name"]', 'John');
    await page.type('input[placeholder="Last name"]', 'Doe');
    await page.type('input[type="email"]', 'johndoe12345@example.com');
    await page.type('input[placeholder="Company name"]', 'Acme Corp');
    await page.type('input[placeholder="Create a password"]', 'StrongPass!1234');
    await page.type('input[placeholder="Confirm password"]', 'StrongPass!1234');
    await page.click('input[type="checkbox"]');
    
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle2' });
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'auth_registration_success.png') });

    await browser.close();
    console.log("Screenshots captured successfully.");
}

run().catch(console.error);
