import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://talent-ops-ai.vercel.app/login?redirect=%2F')
        await page.fill('input[name="email"]', 'test_user_1@example.com')
        await page.fill('input[name="password"]', 'StrongPass_2026!')
        await page.click('button.login-button-primary')
        await page.wait_for_timeout(3000)
        print('URL:', page.url)
        content = await page.content()
        print('Has Approval:', 'administrator approval' in content)
        print('Has Invalid:', 'Invalid credentials' in content)
        print('Has Locked:', 'locked' in content)
        await browser.close()
        
asyncio.run(run())
