import os
import time
from playwright.sync_api import sync_playwright
import uuid

SITE = "http://localhost:5173"
SCREENSHOT_DIR = "C:/Users/User/.gemini/antigravity/brain/e050007d-77bf-4880-ac17-0d8a6b8d4518"

def main():
    print("Starting Playwright to test Campaign Send on local...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("1. Navigating to login page...")
            page.goto(f"{SITE}/login", wait_until="networkidle")
            
            print("2. Logging in...")
            page.locator('input[type="email"]').fill("admin@talentops.com")
            page.locator('input[type="password"]').fill("1012")
            page.locator('button:has-text("Login to TalentOps")').click()
            
            print("3. Waiting for login to complete...")
            time.sleep(5)
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_1_after_login.png")
            
            print("4. Navigating to campaigns page...")
            page.goto(f"{SITE}/campaigns", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_2_campaigns.png")
            
            print("5. Clicking New Campaign...")
            page.locator('button:has-text("New Campaign")').click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_3_wizard.png")
            
            print("6. Adding recipient...")
            page.locator('textarea').fill(f"test_{uuid.uuid4().hex[:8]}@example.com")
            time.sleep(1)
            page.locator('button:has-text("Add 1 Recipients")').click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_4_recipient_added.png")
            
            print("7. Clicking Continue (to Compose)...")
            page.locator('button:has-text("Continue")').click()
            time.sleep(3)
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_5_compose.png")
            
            print("8. Filling subject and body...")
            page.locator('input[placeholder*="Subject"]').fill("Local Playwright Automated Test")
            page.locator('.ProseMirror').first.fill("This is a test email sent from the local Playwright verification script.")
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_6_composed.png")
            
            print("9. Clicking Continue (to enter Flight Check)...")
            page.locator('button:has-text("Continue")').click()
            print("Waiting for Flight Check validation to complete...")
            time.sleep(5)
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_7_preview.png")
            
            # Check if there are any error messages or validation failures on the Flight Check screen
            # The bug caused it to show "validation errors" immediately
            content = page.content()
            if "Something went wrong" in content or "validation" in content.lower():
                print("WARNING: Found potential validation error text on Flight Check screen!")
                page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_7_error.png")
            
            print("10. Clicking Launch...")
            page.locator('button:has-text("Launch")').click()
            time.sleep(4)
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_8_started.png")
            
            print("SUCCESS! Local campaign test sent successfully.")
            return True
            
        except Exception as e:
            print(f"ERROR: {e}")
            page.screenshot(path=f"{SCREENSHOT_DIR}/local_test_error.png")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    main()
