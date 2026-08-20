import asyncio
import os
import sys
from playwright.async_api import async_playwright

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Session as DBSession, TrustedDevice
from app.services.auth_service import create_access_token

# Generate valid admin auth session
db = SessionLocal()
admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
trusted_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == admin_user.id, TrustedDevice.status == "Trusted").first()
session = db.query(DBSession).filter(DBSession.user_id == admin_user.id, DBSession.trusted_device_id == trusted_dev.id).first()
token = create_access_token(data={"sub": str(admin_user.id), "session_id": str(session.id)})
db.close()

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\be5e058f-502c-416d-a76d-db5d160f0985"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1600, 'height': 1100})
        page = await context.new_page()

        # Inject session token into storage before navigation
        await page.goto("http://127.0.0.1:5174/login")
        await page.evaluate(f"""() => {{
            localStorage.setItem('session_token', '{token}');
            sessionStorage.setItem('session_token', '{token}');
            localStorage.setItem('auth_session', JSON.stringify({{ email: '{admin_user.email}' }}));
            localStorage.setItem('theme', 'dark');
        }}""")

        print("1. Capturing Dashboard at '/'...")
        await page.goto("http://127.0.0.1:5174/", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        dashboard_proof = os.path.join(ARTIFACT_DIR, "visual_proof_dashboard_heatmap.png")
        await page.screenshot(path=dashboard_proof, full_page=False)
        print(f"Captured: {dashboard_proof}")

        print("2. Capturing Directory at '/directory'...")
        await page.goto("http://127.0.0.1:5174/directory", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        search_input = page.locator('input[placeholder*="Search"]').first
        if await search_input.count() > 0:
            await search_input.fill("BridgeCross")
            await asyncio.sleep(2)
        directory_proof = os.path.join(ARTIFACT_DIR, "visual_proof_directory_bridgecross.png")
        await page.screenshot(path=directory_proof, full_page=False)
        print(f"Captured: {directory_proof}")

        print("3. Capturing Recruiters at '/recruiters'...")
        await page.goto("http://127.0.0.1:5174/recruiters", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        rec_input = page.locator('input[placeholder*="Search"]').first
        if await rec_input.count() > 0:
            await rec_input.fill("BridgeCross")
            await asyncio.sleep(4)

        recruiters_proof = os.path.join(ARTIFACT_DIR, "visual_proof_recruiters_roster.png")
        await page.screenshot(path=recruiters_proof, full_page=False)
        print(f"Captured: {recruiters_proof}")

        await browser.close()
        print("\n>>> ALL 3 VISUAL PROOFS CAPTURED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
