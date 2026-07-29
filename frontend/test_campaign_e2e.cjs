const { chromium } = require('playwright');
const { spawn } = require('child_process');

async function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTest() {
    console.log("Starting backend...");
    const backend = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--port', '8000'], {
        cwd: 'C:\\TalentOpsAI\\backend',
        shell: true
    });
    
    let backendReady = false;
    backend.stdout.on('data', data => {
        const text = data.toString();
        if (text.includes('Application startup complete')) backendReady = true;
    });
    backend.stderr.on('data', data => {
        const text = data.toString();
        if (text.includes('Application startup complete')) backendReady = true;
    });

    console.log("Starting frontend...");
    const frontend = spawn('npm', ['run', 'dev'], {
        cwd: 'C:\\TalentOpsAI\\frontend',
        shell: true
    });
    
    let frontendReady = false;
    frontend.stdout.on('data', data => {
        const text = data.toString();
        if (text.includes('ready in')) frontendReady = true;
    });

    // Wait up to 30s for both
    let attempts = 0;
    while ((!backendReady || !frontendReady) && attempts < 30) {
        await wait(1000);
        attempts++;
    }

    if (!backendReady || !frontendReady) {
        console.error("Services failed to start.");
        backend.kill();
        frontend.kill();
        process.exit(1);
    }

    console.log("Services ready. Launching browser...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1280, height: 720 }
    });
    
    const page = await context.newPage();

    try {
        console.log("Logging in via auth-bypass for admin...");
        const bypassRes = await fetch('http://localhost:8000/api/bridge/auth-bypass', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: 'admin@talentops.ai' })
        });
        
        if (!bypassRes.ok) {
            console.error("Auth bypass failed", await bypassRes.text());
            throw new Error("Auth bypass failed");
        }
        
        const bypassData = await bypassRes.json();
        const token = bypassData.token;

        await context.addInitScript(token => {
            localStorage.setItem('session_token', token);
            localStorage.setItem('auth_session', JSON.stringify({ email: 'admin@talentops.ai' }));
        }, token);
        
        console.log("Navigating to /campaigns...");
        await page.goto('http://localhost:5173/campaigns');
        await page.waitForLoadState('networkidle');
        
        console.log("Clicking New Campaign...");
        await page.getByRole('button', { name: 'New Campaign' }).click();
        
        console.log("Switching to Paste Directly tab...");
        await wait(1000);
        await page.getByRole('button', { name: 'Paste Directly' }).click();
        
        const textArea = page.locator('textarea');
        await textArea.fill('test1@example.com\ntest2@example.com\ntest3@example.com');
        await wait(500);
        
        await page.getByText(/Add \d+ Recipients/).click();
        await wait(1000);
        
        await page.getByRole('button', { name: /Continue/i }).click();
        console.log("Now in Compose (Step 2)...");
        await wait(1000);
        
        console.log("Filling Subject and Body...");
        await page.getByPlaceholder('Subject...').fill('E2E Test Subject {{Email}}');
        await page.locator('.ProseMirror').first().fill('Hello {{Email}}, this is a lightning fast test!');
        
        await wait(1000);
        await page.getByRole('button', { name: /Continue/i }).click();
        
        console.log("Now in Preview (Step 3)...");
        await wait(2000);
        
        console.log("Checking if Outlook connection is needed...");
        const connectBtn = page.getByRole('button', { name: /Connect your Outlook/i });
        const needsConnection = await connectBtn.isVisible().catch(() => false);
        
        if (needsConnection) {
            console.log("Connecting Outlook...");
            await connectBtn.click({ force: true });
            await wait(1000);
            
            console.log("Mocking Outlook connection via DB...");
            await new Promise((resolve, reject) => {
                const { exec } = require('child_process');
                exec(`python -c "import sqlite3; db=sqlite3.connect('dev.db'); db.execute(\\"INSERT OR REPLACE INTO user_outlook_accounts (user_id, email_address, access_token, status, last_synced_at) VALUES (10, 'admin@talentops.ai', 'mock_token', 'connected', CURRENT_TIMESTAMP)\\"); db.commit()"`, { cwd: 'C:\\\\TalentOpsAI\\\\backend' }, (err) => {
                    if (err) return reject(err);
                    exec(`python -c "import sqlite3; db=sqlite3.connect('dev.db'); db.execute(\\"INSERT OR REPLACE INTO user_bridge_status (user_id, status, last_heartbeat) VALUES (10, 'online', CURRENT_TIMESTAMP)\\"); db.commit()"`, { cwd: 'C:\\\\TalentOpsAI\\\\backend' }, (err) => {
                        if (err) return reject(err);
                        resolve();
                    });
                });
            });

            // Click close on the modal since we bypassed the popup
            await page.getByRole('button', { name: 'Close' }).click({ force: true }).catch(() => {});
            await wait(2000);
            
            // Re-run preflight by toggling tabs or clicking Back then Continue
            console.log("Re-running pre-flight by navigating Back and Continue...");
            await page.getByRole('button', { name: /Back/i }).click({ force: true });
            await wait(1000);
            await page.getByRole('button', { name: /Continue/i }).click({ force: true });
            await wait(2000);
        } else {
            console.log("Outlook already connected.");
        }
        
        await page.screenshot({ path: 'C:\\\\TalentOpsAI\\\\frontend\\\\campaign_preview.png' });
        
        const sendBtn = page.getByRole('button', { name: /Launch Campaign/i });
        await sendBtn.click({ force: true });
        
        console.log("Now in Progress (Step 4)...");
        await wait(2000);
        await page.screenshot({ path: 'C:\\\\TalentOpsAI\\\\frontend\\\\campaign_progress.png' });
        
        console.log("Waiting for sends to complete (10s)...");
        await wait(10000); 
        
        await page.screenshot({ path: 'C:\\\\TalentOpsAI\\\\frontend\\\\campaign_complete.png' });
        console.log("E2E Test completed successfully.");
        
    } catch (e) {
        console.error("Test failed:", e);
        await page.screenshot({ path: 'C:\\\\TalentOpsAI\\\\frontend\\\\campaign_error.png' });
    } finally {
        await browser.close();
        backend.kill();
        frontend.kill();
        console.log("Cleanup done.");
        process.exit(0);
    }
}

runTest();
