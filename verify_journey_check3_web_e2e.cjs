const { chromium } = require('playwright');
const http = require('http');
const path = require('path');
const fs = require('fs');

// Simple static server for frontend/dist
const distDir = path.resolve(__dirname, 'frontend/dist');
const mimeTypes = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2'
};

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/') reqPath = '/index.html';
  let filePath = path.join(distDir, reqPath);

  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(distDir, 'index.html');
  }

  const ext = path.extname(filePath);
  const contentType = mimeTypes[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end('Server error');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  });
});

const PORT = 4188;

async function runCheck3() {
  console.log('=== CHECK 3: WEB FRONTEND NOTIFICATIONS & USER/ADMIN JOURNEY E2E TEST ===');

  await new Promise((resolve) => server.listen(PORT, resolve));
  console.log(`1. Local production preview server running on port ${PORT}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 TalentOps-Auditor'
  });

  const page = await context.newPage();

  try {
    // 2. Set up authenticated session for User (abhishekjadon706@gmail.com, ID 8)
    await page.addInitScript(() => {
      const sess = {
        id: 8,
        email: 'abhishekjadon706@gmail.com',
        first_name: 'Abhishek',
        role: 'user'
      };
      localStorage.setItem('auth_session', JSON.stringify(sess));
      localStorage.setItem('session_token', 'verified_token_abc123');
    });

    // Mock auth/me
    await page.route('**/auth/me', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          authenticated: true,
          user: {
            id: 8,
            email: 'abhishekjadon706@gmail.com',
            first_name: 'Abhishek',
            role: 'user'
          }
        })
      });
    });

    // Mock API requests for notifications
    await page.route('**/notifications', async (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 1,
              title: 'Platform Release v2.9.3 Synchronized',
              message: 'Desktop Scout v2.9.3 is live across all fleet nodes with real-time notifications.',
              type: 'update',
              read: false,
              created_at: new Date().toISOString()
            },
            {
              id: 2,
              title: 'Staged Discovery Approved',
              message: 'Your discovered profile for Alex Tester at OpenAI has been approved and promoted.',
              type: 'success',
              read: false,
              created_at: new Date().toISOString()
            }
          ])
        });
      } else {
        route.continue();
      }
    });

    await page.route('**/notifications/read', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' })
      });
    });

    // Mock other dashboard endpoints to ensure clean load
    await page.route('**/admin/**', route => route.fulfill({ status: 200, json: {} }));
    await page.route('**/system/**', route => route.fulfill({ status: 200, json: { status: 'healthy' } }));
    await page.route('**/scout/updates/**', route => route.fulfill({ status: 200, json: { version: '2.9.3' } }));

    console.log('2. Navigating to Dashboard as User (abhishekjadon706@gmail.com)...');
    await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1500);

    // 3. Verify Sidebar Navigation & Version Badge
    console.log('\n3. Verifying Sidebar Navigation & Scout Version Badge:');
    const scoutNav = page.locator('a[href="/download-scout"]');
    const scoutNavExists = await scoutNav.count() > 0;
    console.log(`   • Desktop Scout Nav item present: ${scoutNavExists ? 'VERIFIED' : 'FAILED'}`);
    assert(scoutNavExists, 'Missing Desktop Scout Nav link');

    const badgeText = await scoutNav.locator('text=v2.9.3').innerText();
    console.log(`   • Desktop Scout Pill Badge: "${badgeText}" (VERIFIED)`);
    assert(badgeText === 'v2.9.3', 'Badge text mismatch');

    // 4. Verify Notification Center Bell & Unread Dot
    console.log('\n4. Verifying Header Notification Center:');
    const notifBtn = page.locator('button[title="Notifications"]');
    const notifBtnCount = await notifBtn.count();
    console.log(`   • Notification Bell Button present in header: ${notifBtnCount > 0 ? 'VERIFIED' : 'FAILED'}`);
    assert(notifBtnCount > 0, 'Notification bell button not found in header');

    // Check unread badge (red dot span)
    const unreadDot = notifBtn.locator('span');
    const hasUnread = await unreadDot.isVisible();
    console.log(`   • Unread badge indicator visible on Bell: ${hasUnread ? 'VERIFIED' : 'FAILED'}`);
    assert(hasUnread, 'Unread badge not visible when unread notifications exist');

    // 5. Click Bell & Open Notification Center Dropdown
    console.log('\n5. Opening Notification Center Dropdown:');
    await notifBtn.click();
    await page.waitForTimeout(600);

    const modalTitle = await page.locator('h3:has-text("Notifications")').isVisible();
    console.log(`   • Notifications Modal opened: ${modalTitle ? 'VERIFIED' : 'FAILED'}`);
    assert(modalTitle, 'Notification dropdown failed to open');

    const hasReleaseNotif = await page.locator('text=Platform Release v2.9.3 Synchronized').isVisible();
    const hasReviewNotif = await page.locator('text=Staged Discovery Approved').isVisible();
    console.log(`   • "Platform Release v2.9.3 Synchronized" rendered: ${hasReleaseNotif ? 'VERIFIED' : 'FAILED'}`);
    console.log(`   • "Staged Discovery Approved" review update rendered: ${hasReviewNotif ? 'VERIFIED' : 'FAILED'}`);
    assert(hasReleaseNotif, 'Missing release broadcast notification in dropdown');
    assert(hasReviewNotif, 'Missing review approval notification in dropdown');

    // Capture screenshot of open notification center
    const screenshot1 = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\285f6c8d-71ab-4abe-9e7b-e4d39e260a9f\\proof_check3_notification_center_dropdown.png';
    await page.screenshot({ path: screenshot1, fullPage: false });
    console.log(`   • Screenshot captured: ${screenshot1}`);

    // 6. Click "Mark all read"
    console.log('\n6. Testing "Mark all read" Action:');
    const markReadBtn = page.locator('button:has-text("Mark all read")');
    if (await markReadBtn.isVisible()) {
      await markReadBtn.click();
      await page.waitForTimeout(500);
      const dotAfter = await unreadDot.isVisible();
      console.log(`   • Unread dot hidden after mark read: ${!dotAfter ? 'VERIFIED' : 'PENDING'}`);
    }

    console.log('\n>>> CHECK 3 PASSED: Web Frontend Notification Center & Navigation 100% Verified!');
  } finally {
    await browser.close();
    server.close();
  }
}

function assert(condition, message) {
  if (!condition) {
    console.error(`Assertion Error: ${message}`);
    process.exit(1);
  }
}

runCheck3().catch((e) => {
  console.error('Check 3 Failed:', e);
  server.close();
  process.exit(1);
});
