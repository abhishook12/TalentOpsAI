import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Opening app...")
        await page.goto("https://talent-ops-ai.vercel.app/")
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path="debug_login.png", full_page=True)
        print("Screenshot saved to debug_login.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
