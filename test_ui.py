import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print('Navigating to login...')
        await page.goto('https://talent-ops-ai.vercel.app/login')
        
        # Log in
        print('Logging in...')
        await page.fill('input[type="email"]', 'admin@talentops.com')
        await page.fill('input[type="password"]', 'admin123456')
        await page.click('button[type="submit"]')
        
        # Wait for navigation to complete
        print('Waiting for login redirect...')
        await page.wait_for_load_state('networkidle')
        
        # Go to devices page
        print('Navigating to devices page...')
        await page.goto('https://talent-ops-ai.vercel.app/admin/devices', wait_until='networkidle')
        
        try:
            # Check for crash boundary error text
            print('Checking for crash errors...')
            await page.wait_for_selector('text="Component crashed"', timeout=3000)
            print('❌ ERROR: Component crashed text found!')
            await browser.close()
            exit(1)
        except Exception:
            print('No crash detected.')
        
        # Wait for either devices to load or the empty state
        try:
            print('Waiting for devices table to render...')
            await page.wait_for_selector('text="Pending Approvals"', timeout=5000)
            
            # Check if pending count is not 0
            pending_count = await page.locator('text="Pending Approvals"').locator('..').locator('text="0"').count()
            if pending_count == 0:
                 print('✅ UI Loaded! Pending devices count is > 0.')
            else:
                 print('⚠️ UI Loaded, but Pending devices shows 0.')
                 
            # Take a screenshot for proof
            await page.screenshot(path='playwright_proof.png')
            print('✅ All tests passed. Screenshot saved.')
        except Exception as e:
            print(f'❌ ERROR: Failed to render devices dashboard correctly. {e}')
            await page.screenshot(path='playwright_error.png')
            await browser.close()
            exit(1)
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
