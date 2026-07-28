import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to login...")
        await page.goto("http://localhost:5173/login")
        
        print("Logging in...")
        await page.fill('input[placeholder="name@company.com"]', 'admin@talentops.com')
        await page.fill('input[placeholder="••••••••"]', 'admin123')
        await page.click('button:has-text("Sign In")')
        await page.wait_for_url("**/dashboard*")
        
        print("Waiting for Dashboard to load metrics...")
        await page.wait_for_selector('h3:has-text("Recruiters")')
        
        # Scrape Dashboard Recruiter count
        dashboard_recruiters_el = await page.locator('div:has(h3:has-text("Recruiters")) >> span.text-3xl').first.inner_text()
        print(f"Dashboard recruiters count: {dashboard_recruiters_el}")
        
        print("Navigating to Recruiters page...")
        await page.click('text="Recruiters"')
        await page.wait_for_url("**/recruiters*")
        
        print("Waiting for Recruiters table to load...")
        await page.wait_for_selector('text="total matches found"')
        
        # Scrape Recruiters page count
        matches_text = await page.locator('text="total matches found"').first.inner_text()
        print(f"Recruiters page says: {matches_text}")
        
        # Verify alignment
        dashboard_num = dashboard_recruiters_el.replace(',', '').strip()
        matches_num = matches_text.split(' ')[0].replace(',', '').strip()
        
        if dashboard_num == matches_num:
            print("GOLDEN BASELINE VERIFIED: Dashboard count matches Recruiters page count!")
        else:
            print(f"DEFECT DETECTED: Dashboard ({dashboard_num}) != Recruiters ({matches_num})")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
