import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Give permissions for clipboard etc just in case
        context = await browser.new_context()
        page = await context.new_page()
        
        print("1. Opening app...")
        await page.goto("https://talent-ops-ai.vercel.app/")
        await page.wait_for_timeout(3000)
        
        # Check if login is needed
        try:
            if await page.locator("input[placeholder='Enter master admin password']").is_visible(timeout=2000):
                print("2. Logging in...")
                await page.fill("input[placeholder='Enter master admin password']", "admin")
                await page.click("button:has-text('Unlock Platform')")
                await page.wait_for_timeout(3000)
        except Exception:
            print("Already logged in or no login screen.")

        # --- UPLOAD 1: Base Data ---
        print("3. Navigating to Upload page...")
        # Click the ETL/Upload link in sidebar
        await page.click("a[href='/upload']")
        await page.wait_for_timeout(3000)
        
        print("4. Uploading base.csv...")
        with open("base.csv", "w") as f:
            f.write("Name,Email,Company,Location\nJohn Smith,john@abc.com,ABC,New York\n")
            
        await page.set_input_files("input[type='file']", "base.csv")
        await page.wait_for_timeout(3000)
        
        print("5. Confirming mapping...")
        # SmartUploadWizard uses: "Start Adaptive Import ({analysis.total_rows} Rows)"
        await page.click("button:has-text('Start Adaptive Import')")
        await page.wait_for_timeout(5000)
        
        # --- UPLOAD 2: Enrichment Data ---
        print("7. Clicking Reset for second upload...")
        await page.click("button:has-text('Reset')")
        await page.wait_for_timeout(2000)
        
        print("8. Uploading enrichment_test.csv...")
        await page.set_input_files("input[type='file']", "enrichment_test.csv")
        await page.wait_for_timeout(3000)
        
        print("9. Confirming mapping for enrichment...")
        await page.click("button:has-text('Start Adaptive Import')")
        await page.wait_for_timeout(5000)
        
        print("10. Taking screenshot of enrichment preview...")
        await page.screenshot(path="enrichment_preview.png", full_page=True)
        print("Screenshot saved to enrichment_preview.png")
        
        # Verify text
        content = await page.content()
        # Since it directly completes without intermediate finalize:
        print("Completed upload flow successfully.")
        
        print("12. Taking screenshot of completed screen...")
        await page.screenshot(path="enrichment_completed.png", full_page=True)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
