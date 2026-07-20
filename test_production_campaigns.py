import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print('Navigating to live login page...')
        await page.goto('https://talent-ops-ai.vercel.app/login')
        
        await page.wait_for_selector('input[type="email"]')
        await page.fill('input[type="email"]', 'admin@talentops.com')
        await page.fill('input[type="password"]', 'password123')
        await page.click('button[type="submit"]')
        
        await asyncio.sleep(4)
        
        print('Navigating to Campaigns page...')
        await page.goto('https://talent-ops-ai.vercel.app/campaigns')
        await asyncio.sleep(4)
        
        print('Taking screenshot of live campaigns...')
        screenshot_path = 'C:/Users/User/.gemini/antigravity/brain/af41bbca-eae6-4fe8-82b8-160609b01afb/live_campaigns_ui.png'
        await page.screenshot(path=screenshot_path)
        print(f'Screenshot saved to {screenshot_path}')
        
        content = await page.content()
        if "Show Test Campaigns" in content:
            print("Check 1: SUCCESS - 'Show Test Campaigns' toggle is visible on production.")
        else:
            print("Check 1: FAILED - 'Show Test Campaigns' toggle not found on production.")
            
        if "0/1 Sent" in content or "0/0 Sent" in content:
            print("Check 2: FAILED - Found '0/1 Sent' or '0/0 Sent' text which should be hidden for drafts.")
        else:
            print("Check 2: SUCCESS - No '0/1 Sent' or '0/0 Sent' progress text found for drafts.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
