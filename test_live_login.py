import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print('Navigating to live login page...')
        await page.goto('https://talent-ops-ai.vercel.app/login')
        
        # Wait for form
        await page.wait_for_selector('input[type="email"]')
        
        print('Entering credentials...')
        await page.fill('input[type="email"]', 'admin@talentops.com')
        await page.fill('input[type="password"]', '1012')
        
        print('Submitting form...')
        await page.click('button[type="submit"]')
        
        # Wait for navigation to complete
        await asyncio.sleep(4)
        
        print(f'Current URL after login: {page.url}')
        
        # Take a screenshot
        screenshot_path = 'C:/Users/User/.gemini/antigravity/brain/af41bbca-eae6-4fe8-82b8-160609b01afb/successful_login.png'
        await page.screenshot(path=screenshot_path)
        print(f'Screenshot saved to {screenshot_path}')
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
