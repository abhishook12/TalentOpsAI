import asyncio
from playwright.async_api import async_playwright
import time

PROD_URL = 'https://talent-ops-ai.vercel.app'

async def verify_prod():
    print('Starting Production Smoke Test...')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        # Hard refresh simulation and loading
        max_retries = 10
        success = False
        for i in range(max_retries):
            print(f'Checking if Vercel is done deploying... Attempt {i+1}')
            await page.goto(f'{PROD_URL}/login')
            await asyncio.sleep(2)
            
            # Check if white screen or 'header is not defined'
            content = await page.evaluate("() => document.body.innerText")
            if 'header is not defined' in content:
                print('Error still present, waiting 15 seconds...')
                await asyncio.sleep(15)
                continue
                
            # Check if login form is there
            if await page.locator('input[type="email"]').count() > 0:
                print('Vercel deployment is live! Login page loaded.')
                success = True
                break
            
            print('Waiting for page to become available...')
            await asyncio.sleep(15)
            
        if not success:
            print('Production is still broken or Vercel took too long.')
            await browser.close()
            return
            
        await page.screenshot(path='prod_login.png')
        
        # Register a test user
        print('Testing Registration...')
        await page.goto(f'{PROD_URL}/register')
        await page.wait_for_selector('input[type="email"]')
        test_email = f'prod_smoke_{int(time.time())}@e2etest.com'
        await page.fill('input[type="email"]', test_email)
        await page.fill('input[type="password"]', 'Password123!')
        await page.fill('input[placeholder="Confirm your password"]', 'Password123!')
        await page.fill('input[type="text"][placeholder*="First"]', 'Prod')
        await page.fill('input[type="text"][placeholder*="Last"]', 'User')
        await page.check('input[type="checkbox"]')
        await page.click('button:has-text("Create Account")')
        
        try:
            await page.wait_for_url('**/login', timeout=15000)
            print('Registration succeeded on production.')
            await page.fill('input[type="email"]', test_email)
            await page.fill('input[type="password"]', 'Password123!')
            await page.click('button:has-text("Sign In")')
            await page.wait_for_selector('text=Dashboard', timeout=15000)
            print('Login succeeded on production.')
        except Exception as e:
            print('Login or Registration failed. Maybe redirect was different.')
            
        await page.goto(f'{PROD_URL}/')
        await asyncio.sleep(3)
        await page.screenshot(path='prod_dashboard.png')
        
        # Check Sidebar and navigation
        print('Testing routing...')
        routes = ['/campaigns', '/recruiters', '/profile']
        for r in routes:
            await page.goto(f'{PROD_URL}{r}')
            await asyncio.sleep(2)
            content = await page.evaluate("() => document.body.innerText")
            if 'header is not defined' in content:
                print(f'CRASH on {r}: header is not defined')
            else:
                print(f'Route {r} loaded successfully.')
                
        await browser.close()
        print('Production Verification Complete.')

if __name__ == '__main__':
    asyncio.run(verify_prod())
