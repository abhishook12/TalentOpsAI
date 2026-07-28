import asyncio
import json
import requests
import time
from playwright.async_api import async_playwright

ADMIN_EMAIL = "admin@talentops.com"
ADMIN_PASSWORD = "Password123!"
TARGET_URL = "https://talent-ops-ai.vercel.app/login?redirect=%2F"
API_URL = "https://talentopsai-1.onrender.com"

async def test_scenario_1_and_3_times(iteration):
    user_email = f"test_user_{iteration}@example.com"
    print(f"\n--- Running Full Scenario Test - Iteration {iteration}/3 ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create a unique device fingerprint by changing the User-Agent
        context = await browser.new_context(user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 PlaywrightTestRun/{iteration}")
        page = await context.new_page()
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.type}: {msg.text}"))
        
        # Step 1: Open login page
        print("1. Opening login page...")
        await page.goto(TARGET_URL)
        await page.wait_for_selector("input[type='email']")
        
        # Step 2: Login as normal user to trigger approval
        print(f"2. Entering credentials for normal user {user_email}...")
        
        # Now admin logs in via API to clear their own devices
        print("2.5 Admin clearing their own devices...")
        sess = requests.Session()
        res = sess.post(f"{API_URL}/auth/login", json={
            "email": ADMIN_EMAIL, 
            "password": ADMIN_PASSWORD,
            "remember_me": False
        })
        if res.status_code != 200:
            print(f"Admin login failed: {res.status_code} {res.text}")
        
        # We need the access_token cookie, which requests handles
        res = sess.get(f"{API_URL}/admin/devices/")
        if res.status_code != 200:
            print(f"Admin devices failed: {res.status_code} {res.text}")
        devices = res.json()
        if isinstance(devices, list):
            for d in devices:
                if d.get("user_email") == user_email:
                    sess.delete(f"{API_URL}/admin/devices/{d['id']}/sessions")
        
        # Clear playwright cookies and local storage just in case
        await context.clear_cookies()
        await page.goto(TARGET_URL)
        await page.wait_for_selector("input[type='email']")

        await page.fill("input[type='email']", user_email)
        await page.fill("input[type='password']", ADMIN_PASSWORD)

        await page.click("button.login-button-primary")
        
        print("3. Waiting for Approval Screen...")
        try:
            await page.wait_for_selector("text=Waiting for administrator approval", timeout=15000)
            print("Approval screen detected!")
        except Exception as e:
            print(f"Approval screen not found: {e}")
            await browser.close()
            return False
            
        print("4. Admin logs in via API to approve the device...")
        sess = requests.Session()
        res = sess.post(f"{API_URL}/auth/login", json={
            "email": ADMIN_EMAIL, 
            "password": ADMIN_PASSWORD,
            "remember_me": False
        })
        if res.status_code != 200:
            print(f"Admin login failed: {res.text}")
            await browser.close()
            return False
            
        # We need the access_token cookie, which requests handles
        res = sess.get(f"{API_URL}/admin/devices/")
        if res.status_code != 200:
            print(f"Failed to fetch devices: {res.text}")
            await browser.close()
            return False
            
        devices = res.json()
        target_device = None
        for d in devices:
            if d.get("user_email") == user_email and d.get("status") == "Pending":
                target_device = d
                break
                
        if not target_device:
            print("Device not found in admin list!")
            await browser.close()
            return False
            
        print(f"5. Admin approves device {target_device['id']}...")
        res = sess.put(f"{API_URL}/admin/devices/{target_device['id']}/status", json={"status": "Trusted"})
        if res.status_code != 200:
            print(f"Admin approval failed: {res.text}")
            await browser.close()
            return False
            
        print("6. Waiting for Dashboard redirect on frontend...")
        try:
            await page.wait_for_url("https://talent-ops-ai.vercel.app/", timeout=20000)
            print("Redirected to Dashboard successfully!")
        except Exception as e:
            print(f"Did not redirect to dashboard: {e}")
            await page.screenshot(path=f"iteration_{iteration}_failed.png")
            await browser.close()
            return False
            
        # Verify dashboard loaded
        try:
            await page.wait_for_selector("text=Dashboard", timeout=10000)
            print("Dashboard loaded successfully.")
        except Exception as e:
            print(f"Dashboard element not found: {e}")
            await page.screenshot(path=f"iteration_{iteration}_dashboard_failed.png")
            await browser.close()
            return False
            
        print(f"Iteration {iteration} PASSED")
        await browser.close()
        return True

async def run_all():
    for i in range(1, 4):
        success = await test_scenario_1_and_3_times(i)
        if not success:
            print(f"FAILED on iteration {i}")
            return
    print("\nALL 3 ITERATIONS PASSED - 100% SUCCESS")

if __name__ == "__main__":
    asyncio.run(run_all())
