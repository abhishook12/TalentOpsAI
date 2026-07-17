import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        page.on("console", lambda msg: print(f"Browser console: {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser error: {err}"))
        
        try:
            await page.goto("http://localhost:5173/login", timeout=10000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print("Python Error:", e)
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
