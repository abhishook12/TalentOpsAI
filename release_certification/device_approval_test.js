const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const EVIDENCE_DIR = 'C:\\TalentOpsAI\\release_certification\\evidence';

async function runDeviceTest() {
  console.log("Starting Device Approval Test...");
  const browser = await chromium.launch({ headless: true });
  const context1 = await browser.newContext(); // Admin
  const context2 = await browser.newContext(); // User

  try {
    // 1. Setup - get Admin Token to create a user and approve devices
    const adminPage = await context1.newPage();
    await adminPage.goto('http://localhost:5173/login');
    await adminPage.fill('input[type="email"]', 'admin@talentops.com');
    await adminPage.fill('input[type="password"]', 'Admin@TalentOps2026');
    await adminPage.click('button[type="submit"]');
    await adminPage.waitForTimeout(3000);
    console.log("Admin logged in");

    // Grab admin token from localStorage
    const adminToken = await adminPage.evaluate(() => localStorage.getItem('session_token'));
    
    // Create new user via API
    const userEmail = `device_user_${Date.now()}@talentops.com`;
    const res = await adminPage.request.post('http://localhost:8000/users/', {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: { email: userEmail, password: 'User123!', first_name: 'Device', last_name: 'User', role_id: 2 }
    });
    console.log("User created:", res.status());

    // 2. User tries to log in
    const userPage = await context2.newPage();
    await userPage.goto('http://localhost:5173/login');
    await userPage.fill('input[type="email"]', userEmail);
    await userPage.fill('input[type="password"]', 'User123!');
    await userPage.click('button[type="submit"]');
    
    // Wait for the error or block
    await userPage.waitForTimeout(2000);
    await userPage.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_DEVICE_PENDING.png') });
    console.log("Captured Pending Device Screenshot");

    // 3. Admin Approves Device via API
    const devicesRes = await adminPage.request.get('http://localhost:8000/admin/devices/', {
      headers: { Authorization: `Bearer ${adminToken}` }
    });
    let devices = await devicesRes.json();
    if (devices.devices) devices = devices.devices;
    
    const pendingDevice = devices.find(d => d.status === 'Pending');
    if (pendingDevice) {
      await adminPage.request.put(`http://localhost:8000/admin/devices/${pendingDevice.id}/status`, {
        headers: { Authorization: `Bearer ${adminToken}` },
        data: { status: 'Trusted' }
      });
      console.log("Admin approved device ID:", pendingDevice.id);
    } else {
      console.log("No pending device found! Devices:", devices);
    }

    // 4. User tries to log in again
    await userPage.click('button[type="submit"]');
    await userPage.waitForTimeout(3000);
    await userPage.screenshot({ path: path.join(EVIDENCE_DIR, 'UI_DEVICE_APPROVED.png') });
    console.log("Captured Approved Device Screenshot");

  } catch (e) {
    console.error(e);
  } finally {
    await browser.close();
  }
}

runDeviceTest();
