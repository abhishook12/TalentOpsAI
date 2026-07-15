import asyncio
from playwright.async_api import async_playwright

async def verify_layout():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to Dashboard...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Check body height vs window height
        body_height = await page.evaluate("document.body.scrollHeight")
        window_height = await page.evaluate("window.innerHeight")
        
        # Check cc-content height
        try:
            content_scroll_height = await page.evaluate("document.querySelector('.cc-content').scrollHeight")
            content_client_height = await page.evaluate("document.querySelector('.cc-content').clientHeight")
        except:
            content_scroll_height = 0
            content_client_height = 0
        
        print(f"Body scrollHeight: {body_height}, Window innerHeight: {window_height}")
        print(f".cc-content scrollHeight: {content_scroll_height}, clientHeight: {content_client_height}")
        
        await page.screenshot(path="layout_fix_check.png")
        print("Saved screenshot to layout_fix_check.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_layout())
