from playwright.sync_api import sync_playwright
import time
import os

os.makedirs('screenshots', exist_ok=True)

def verify_modals():
    print("STARTING 3-TIMES MODAL VERIFICATION PROTOCOL...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        # PASS 1: Register Page Modal/Container
        print("[PASS 1] Verifying Register Page Glow Container...")
        page.goto("http://localhost:5173/register")
        page.wait_for_timeout(1000)
        page.screenshot(path="screenshots/pass1_register.png")
        print("  -> Screenshot saved: pass1_register.png")

        # Login to access other modals
        print("Logging in to access internal modals...")
        page.goto("http://localhost:5173/login")
        page.wait_for_timeout(1000)
        page.fill("input[type='email']", "admin@talentops.local")
        page.fill("input[type='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # PASS 2: Recruiters Add Modal
        print("[PASS 2] Verifying Recruiters Add Modal Transition...")
        page.goto("http://localhost:5173/recruiters")
        page.wait_for_timeout(1500)
        # Click the "Add Recruiter" button (assuming it's a primary button)
        try:
            page.click("button:has-text('Add')")
            page.wait_for_timeout(500) # Wait for fade up
            page.screenshot(path="screenshots/pass2_recruiters_modal.png")
            print("  -> Screenshot saved: pass2_recruiters_modal.png")
        except Exception as e:
            print("  -> Could not open Recruiters modal:", e)

        # PASS 3: User Management Add Modal
        print("[PASS 3] Verifying User Management Modal Transition...")
        page.goto("http://localhost:5173/admin/users")
        page.wait_for_timeout(1500)
        try:
            page.click("button:has-text('Add User')")
            page.wait_for_timeout(500)
            page.screenshot(path="screenshots/pass3_user_modal.png")
            print("  -> Screenshot saved: pass3_user_modal.png")
        except Exception as e:
            print("  -> Could not open User Management modal:", e)

        print("3-TIMES MODAL VERIFICATION COMPLETE.")
        browser.close()

if __name__ == "__main__":
    verify_modals()
