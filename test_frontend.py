import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"PageError: {err}"))
        page.on("console", lambda msg: errors.append(f"Console: {msg.type} {msg.text}") if msg.type == "error" else None)
        
        print("Navigating to login...")
        await page.goto("http://localhost:5173/login")
        await page.fill('input[type="email"]', 'admin@talentops.com')
        await page.fill('input[type="password"]', '1012')
        await page.click('button[type="submit"]')
        
        await page.wait_for_url("http://localhost:5173/", timeout=5000)
        print("Logged in. Waiting 2 seconds for dashboard to load...")
        await asyncio.sleep(2)
        
        pages_to_visit = [
            "/analytics",
            "/directory",
            "/recruiters",
            "/campaigns"
        ]
        
        for p_url in pages_to_visit:
            print(f"Navigating to {p_url}...")
            await page.goto(f"http://localhost:5173{p_url}")
            await asyncio.sleep(2)
            
        await browser.close()
        
        if errors:
            print("ERRORS FOUND:")
            for e in set(errors):
                print(e)
        else:
            print("No errors found.")

asyncio.run(main())
