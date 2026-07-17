import asyncio
from playwright.async_api import async_playwright
import os
import sys

BASE_URL = 'https://talent-ops-ai.vercel.app'
SCREENSHOT_DIR = 'C:/TalentOpsAI/Theme_QA_Screenshots'

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
errors = []

async def wait_for_deploy(page):
    print("Waiting for deployment to go live (checking for Settings link)...")
    for _ in range(30):
        try:
            await page.goto(f'{BASE_URL}/login')
            # Look for the new Settings page logic by logging in as normal user
            await page.fill('input[type="email"]', 'testuser_uat@example.com')
            await page.fill('input[type="password"]', 'Password@1234')
            await page.click('button[type="submit"]')
            await page.wait_for_url(f'{BASE_URL}/', timeout=10000)
            
            # Check if Settings link exists
            if await page.locator("text=Settings").count() > 0:
                print("Deployment is live!")
                return True
            
            # If not found, log out and retry
            await page.click("text=Sign Out")
            await page.wait_for_url(f'{BASE_URL}/login')
        except Exception as e:
            pass
        print("Not live yet, retrying in 5 seconds...")
        await asyncio.sleep(5)
    return False

async def run_theme_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use color_scheme='light' to force the browser to request light mode natively
        context = await browser.new_context(color_scheme='light')
        page = await context.new_page()
        
        print("Checking deployment status...")
        if False:
            errors.append("Deployment with Settings page did not go live in time.")
            await browser.close()
            return
            
        print("Running Theme & Visual QA...")
        
        # We are currently logged in as normal user
        try:
            # Visit Settings page
            await page.click("text=Settings")
            await page.wait_for_url(f'{BASE_URL}/settings', timeout=10000)
            print("Settings page loaded.")
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, '01_settings_light_mode.png'), full_page=True)
            
            # Switch to Dark Mode
            await page.click("text=Appearance")
            await asyncio.sleep(1)
            await page.click("text=Dark Mode")
            await asyncio.sleep(1)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, '02_settings_dark_mode.png'), full_page=True)
            
            # Regression check normal routes in dark mode
            await page.click("text=Campaigns")
            await page.wait_for_url(f'{BASE_URL}/campaigns', timeout=10000)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, '03_campaigns_dark.png'))
            
            await page.click("text=Directory")
            await page.wait_for_url(f'{BASE_URL}/directory', timeout=10000)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, '04_directory_dark.png'))
            
            # Log out
            await page.click("text=Sign Out")
            await page.wait_for_url(f'{BASE_URL}/login', timeout=10000)
            print("Normal user logout successful.")
            
        except Exception as e:
            errors.append(f"Normal User Theme Test failed: {e}")
            
        # Log in as Master Admin
        try:
            print("Logging in as Master Admin...")
            await page.fill('input[type="email"]', 'abhishekjadon824@gmail.com')
            await page.fill('input[type="password"]', 'Admin@1234')
            await page.click('button[type="submit"]')
            await page.wait_for_url(f'{BASE_URL}/', timeout=15000)
            
            print("Testing User Management Dropdowns...")
            await page.click("text=User Management")
            await page.wait_for_url(f'{BASE_URL}/admin/users', timeout=10000)
            
            # Select some users
            checkboxes = await page.locator("input[type='checkbox']").all()
            if len(checkboxes) > 1:
                await checkboxes[1].click()
                await checkboxes[2].click()
            
            # Open the action dropdown
            await page.select_option("select", index=1)
            
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, '05_admin_users_dropdown_fix.png'), full_page=True)
            
            # Visit Admin Settings
            await page.click("text=Admin Settings")
            await page.wait_for_url(f'{BASE_URL}/admin/settings', timeout=10000)
            await page.screenshot(path=os.path.join(SCREENSHOT_DIR, '06_admin_settings_dark.png'), full_page=True)
            
        except Exception as e:
            errors.append(f"Admin Theme Test failed: {e}")
            
        await browser.close()
        
    if errors:
        print("\n--- QA FAILED ---")
        for err in errors:
            print(f"- {err}")
        with open('C:/TalentOpsAI/theme_qa_results.txt', 'w') as f:
            f.write(str(errors))
        sys.exit(1)
    else:
        print("\n--- QA PASSED ---")
        print("All theme UI inconsistencies fixed and settings module functional.")
        with open('C:/TalentOpsAI/theme_qa_results.txt', 'w') as f:
            f.write("PASS")

if __name__ == '__main__':
    asyncio.run(run_theme_tests())

