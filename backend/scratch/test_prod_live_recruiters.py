import asyncio
import os
import sys
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\be5e058f-502c-416d-a76d-db5d160f0985"
PROD_URL = "https://talent-ops-ai.vercel.app"

async def test_prod_live():
    print("Testing live production site at:", PROD_URL)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1600, 'height': 1050})
        page = await context.new_page()

        # Listen to console and errors
        page.on('console', lambda msg: print(f"[PROD CONSOLE] {msg.type}: {msg.text}"))
        page.on('requestfailed', lambda req: print(f"[PROD REQ FAILED] {req.url}"))
        page.on('response', lambda resp: print(f"[PROD RESP {resp.status}] {resp.url}") if resp.status >= 400 or 'recruiters' in resp.url else None)

        print("1. Navigating to login page...")
        await page.goto(f"{PROD_URL}/login", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # Inject session token or perform test
        print("2. Navigating to /recruiters on Vercel production...")
        await page.goto(f"{PROD_URL}/recruiters", wait_until="domcontentloaded")
        await asyncio.sleep(6)

        # Check if error message is present
        error_locator = page.locator('text="Failed to load recruiters"')
        error_count = await error_locator.count()
        print(f"Error Banner Count on Production: {error_count}")

        # Check if table rows loaded
        rows = await page.locator('tbody tr').count()
        print(f"Loaded Recruiter Table Rows on Production: {rows}")

        proof_path = os.path.join(ARTIFACT_DIR, "prod_live_recruiters_verified.png")
        await page.screenshot(path=proof_path, full_page=False)
        print(f"Screenshot saved to: {proof_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_prod_live())
