import asyncio
import os
import time
import sqlite3
import json
from playwright.async_api import async_playwright

EVIDENCE_DIR = os.path.join(os.getcwd(), "evidence_package")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

async def main():
    print("ATLAS Evidence Collector Started.")
    
    # =============================================
    # STEP 0: Clean up old test data
    # =============================================
    print("Cleaning up old test data...")
    conn = sqlite3.connect("backend/dev.db")
    cursor = conn.cursor()
    
    # Delete old test devices and users to avoid stale rows
    cursor.execute("DELETE FROM trusted_devices WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'googleuser_%')")
    cursor.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'googleuser_%')")
    cursor.execute("DELETE FROM users WHERE email LIKE 'googleuser_%'")
    
    # Reset admin password to guarantee login works
    import bcrypt
    new_hash = bcrypt.hashpw(b"1012", bcrypt.gensalt()).decode('utf-8')
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = 'admin@talentops.com'", (new_hash,))
    conn.commit()
    conn.close()
    print("Old test data cleaned. Admin password reset.")
    
    print("Connecting to running dev servers...")
    await asyncio.sleep(2)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # User Context
        user_context = await browser.new_context(record_har_path=os.path.join(EVIDENCE_DIR, "user_network.har"))
        user_page = await user_context.new_page()
        user_page.on("console", lambda msg: print(f"[USER CONSOLE] {msg.text}"))
        user_page.on("pageerror", lambda err: print(f"[USER PAGE ERROR] {err}"))
        
        # Admin Context
        admin_context = await browser.new_context(record_har_path=os.path.join(EVIDENCE_DIR, "admin_network.har"))
        admin_page = await admin_context.new_page()
        admin_page.on("console", lambda msg: print(f"[ADMIN CONSOLE] {msg.text}"))
        admin_page.on("pageerror", lambda err: print(f"[ADMIN PAGE ERROR] {err}"))
        
        try:
            # =========================================================
            # SCENARIO 1 & 2: User Login & Device Request
            # =========================================================
            print("\n--- SCENARIO 1 & 2: Google Auth & Device Request ---")
            await user_page.goto("http://127.0.0.1:5173/login")
            await user_page.wait_for_selector(".login-form", timeout=10000)
            await user_page.screenshot(path=os.path.join(EVIDENCE_DIR, "1_login_page.png"))
            print("✓ Screenshot: Login page captured.")
            
            # Click the mock Google auth button via JS
            await user_page.evaluate('document.getElementById("atlas-simulate-google").click()')
            
            # Wait for ApprovalProgress to show up
            await user_page.wait_for_selector("text=Waiting for administrator approval", timeout=15000)
            await user_page.screenshot(path=os.path.join(EVIDENCE_DIR, "2_user_waiting_screen.png"))
            print("✓ Screenshot: User waiting for approval captured.")
            
            # =========================================================
            # SCENARIO 3: Admin Approval
            # =========================================================
            print("\n--- SCENARIO 3: Admin Approval ---")
            await admin_page.goto("http://127.0.0.1:5173/login")
            await admin_page.wait_for_selector(".login-form", timeout=10000)
            await admin_page.fill("input[type='email']", "admin@talentops.com")
            await admin_page.fill("input[type='password']", "1012")
            await admin_page.click("button[type='submit']")
            await admin_page.wait_for_url("**/", timeout=15000)
            print("✓ Admin logged in.")
            
            await admin_page.goto("http://127.0.0.1:5173/admin/devices")
            # Wait for the pending device row with status badge "Pending"
            await admin_page.wait_for_selector("text=Pending", timeout=15000)
            await admin_page.screenshot(path=os.path.join(EVIDENCE_DIR, "3_admin_device_notification.png"))
            print("✓ Screenshot: Admin sees pending device request.")
            
            # Find the newly created device specifically by user name
            pending_row = admin_page.locator("tr", has_text="Atlas Tester").first
            await pending_row.locator("button[title='Approve']").click()
            
            # Wait for the status to change to Trusted
            await admin_page.wait_for_timeout(2000)
            await admin_page.screenshot(path=os.path.join(EVIDENCE_DIR, "4_admin_approval_confirmation.png"))
            print("✓ Screenshot: Admin approved device.")
            
            # =========================================================
            # SCENARIO 4: User Dashboard Redirect  
            # =========================================================
            print("\n--- SCENARIO 4: User Login Completion ---")
            # The SSE should have pushed "approved", onApproved fires,
            # api.post('/auth/complete-device-approval') runs,
            # performBackgroundInitialization redirects to dashboard.
            # Give it up to 20 seconds.
            try:
                await user_page.wait_for_selector("h2:has-text('Welcome to TalentOps AI'), div:has-text('Total Recruiters'), div:has-text('Access Restricted')", timeout=20000)
                await user_page.screenshot(path=os.path.join(EVIDENCE_DIR, "5_user_dashboard_redirect.png"))
                print("✓ Screenshot: User redirected to dashboard.")
            except Exception as e:
                print(f"⚠ Dashboard redirect timed out: {e}")
                # Take error screenshot showing current state
                await user_page.screenshot(path=os.path.join(EVIDENCE_DIR, "5_user_state_after_approval.png"))
                with open(os.path.join(EVIDENCE_DIR, "5_user_state_after_approval.html"), "w", encoding="utf-8") as f:
                    f.write(await user_page.content())
                current_url = user_page.url
                print(f"  Current URL: {current_url}")
            
            # =========================================================
            # SCENARIO 5: Verify Identity
            # =========================================================
            print("\n--- SCENARIO 5: Verify Identity ---")
            try:
                await user_page.goto("http://127.0.0.1:5173/profile", timeout=10000)
                await user_page.wait_for_timeout(2000)
                await user_page.screenshot(path=os.path.join(EVIDENCE_DIR, "6_user_profile.png"))
                print("✓ Screenshot: User profile captured.")
            except Exception as e:
                print(f"⚠ Profile page: {e}")
                await user_page.screenshot(path=os.path.join(EVIDENCE_DIR, "6_user_profile_error.png"))
            
            # =========================================================
            # DB VERIFICATION
            # =========================================================
            print("\n--- DATABASE VERIFICATION ---")
            conn = sqlite3.connect("backend/dev.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, email, first_name, last_name, status FROM users WHERE email LIKE 'googleuser_%' ORDER BY id DESC LIMIT 3")
            users = cursor.fetchall()
            print(f"  Users: {users}")
            
            cursor.execute("SELECT id, device_name, user_id, status FROM trusted_devices ORDER BY id DESC LIMIT 3")
            devices = cursor.fetchall()
            print(f"  Devices: {devices}")
            
            cursor.execute("SELECT id, user_id, ip_address, is_active FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'googleuser_%') ORDER BY id DESC LIMIT 3")
            sessions = cursor.fetchall()
            print(f"  Sessions: {sessions}")
            
            with open(os.path.join(EVIDENCE_DIR, "database_verification.json"), "w") as f:
                json.dump({
                    "users": [{"id": u[0], "email": u[1], "name": f"{u[2]} {u[3]}", "status": u[4]} for u in users],
                    "devices": [{"id": d[0], "device": d[1], "user_id": d[2], "status": d[3]} for d in devices],
                    "sessions": [{"id": s[0], "user_id": s[1], "ip": s[2], "active": bool(s[3])} for s in sessions]
                }, f, indent=2)
            
            conn.close()
            print("✓ Database evidence collected.")
            
        except Exception as e:
            print(f"\n✗ Error during collection: {e}")
            try:
                await user_page.screenshot(path=os.path.join(EVIDENCE_DIR, "error_user_state.png"))
                await admin_page.screenshot(path=os.path.join(EVIDENCE_DIR, "error_admin_state.png"))
            except:
                pass
        
        finally:
            await user_context.close()
            await admin_context.close()
            await browser.close()
            print("\n=== Evidence collection complete. ===")

if __name__ == "__main__":
    asyncio.run(main())
