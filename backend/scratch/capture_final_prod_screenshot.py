import asyncio
import os
import urllib.request
import json
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\be5e058f-502c-416d-a76d-db5d160f0985"
PROD_URL = "https://talent-ops-ai.vercel.app"
API_URL = "https://talentopsai-1.onrender.com"

async def capture_final():
    print("1. Authenticating with Render...")
    login_req = urllib.request.Request(
        f"{API_URL}/auth/login",
        data=json.dumps({"email": "admin@talentops.com", "password": "admin123456"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    login_resp = urllib.request.urlopen(login_req)
    login_data = json.loads(login_resp.read().decode())
    token = login_data.get("token")
    print(f"Token acquired: {token[:20]}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1600, 'height': 1050})
        page = await context.new_page()

        # Seed local storage
        await page.goto(f"{PROD_URL}/login", wait_until="domcontentloaded")
        await page.evaluate(f"""() => {{
            localStorage.setItem('session_token', '{token}');
            sessionStorage.setItem('session_token', '{token}');
            localStorage.setItem('auth_session', JSON.stringify({{ email: 'admin@talentops.com', role: 'superadmin' }}));
            localStorage.setItem('theme', 'dark');
        }}""")

        print("2. Navigating to https://talent-ops-ai.vercel.app/recruiters...")
        await page.goto(f"{PROD_URL}/recruiters", wait_until="domcontentloaded")
        
        # Wait for table rows to appear
        print("Waiting for recruiter table rows to render...")
        try:
            await page.wait_for_selector('tbody tr', timeout=20000)
            print("Table rows successfully rendered!")
        except Exception as e:
            print("Timeout waiting for rows:", e)
            
        await asyncio.sleep(2)

        row_count = await page.locator('tbody tr').count()
        print(f"Rendered Table Rows: {row_count}")

        final_ss = os.path.join(ARTIFACT_DIR, "live_production_recruiters_fully_loaded.png")
        await page.screenshot(path=final_ss, full_page=False)
        print(f"Screenshot saved to: {final_ss}")

        # Search check
        print("3. Navigating to https://talent-ops-ai.vercel.app/search...")
        await page.goto(f"{PROD_URL}/search", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        search_box = page.locator('input[placeholder*="Search"], input[type="text"]').first
        await search_box.fill("SystemOne")
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)

        final_search_ss = os.path.join(ARTIFACT_DIR, "live_production_search_fully_loaded.png")
        await page.screenshot(path=final_search_ss, full_page=False)
        print(f"Screenshot saved to: {final_search_ss}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_final())
