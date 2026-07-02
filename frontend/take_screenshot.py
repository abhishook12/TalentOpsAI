import asyncio
from playwright.async_api import async_playwright
import sys

async def main():
    screenshot_name = sys.argv[1] if len(sys.argv) > 1 else "verification_1.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        print(f"Navigating to Dashboard to capture {screenshot_name}...")
        await page.goto("http://localhost:5173")
        await page.wait_for_selector(".cc-topbar", timeout=5000)
        
        # Wait a few seconds for the map and metrics to load
        await page.wait_for_timeout(3000)

        out_path = f"C:/Users/User/.gemini/antigravity/brain/15aabb56-dcdf-44fd-be32-72119f59740d/{screenshot_name}"
        await page.screenshot(path=out_path)
        print(f"Captured {screenshot_name}.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
