import asyncio
from playwright.async_api import async_playwright
import os
import time

BASE_URL = 'https://talent-ops-ai.vercel.app'
SCREENSHOT_DIR = 'C:/TalentOpsAI/UAT_screenshots'

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

errors = []
console_logs = []

async def test_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(record_video_dir=SCREENSHOT_DIR, viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        page.on('console', lambda msg: console_logs.append(f'[{msg.type}] {msg.text}') if msg.type in ['error', 'warning'] else None)
        page.on('pageerror', lambda err: errors.append(f'[PAGE ERROR] {err.message}'))
        page.on('requestfailed', lambda req: errors.append(f'[REQ FAILED] {req.url} - {req.failure}'))

        print(f"Loading {BASE_URL}...")
        await page.goto(BASE_URL)
        
        # 1. Login as Master Admin
        print("Logging in as Master Admin...")
        await page.goto(f'{BASE_URL}/login')
        await page.fill('input[type="email"]', 'abhishekjadon824@gmail.com')
        await page.fill('input[type="password"]', 'Admin@1234')
        await page.click('button[type="submit"]')
        await page.wait_for_url(f'{BASE_URL}/', timeout=15000)
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f'{SCREENSHOT_DIR}/01_admin_dashboard.png')

        # 2. Navigation Audit
        print("Auditing Admin Navigation...")
        admin_links = [
            '/admin',
            '/admin/users',
            '/admin/visitor-analytics',
            '/activity',
            '/admin/health',
            '/admin/settings'
        ]

        for link in admin_links:
            await page.goto(f'{BASE_URL}{link}')
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f'{SCREENSHOT_DIR}/02_admin_nav_{link.replace("/", "_")}.png')
            content = await page.content()
            if "Not Found" in content or "404" in content:
                errors.append(f"[NOT FOUND] Route {link} returned Not Found")

        print("Master Admin tests completed.")

        # Logout
        await page.click('button:has-text("Sign Out")')
        await page.wait_for_url(f'{BASE_URL}/login', timeout=10000)
        await page.wait_for_timeout(1000)

        # 3. Test Normal User RBAC
        print("Logging in as Normal User...")
        await page.goto(f'{BASE_URL}/register')
        await page.fill('input[placeholder*="First Name"]', 'Test')
        await page.fill('input[placeholder*="Last Name"]', 'User')
        await page.fill('input[type="email"]', 'testuser_uat@example.com')
        await page.fill('input[type="password"]', 'TestUser@1234')
        
        # Try to register, if fails (already exists), just login
        try:
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)
        except:
            pass

        await page.goto(f'{BASE_URL}/login')
        await page.fill('input[type="email"]', 'testuser_uat@example.com')
        await page.fill('input[type="password"]', 'TestUser@1234')
        await page.click('button[type="submit"]')
        
        try:
            await page.wait_for_url(f'{BASE_URL}/', timeout=10000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f'{SCREENSHOT_DIR}/03_normal_user_dashboard.png')
            
            # Normal user allowed links
            await page.goto(f'{BASE_URL}/campaigns')
            await page.wait_for_timeout(1000)
            await page.screenshot(path=f'{SCREENSHOT_DIR}/04_normal_user_campaigns.png')

            await page.goto(f'{BASE_URL}/recruiters')
            await page.wait_for_timeout(1000)
            await page.screenshot(path=f'{SCREENSHOT_DIR}/05_normal_user_recruiters.png')

        except Exception as e:
            errors.append(f"[LOGIN FAILED] Could not log in as normal user: {e}")

        print("Checking RBAC for normal user...")
        for link in admin_links:
            await page.goto(f'{BASE_URL}{link}')
            await page.wait_for_timeout(1500)
            await page.screenshot(path=f'{SCREENSHOT_DIR}/06_rbac_{link.replace("/", "_")}.png')
            
            # Since non-admin might just be redirected, let's check current URL or content
            content = await page.content()
            if link in page.url and ("Command Center" in content or "Visitor Analytics" in content):
                errors.append(f"[RBAC FAILED] Normal user accessed admin content at {link}")
                
        await browser.close()

        print("--------------------")
        print("ERRORS FOUND:")
        for e in errors:
            print(e)
        print("--------------------")
        
        with open('C:/TalentOpsAI/uat_results.txt', 'w') as f:
            f.write("ERRORS:\n")
            f.write(str(errors))
            f.write("\n\nCONSOLE:\n")
            f.write(str(console_logs))

asyncio.run(test_all())
