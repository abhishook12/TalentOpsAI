import asyncio
from playwright.async_api import async_playwright

async def test_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on('response', lambda response: print(f'RESPONSE: {response.status} {response.url} {response.status_text}') if response.status >= 400 else None)
        page.on('pageerror', lambda err: print(f'PAGE ERROR: {err.message}'))

        print("Logging in...")
        await page.goto('https://talent-ops-ai.vercel.app/login')
        
        await page.fill('input[type="email"]', 'abhishekjadon824@gmail.com')
        await page.fill('input[type="password"]', 'Admin@1234')
        
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        
        print("Done. URL is:", page.url)
        await browser.close()

asyncio.run(test_all())
