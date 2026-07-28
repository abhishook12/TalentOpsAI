import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print("Navigating to login...")
        await page.goto("http://localhost:5173/login")
        
        print("Logging in...")
        await page.fill('input[type="email"]', 'admin@talentops.com')
        await page.fill('input[type="password"]', '1012')
        await page.click('button:has-text("Sign In")')
        print("Capturing Dashboard...")
        await page.wait_for_selector('text="Total Recruiters"')
        await asyncio.sleep(2) # wait for animations
        await page.screenshot(path='C:\\Users\\User\\.gemini\\antigravity\\brain\\8ca93279-e790-4ae4-b3a8-41b138956926\\proof_dashboard.png')
        print("Capturing Recruiters...")
        await page.goto("http://localhost:5173/recruiters")
        await asyncio.sleep(8)
        await page.screenshot(path='C:\\Users\\User\\.gemini\\antigravity\\brain\\8ca93279-e790-4ae4-b3a8-41b138956926\\proof_recruiters.png')
        
        print("Capturing Directory...")
        await page.goto("http://localhost:5173/directory")
        await asyncio.sleep(8)
        await page.screenshot(path='C:\\Users\\User\\.gemini\\antigravity\\brain\\8ca93279-e790-4ae4-b3a8-41b138956926\\proof_directory.png')
        
        print("Capturing Analytics...")
        await page.goto("http://localhost:5173/analytics")
        await asyncio.sleep(8)
        await page.screenshot(path='C:\\Users\\User\\.gemini\\antigravity\\brain\\8ca93279-e790-4ae4-b3a8-41b138956926\\proof_analytics.png')
        
        print("Done capturing 3 proofs!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
