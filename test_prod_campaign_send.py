import os
import time
from playwright.sync_api import sync_playwright

SITE = "https://talent-ops-ai.vercel.app"
SCREENSHOT_DIR = "C:/Users/User/.gemini/antigravity/brain/e050007d-77bf-4880-ac17-0d8a6b8d4518"

def main():
    print("Starting Playwright to test Campaign Send on production...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Log network errors safely
        page.on("requestfailed", lambda req: print(f"   [Network Error] {req.method} {req.url} - {getattr(req.failure, 'error_text', 'Unknown Error')}"))
        page.on("response", lambda res: print(f"API: {res.status} {res.url}") if "/api/" in res.url or ".js" in res.url or ".css" in res.url else None)

        try:
            # 1. Navigate to login
            print("1. Navigating to login page...")
            page.goto(f"{SITE}/login", wait_until="domcontentloaded")
            
            # 2. Login
            print("2. Logging in...")
            page.locator('input[type="email"]').fill("admin@talentops.com")
            page.locator('input[type="password"]').fill("1012")
            page.locator('button:has-text("Login to TalentOps")').click()
            
            # 3. Wait for login to complete
            print("3. Waiting for login to complete...")
            time.sleep(15)
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_1_after_login.png")
            
            # 4. Navigate to campaigns
            print("4. Navigating to campaigns page...")
            page.goto(f"{SITE}/campaigns", wait_until="domcontentloaded")
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_2_campaigns.png")
            
            # 5. Click New Campaign
            print("5. Clicking New Campaign...")
            page.locator('button:has-text("New Campaign")').click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_3_wizard.png")
            
            # 6. Add recipient
            print("6. Adding recipient...")
            page.locator('textarea').fill("test@talentops.com")
            time.sleep(1)
            page.locator('button:has-text("Add 1 Recipients")').click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_4_recipient_added.png")
            
            # 7. Click Continue to Compose
            print("7. Clicking Continue (to Compose)...")
            page.locator('button:has-text("Continue")').click()
            time.sleep(3)
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_5_compose.png")
            
            # 8. Fill Subject and Body
            print("8. Filling subject and body...")
            page.locator('input[placeholder*="Subject"]').fill("Playwright Automated Test")
            page.locator('.ProseMirror').first.fill("This is a test email sent from the Playwright verification script to ensure the campaign system is functioning properly on production.")
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_6_composed.png")
            
            # 9. Click Continue to Preview
            print("9. Clicking Continue (to Preview)...")
            page.locator('button:has-text("Continue")').click()
            time.sleep(5) # Wait for preflight validation
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_7_preview.png")
            
            # 10. Click Launch
            print("10. Clicking Launch...")
            page.locator('button:has-text("Launch")').click()
            time.sleep(4)
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_8_started.png")
            
            print("SUCCESS! Campaign test sent successfully.")
            
        except Exception as e:
            print(f"ERROR: {e}")
            page.screenshot(path=f"{SCREENSHOT_DIR}/test_send_error.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    main()
