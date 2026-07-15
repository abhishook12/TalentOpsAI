import asyncio
from playwright.async_api import async_playwright
import os

ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\af41bbca-eae6-4fe8-82b8-160609b01afb"

async def run_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Taking 3x verification screenshot of campaigns page...")
        
        for i in range(1, 4):
            print(f"--- Verification Loop {i} ---")
            await page.goto("http://localhost:5173/campaigns", wait_until="networkidle")
            
            # Wait a moment for any lazy loading
            await asyncio.sleep(1)
            
            screenshot_path = os.path.join(ARTIFACTS_DIR, f"campaign_verify_{i}.png")
            await page.screenshot(path=screenshot_path)
            
            # Check for "Not Found" text which indicates a routing failure
            not_found = await page.evaluate('''() => {
                return document.body.innerText.includes("Not Found");
            }''')
            
            if not_found:
                print("ERROR: 'Not Found' text is still on the screen!")
            else:
                print("SUCCESS: Campaigns route loaded successfully.")
                
            if i < 3:
                await asyncio.sleep(2)
            
        await browser.close()
        print("All 3 checks complete.")

if __name__ == "__main__":
    asyncio.run(run_verification())
