import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://talent-ops-ai.vercel.app/login')
        await page.wait_for_selector('input[type="email"]')
        await page.fill('input[type="email"]', 'admin@talentops.com')
        await page.fill('input[type="password"]', 'password123')
        await page.click('button[type="submit"]')
        await asyncio.sleep(4)
        await page.goto('https://talent-ops-ai.vercel.app/campaigns')
        await asyncio.sleep(4)
        # Check if the table is present
        table = await page.query_selector('table')
        if table:
            print('Table found')
            print(await table.inner_text())
        else:
            print('No table found on the page! Content:')
            print(await page.content())
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
