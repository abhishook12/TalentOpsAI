const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:5173';
const EVIDENCE_DIR = path.join(__dirname, 'evidence');

if (!fs.existsSync(EVIDENCE_DIR)) {
    fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

async function run() {
    console.log('Starting ATLAS UI Evidence Collection...');
    const browser = await chromium.launch({ headless: true });
    
    // ==========================================
    // ROLE: ADMIN
    // ==========================================
    console.log('\\n--- Testing Admin Role ---');
    let context = await browser.newContext();
    let page = await context.newPage();
    let consoleErrors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(`[Admin] ${msg.text()}`);
    });

    // Login Page
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(2000);
    
    // AC-GLOGIN-001: Google Login button
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_LOGIN_PAGE.png') });
    console.log('Captured: UI_LOGIN_PAGE.png');

    // Perform Admin Login
    await page.fill('input[type="email"]', 'admin@talentops.com');
    await page.fill('input[type="password"]', 'Admin@TalentOps2026');
    await page.click('button[type="submit"]');
    
    // Wait for redirect to dashboard
    await page.waitForURL('**/');
    console.log('Redirected to dashboard successfully.');
    
    // AC-LOGIN-006: Admin Dashboard Redirect
    await page.waitForTimeout(3000); // Wait for charts to load
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_ADMIN_DASHBOARD.png') });
    console.log('Captured: UI_ADMIN_DASHBOARD.png');

    // Campaigns Workflow (AC-CAMP-001)
    await page.goto(`${BASE_URL}/campaigns`);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_CAMPAIGNS_LIST.png') });
    console.log('Captured: UI_CAMPAIGNS_LIST.png');
    
    // Notifications (AC-NOTIF-001)
    // Looking for a bell icon or notifications button, wait for a selector if it exists
    const bellIcon = await page.$('button[aria-label="Notifications"], .lucide-bell');
    if (bellIcon) {
        await bellIcon.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_NOTIFICATIONS_DROPDOWN.png') });
        console.log('Captured: UI_NOTIFICATIONS_DROPDOWN.png');
    } else {
        console.log('Notifications bell not found on this UI.');
    }

    // Save Admin Console Logs
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'ADMIN_CONSOLE_ERRORS.json'), JSON.stringify(consoleErrors, null, 2));
    await context.close();

    // ==========================================
    // ROLE: USER (Non-Admin)
    // ==========================================
    console.log('\\n--- Testing User Role ---');
    context = await browser.newContext();
    page = await context.newPage();
    consoleErrors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(`[User] ${msg.text()}`);
    });

    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(1000);
    
    await page.fill('input[type="email"]', 'user@talentops.com');
    await page.fill('input[type="password"]', 'User@TalentOps2026');
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(3000);
    
    // Check if redirected to login due to device approval
    if (page.url().includes('/login')) {
        console.log('User login blocked by device approval. Approving via Admin API...');
        
        // Login as Admin via API
        const adminLogin = await page.request.post('http://127.0.0.1:8000/auth/login', {
            data: { email: 'admin@talentops.com', password: 'Admin@TalentOps2026' }
        });
        const adminData = await adminLogin.json();
        const adminToken = adminData.access_token;
        
        // Get Pending Devices
        const devicesRes = await page.request.get('http://127.0.0.1:8000/admin/devices/', {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        const devicesData = await devicesRes.json();
        const pendingDevice = devicesData.find(d => d.status === 'Pending');
        
        if (pendingDevice) {
            // Approve Device
            await page.request.put(`http://127.0.0.1:8000/admin/devices/${pendingDevice.id}/status`, {
                headers: { 'Authorization': `Bearer ${adminToken}` },
                data: { status: 'Trusted' }
            });
            console.log('Device approved successfully!');
            
            // Try User Login again
            await page.fill('input[type="email"]', 'user@talentops.com');
            await page.fill('input[type="password"]', 'User@TalentOps2026');
            await page.click('button[type="submit"]');
            await page.waitForURL('**/');
            console.log('User logged in successfully after device approval.');
        }
    }
    
    await page.waitForTimeout(3000);
    const userUrl = page.url();
    console.log(`User redirected to: ${userUrl}`);
    
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_USER_DASHBOARD.png') });
    console.log('Captured: UI_USER_DASHBOARD.png');
    
    fs.writeFileSync(path.join(EVIDENCE_DIR, 'USER_CONSOLE_ERRORS.json'), JSON.stringify(consoleErrors, null, 2));
    await context.close();

    // ==========================================
    // ROLE: FAILED LOGIN (Lockout check AC-LOGIN-005)
    // ==========================================
    console.log('\\n--- Testing Failed Login / Lockout ---');
    context = await browser.newContext();
    page = await context.newPage();
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(1000);
    
    for(let i=1; i<=6; i++) {
        await page.fill('input[type="email"]', 'admin@talentops.com');
        await page.fill('input[type="password"]', 'wrong_pass_' + i);
        await page.click('button[type="submit"]');
        await page.waitForTimeout(1000);
    }
    
    await page.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_LOGIN_LOCKOUT.png') });
    console.log('Captured: UI_LOGIN_LOCKOUT.png (Check if error message shows lockout)');
    
    await context.close();
    await browser.close();
    console.log('\\nATLAS UI Evidence Collection Complete.');
}

run().catch(console.error);
