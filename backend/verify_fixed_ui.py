import asyncio
from playwright.async_api import async_playwright
import os

ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\af41bbca-eae6-4fe8-82b8-160609b01afb"

async def run_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Taking verification screenshot...")
        await page.goto("http://localhost:5173/campaigns", wait_until="networkidle")
        
        screenshot_path = os.path.join(ARTIFACTS_DIR, "fixed_campaign_ui_verify.png")
        await page.screenshot(path=screenshot_path)
        
        # Check for Vite error overlay
        error_overlay = await page.query_selector('vite-error-overlay')
        if error_overlay:
            print("ERROR: Vite error overlay detected!")
        else:
            print("SUCCESS: No Vite error overlay detected.")
            
        await browser.close()
        print(f"Screenshot saved to {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(run_verification())
