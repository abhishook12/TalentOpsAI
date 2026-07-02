import asyncio
from playwright.async_api import async_playwright
import os
import shutil

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        print("Navigating to Dashboard...")
        await page.goto("http://localhost:5173")
        await page.wait_for_selector(".cc-topbar", timeout=5000)
        
        # Give it a moment to render dashboard data
        await page.wait_for_timeout(2000)

        # 1. Take Dark Mode screenshot
        dark_path = "C:/Users/User/.gemini/antigravity/brain/15aabb56-dcdf-44fd-be32-72119f59740d/ui_dark_mode.png"
        await page.screenshot(path=dark_path)
        print("Captured dark mode screenshot.")

        # 2. Click Theme Switcher (aria-label="Toggle theme")
        await page.click('button[aria-label="Toggle theme"]')
        await page.wait_for_timeout(1000)
        
        # 3. Take Light Mode screenshot
        light_path = "C:/Users/User/.gemini/antigravity/brain/15aabb56-dcdf-44fd-be32-72119f59740d/ui_light_mode.png"
        await page.screenshot(path=light_path)
        print("Captured light mode screenshot.")

        # 4. Click Notifications button
        await page.click('button[aria-label="Notifications"]')
        await page.wait_for_timeout(1000)
        
        # 5. Take Activity page screenshot
        activity_path = "C:/Users/User/.gemini/antigravity/brain/15aabb56-dcdf-44fd-be32-72119f59740d/ui_activity_page.png"
        await page.screenshot(path=activity_path)
        print(f"Captured Activity page screenshot. Current URL: {page.url}")

        # 6. Click Account button
        await page.click('button[aria-label="Account"]')
        await page.wait_for_timeout(1000)

        # 7. Take Admin page screenshot
        admin_path = "C:/Users/User/.gemini/antigravity/brain/15aabb56-dcdf-44fd-be32-72119f59740d/ui_admin_page.png"
        await page.screenshot(path=admin_path)
        print(f"Captured Admin page screenshot. Current URL: {page.url}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
