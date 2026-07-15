import asyncio
from playwright.async_api import async_playwright
import os

ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\af41bbca-eae6-4fe8-82b8-160609b01afb"

async def run_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Taking 3x verification screenshot of login page...")
        
        for i in range(1, 4):
            print(f"--- Verification Loop {i} ---")
            await page.goto("http://localhost:5173/login", wait_until="networkidle")
            screenshot_path = os.path.join(ARTIFACTS_DIR, f"login_verify_{i}.png")
            await page.screenshot(path=screenshot_path)
            
            # Check for lockdown text
            lockdown_detected = await page.evaluate('''() => {
                return document.body.innerText.includes("System is in Emergency Lockdown");
            }''')
            
            if lockdown_detected:
                print("ERROR: Emergency Lockdown text is still on the screen!")
            else:
                print("SUCCESS: Emergency Lockdown text is GONE.")
                
            if i < 3:
                await asyncio.sleep(2)
            
        await browser.close()
        print("All 3 checks complete.")

if __name__ == "__main__":
    asyncio.run(run_verification())
