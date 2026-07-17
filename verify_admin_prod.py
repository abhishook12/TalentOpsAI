import asyncio
from playwright.async_api import async_playwright
import time

PROD_URL = 'https://talent-ops-ai.vercel.app'
ADMIN_EMAIL = 'abhishekjadon824@gmail.com'
ADMIN_PASS = 'Admin@1234'

async def verify_admin_prod():
    print('Starting Admin Production Verification...')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # --- TEST 1: Email/Password Login ---
        print('\n--- TEST 1: Email/Password Login ---')
        context1 = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page1 = await context1.new_page()
        
        # Wait for deployment
        for i in range(10):
            print(f'Checking Vercel deployment... Attempt {i+1}')
            await page1.goto(f'{PROD_URL}/login')
            await asyncio.sleep(2)
            if await page1.locator('input[type="email"]').count() > 0:
                break
            await asyncio.sleep(15)
            
        await page1.fill('input[type="email"]', ADMIN_EMAIL)
        await page1.fill('input[type="password"]', ADMIN_PASS)
        await page1.click('button:has-text("Sign In")')
        
        try:
            await page1.wait_for_selector('text=Admin Console', timeout=15000)
            print('PASS: Login successful. Admin Console detected.')
            await page1.screenshot(path='prod_admin_login_success.png')
        except Exception as e:
            print('FAIL: Could not log in or see Admin Console.')
            print(e)
            return

        # --- TEST 2: Session Persistence & Refresh ---
        print('\n--- TEST 2: Session Persistence & Refresh ---')
        await page1.reload()
        await asyncio.sleep(3)
        if await page1.locator('text=Admin Console').count() > 0:
            print('PASS: Session persisted after hard refresh.')
        else:
            print('FAIL: Session lost after refresh.')

        # --- TEST 3: Logout ---
        print('\n--- TEST 3: Logout ---')
        await page1.click('text=Sign Out')
        await asyncio.sleep(2)
        if await page1.locator('input[type="email"]').count() > 0:
            print('PASS: Logout successful. Redirected to login page.')
        else:
            print('FAIL: Logout failed.')

        await context1.close()

        # --- TEST 4: Browser Restart / Incognito ---
        print('\n--- TEST 4: Browser Restart / Incognito ---')
        context2 = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page2 = await context2.new_page()
        await page2.goto(f'{PROD_URL}/login')
        await page2.fill('input[type="email"]', ADMIN_EMAIL)
        await page2.fill('input[type="password"]', ADMIN_PASS)
        await page2.click('button:has-text("Sign In")')
        
        try:
            await page2.wait_for_selector('text=Admin Console', timeout=15000)
            print('PASS: Login successful in new Incognito context.')
            await page2.screenshot(path='prod_admin_incognito_success.png')
        except Exception as e:
            print('FAIL: Incognito login failed.')
            
        await browser.close()
        print('\nVerification Complete.')

if __name__ == '__main__':
    asyncio.run(verify_admin_prod())
