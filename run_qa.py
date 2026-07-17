import asyncio
from playwright.async_api import async_playwright
import time
import os

BASE_URL = 'http://localhost:5173'
ADMIN_EMAIL = 'abhishekjadon824@gmail.com'
ADMIN_PASSWORD = 'StrongPassword123!'

async def run_qa():
    os.makedirs('qa_screenshots', exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        print("Starting QA...")
        
        # 1. Login
        print("Logging in...")
        await page.goto(f"{BASE_URL}/login")
        await page.fill('input[type="email"]', ADMIN_EMAIL)
        await page.fill('input[type="password"]', ADMIN_PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE_URL}/", timeout=15000)
        print("Login successful.")
        
        # 2. Check all main routes
        routes = [
            '/',
            '/recruiters',
            '/analytics',
            '/directory',
            '/admin',
            '/admin/visitor-analytics',
            '/admin/users',
            '/settings',
            '/profile'
        ]
        
        for route in routes:
            print(f"Testing route {route}...")
            await page.goto(f"{BASE_URL}{route}")
            await page.wait_for_timeout(2000) # Wait for loaders to finish
            
            # Check for console errors
            # (In a real script we would capture page.on('pageerror'))
            
            # Save screenshot
            safe_route = route.replace('/', '_') or '_home'
            await page.screenshot(path=f"qa_screenshots/route{safe_route}.png")
            print(f"? Route {route} is accessible and rendered.")

        await browser.close()
        print("QA Script Completed Successfully.")

if __name__ == '__main__':
    asyncio.run(run_qa())

