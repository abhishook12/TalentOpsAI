import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("console", lambda msg: print(f"Browser console: {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser error: {err}"))
        page.on("requestfailed", lambda req: print(f"Request failed: {req.url} - {req.failure}"))
        page.on("response", lambda res: print(f"Response: {res.url} - {res.status}"))

        try:
            # First, register and login
            await page.goto("http://localhost:5173/register", wait_until="load")
            await page.wait_for_selector('input[type="email"]')
            
            email = "test_data_check@test.com"
            password = "Password123!"
            
            text_inputs = await page.locator('input[type="text"]').all()
            if len(text_inputs) >= 2:
                await text_inputs[0].fill('Test')
                await text_inputs[1].fill('Data')
            
            await page.fill('input[type="email"]', email)
            passwords = await page.locator('input[type="password"]').all()
            if len(passwords) >= 2:
                await passwords[0].fill(password)
                await passwords[1].fill(password)
            
            checkboxes = await page.locator('input[type="checkbox"]').all()
            if len(checkboxes) > 0:
                await checkboxes[0].check()
                
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/login", timeout=10000)
            
            await page.fill('input[type="email"]', email)
            await page.fill('input[type="password"]', password)
            await page.click('button[type="submit"]')
            
            await page.wait_for_url("http://localhost:5173/", timeout=10000)
            print("Successfully logged in, waiting for dashboard data...")
            await asyncio.sleep(5) # give it time to load data
            
        except Exception as e:
            print("Error during test:", e)
        finally:
            await browser.close()

asyncio.run(run())
