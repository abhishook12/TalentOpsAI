import asyncio
from playwright.async_api import async_playwright
import psycopg2
import time
import os

OUT_DIR = "C:\\Users\\User\\.gemini\\antigravity\\brain\\8ca93279-e790-4ae4-b3a8-41b138956926"
DB_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

async def run():
    print("Resetting db state for normal_user@talentops.com...")
    # Delete existing normal_user to ensure clean state
    conn = psycopg2.connect("postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres")
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE email='normal_user@talentops.com'")
    conn.commit()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Blocked User
        print("Taking screenshot of blocked user...")
        context1 = await browser.new_context()
        page1 = await context1.new_page()
        # Hit impersonate to set cookie and redirect
        await page1.add_init_script("localStorage.setItem('session_token', 'fake_token_to_trigger_auth_check');")
        await page1.goto("http://localhost:8000/test_auth/impersonate/normal_user@talentops.com")
        await page1.wait_for_timeout(3000)
        await page1.screenshot(path=os.path.join(OUT_DIR, "1_blocked.png"))
        
        # 2. Admin View
        print("Taking screenshot of admin devices page...")
        context2 = await browser.new_context()
        page2 = await context2.new_page()
        await page2.add_init_script("localStorage.setItem('session_token', 'fake_token_to_trigger_auth_check');")
        await page2.goto("http://localhost:8000/test_auth/impersonate/admin@talentops.com")
        await page2.wait_for_timeout(2000)
        await page2.goto("http://localhost:5173/admin/devices")
        await page2.wait_for_timeout(3000)
        await page2.screenshot(path=os.path.join(OUT_DIR, "2_admin_devices.png"))
        
        # 3. Approve via DB
        print("Approving device in DB...")
        cur.execute("UPDATE trusted_devices SET status='Trusted' WHERE user_id=(SELECT id FROM users WHERE email='normal_user@talentops.com' LIMIT 1)")
        conn.commit()
        
        # 4. Approved User View
        print("Taking screenshot of approved user...")
        # Reload page1
        await page1.reload()
        await page1.wait_for_timeout(3000)
        await page1.screenshot(path=os.path.join(OUT_DIR, "3_approved.png"))
        
        await browser.close()
        cur.close()
        conn.close()

if __name__ == "__main__":
    asyncio.run(run())
    print("Done")
