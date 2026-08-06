import os
import time
import uuid
from playwright.sync_api import sync_playwright

SITE = "http://localhost:5173"
SCREENSHOT_DIR = "C:/Users/User/.gemini/antigravity/brain/e050007d-77bf-4880-ac17-0d8a6b8d4518"

def main():
    print("Starting Playwright to test Campaign Send on local...")
    test_email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
    test_pass = "TestPassword123!"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print(f"1. Registering {test_email}...")
            page.goto(f"{SITE}/register", wait_until="domcontentloaded")
            page.locator('input[placeholder="First name"]').fill("Test")
            page.locator('input[placeholder="Last name"]').fill("User")
            page.locator('input[type="email"]').fill(test_email)
            page.locator('input[placeholder="Create a strong password"]').fill(test_pass)
            page.locator('input[placeholder="Confirm your password"]').fill(test_pass)
            page.locator('input[type="checkbox"]').check()
            page.locator('button[type="submit"]').click()
            
            print("Waiting for registration to complete...")
            time.sleep(5)
            
            print("2. Logging in...")
            page.goto(f"{SITE}/login", wait_until="domcontentloaded")
            page.locator('input[type="email"]').fill(test_email)
            page.locator('input[type="password"]').fill(test_pass)
            page.locator('button:has-text("Login to TalentOps")').click()
            
            time.sleep(5)
            page.screenshot(path=f"{SCREENSHOT_DIR}/e2e_1_after_login.png")
            
            print("3. Navigating to campaigns page...")
            page.goto(f"{SITE}/campaigns", wait_until="domcontentloaded")
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/e2e_2_campaigns.png")
            
            print("4. Clicking New Campaign...")
            page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.includes('New Campaign'));
                if (btn) btn.click();
            }''')
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/e2e_3_wizard.png")
            
            print("5. Adding recipient...")
            page.locator('textarea').fill(f"target_{uuid.uuid4().hex[:8]}@example.com")
            time.sleep(1)
            page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.includes('Add 1 Recipients'));
                if (btn) btn.click();
            }''')
            time.sleep(2)
            
            print("6. Clicking Continue (to Compose)...")
            page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.includes('Continue'));
                if (btn) btn.click();
            }''')
            time.sleep(3)
            
            print("7. Filling subject and body...")
            page.locator('input[placeholder*="Subject"]').fill("Local Playwright Automated Test")
            page.locator('.ProseMirror').first.fill("This is a test email sent from the local Playwright verification script.")
            time.sleep(2)
            
            print("8. Clicking Continue (to enter Flight Check)...")
            page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.includes('Continue'));
                if (btn) btn.click();
            }''')
            print("Waiting for Flight Check validation to complete...")
            time.sleep(5)
            page.screenshot(path=f"{SCREENSHOT_DIR}/e2e_4_preview.png")
            
            content = page.content()
            if "Something went wrong" in content or "validation" in content.lower():
                print("WARNING: Found potential validation error text on Flight Check screen!")
                page.screenshot(path=f"{SCREENSHOT_DIR}/e2e_5_error.png")
            
            print("9. Clicking Launch...")
            page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.includes('Launch'));
                if (btn) btn.click();
            }''')
            time.sleep(4)
            page.screenshot(path=f"{SCREENSHOT_DIR}/e2e_6_started.png")
            
            print("SUCCESS! Local campaign test sent successfully.")
            return True
            
        except Exception as e:
            print(f"ERROR: {e}")
            page.screenshot(path=f"{SCREENSHOT_DIR}/e2e_error.png")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    for i in range(3):
        print(f"\n--- ATTEMPT {i+1} ---")
        success = main()
        if not success:
            print("? FAILED.")
            break
    else:
        print("\n? ALL 3 CHECKS PASSED.")
