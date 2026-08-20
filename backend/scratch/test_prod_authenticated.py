import asyncio
import os
import sys
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\be5e058f-502c-416d-a76d-db5d160f0985"
PROD_URL = "https://talent-ops-ai.vercel.app"

async def test_prod_authenticated():
    print("Testing live Vercel production with authentication...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1600, 'height': 1050})
        page = await context.new_page()

        page.on('console', lambda msg: print(f"[PROD CONSOLE] {msg.type}: {msg.text}"))
        page.on('response', lambda resp: print(f"[PROD HTTP {resp.status}] {resp.url}") if resp.status >= 400 or 'recruiters' in resp.url else None)

        print("1. Navigating to login...")
        await page.goto(f"{PROD_URL}/login", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # Log in via UI
        email_input = page.locator('input[type="email"], input[placeholder*="company"]').first
        pass_input = page.locator('input[type="password"]').first
        
        await email_input.fill("abhishekjadon824@gmail.com")
        await pass_input.fill("1012")
        
        login_btn = page.locator('button:has-text("Login to TalentOps"), button:has-text("Sign in")').first
        await login_btn.click()
        await asyncio.sleep(4)

        print("2. Navigating to /recruiters on production...")
        await page.goto(f"{PROD_URL}/recruiters", wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # Check for error banners
        error_banner = page.locator('text="Failed to load recruiters"')
        err_count = await error_banner.count()
        print(f"Error Banner Count on Production: {err_count}")

        # Check rows
        rows = await page.locator('tbody tr').count()
        print(f"Rendered Recruiter Rows on Production: {rows}")

        screenshot_path = os.path.join(ARTIFACT_DIR, "prod_live_recruiters_success.png")
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Screenshot saved: {screenshot_path}")

        # Test Search on Production
        print("3. Navigating to /search on production...")
        await page.goto(f"{PROD_URL}/search", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        search_input = page.locator('input[placeholder*="Search"], input[type="text"]').first
        await search_input.fill("Aaron Dehart")
        await page.keyboard.press("Enter")
        await asyncio.sleep(4)

        search_screenshot = os.path.join(ARTIFACT_DIR, "prod_live_search_success.png")
        await page.screenshot(path=search_screenshot, full_page=False)
        print(f"Search screenshot saved: {search_screenshot}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_prod_authenticated())
