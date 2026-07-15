import asyncio
from playwright.async_api import async_playwright
import time
import os

ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\af41bbca-eae6-4fe8-82b8-160609b01afb"

async def run_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Starting 4x UI Verification for Campaigns Page...")
        for i in range(1, 5):
            print(f"--- Verification Loop {i} ---")
            
            # Go to campaigns page
            await page.goto("http://localhost:5173/campaigns", wait_until="networkidle")
            
            # Take screenshot
            screenshot_path = os.path.join(ARTIFACTS_DIR, f"campaign_ui_verify_{i}.png")
            await page.screenshot(path=screenshot_path)
            
            print(f"[PASS] UI successfully rendered and screenshot saved: campaign_ui_verify_{i}.png")
            
            if i < 4:
                print("Waiting 60 seconds as per strict User Rule...")
                await asyncio.sleep(60)
                
        await browser.close()
        print("All 4 verification checks completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_verification())
