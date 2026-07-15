import asyncio
from playwright.async_api import async_playwright
import time

async def verify_login_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i in range(1, 5):
            print(f'--- Check {i}: Register & Login ---')
            context = await browser.new_context()
            page = await context.new_page()
            
            email = f"test_user_{i}_{int(time.time())}@test.com"
            password = "Password123!"
            
            try:
                # 1. Go to Register
                print('Navigating to register...')
                await page.goto('http://localhost:5173/register', wait_until='load')
                # Wait for any input
                await page.wait_for_selector('input')
                
                # We have 3 text inputs (First name, Last name, Company), 1 email, 2 password
                text_inputs = await page.locator('input[type="text"]').all()
                await text_inputs[0].fill('Test')
                await text_inputs[1].fill(f'User {i}')
                # Skip company
                
                await page.fill('input[type="email"]', email)
                
                passwords = await page.locator('input[type="password"]').all()
                await passwords[0].fill(password)
                await passwords[1].fill(password)
                
                # Check terms
                await page.check('input[type="checkbox"]')
                
                # Submit Register
                await page.click('button[type="submit"]')
                print('Submitted registration...')
                
                # Should redirect to login
                await page.wait_for_url('**/login', timeout=10000)
                await page.wait_for_selector('input[type="email"]')
                
                # 2. Login
                print('Logging in...')
                await page.fill('input[type="email"]', email)
                await page.fill('input[type="password"]', password)
                await page.click('button[type="submit"]')
                
                # Wait for dashboard
                print('Waiting for dashboard...')
                await page.wait_for_url('http://localhost:5173/', timeout=10000)
                # Wait for a metric card or some content
                await page.wait_for_selector('.cc-metric', timeout=10000)
                
                print(f'Login successful for check {i}')
                await page.screenshot(path=f'C:/Users/User/.gemini/antigravity/brain/15aabb56-dcdf-44fd-be32-72119f59740d/dashboard_check_{i}.png', full_page=True)
                
            except Exception as e:
                print(f'Failed on check {i}:', e)
                await page.screenshot(path=f'C:/Users/User/.gemini/antigravity/brain/15aabb56-dcdf-44fd-be32-72119f59740d/dashboard_check_{i}_error.png', full_page=True)
            finally:
                await context.close()
                
            if i < 4:
                print('Waiting 60s for next check...')
                await asyncio.sleep(60)
                
        await browser.close()

asyncio.run(verify_login_flow())
