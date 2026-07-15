import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        page.on('console', lambda msg: print(f'Browser Console: {msg.type}: {msg.text}'))
        page.on('pageerror', lambda err: print(f'Browser Error: {err}'))
        
        try:
            print('Navigating to login...')
            await page.goto('http://localhost:5173/login', wait_until='load')
            await asyncio.sleep(2)
            print('Page content:')
            content = await page.content()
            print(content)
        except Exception as e:
            print('Error:', e)
            
        await browser.close()

asyncio.run(check())
