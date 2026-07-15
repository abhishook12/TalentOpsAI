import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        page.on('console', lambda msg: print(f'Console: {msg.type}: {msg.text}'))
        page.on('pageerror', lambda err: print(f'PageError: {err}'))
        page.on('request', lambda req: print(f'Request: {req.method} {req.url}'))
        page.on('response', lambda res: print(f'Response: {res.status} {res.url}'))
        
        try:
            print('Navigating...')
            await page.goto('http://localhost:5173/login', wait_until='load')
            await asyncio.sleep(3)
        except Exception as e:
            print('Error:', e)
            
        await browser.close()

asyncio.run(check())
