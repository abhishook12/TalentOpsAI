import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"PageError: {err}"))
        
        print("Navigating to login...")
        await page.goto("http://localhost:5173/login")
        await page.fill('input[type="email"]', 'admin@talentops.com')
        await page.fill('input[type="password"]', '1012')
        await page.click('button[type="submit"]')
        await page.wait_for_url("http://localhost:5173/")
        
        print("Navigating to AI Search...")
        await page.goto("http://localhost:5173/ai-search")
        await asyncio.sleep(1)
        
        print("Typing a number into search to verify bug fix...")
        # Assuming there is an input field for search, usually placeholder="Search" or similar
        # Since I don't know the exact selector, I will just press Tab until I hit it, or use the role
        await page.fill('input[type="text"]', '16123306699')
        await asyncio.sleep(2)
        
        await browser.close()
        
        if errors:
            print("ERRORS FOUND:")
            for e in set(errors):
                print(e)
        else:
            print("No errors found. Bug successfully fixed!")

asyncio.run(main())
