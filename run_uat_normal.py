import asyncio
from playwright.async_api import async_playwright
import os
import time

BASE_URL = 'https://talent-ops-ai.vercel.app'
SCREENSHOT_DIR = 'C:/TalentOpsAI/UAT_screenshots'

errors = []

async def test_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        print("Logging in as Normal User...")
        await page.goto(f'{BASE_URL}/login')
        await page.fill('input[type="email"]', 'testuser_uat@example.com')
        await page.fill('input[type="password"]', 'TestUser@1234')
        await page.click('button[type="submit"]')
        
        try:
            # Wait for dashboard
            await page.wait_for_selector('text=TalentOps AI', timeout=15000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f'{SCREENSHOT_DIR}/03_normal_user_dashboard.png')
            print("Normal user login successful.")
        except Exception as e:
            errors.append(f"[LOGIN FAILED] Could not log in as normal user: {e}")

        admin_links = [
            '/admin',
            '/admin/users',
            '/admin/visitor-analytics',
            '/admin/health',
            '/admin/settings'
        ]

        print("Checking RBAC for normal user...")
        for link in admin_links:
            await page.goto(f'{BASE_URL}{link}')
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f'{SCREENSHOT_DIR}/06_rbac_{link.replace("/", "_")}.png')
            
            content = await page.content()
            if "Not Found" in content or "Access Denied" not in content:
                pass
            if link in page.url and ("Command Center" in content or "User Management" in content):
                errors.append(f"[RBAC FAILED] Normal user accessed admin content at {link}")
                
        await browser.close()
        
        with open('C:/TalentOpsAI/uat_normal_results.txt', 'w') as f:
            f.write(str(errors))

asyncio.run(test_all())
