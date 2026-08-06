import sys, time
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

SITE = "https://talent-ops-ai.vercel.app"
SCREENSHOT_DIR = r"C:\Users\User\.gemini\antigravity\brain\e050007d-77bf-4880-ac17-0d8a6b8d4518"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()

        # Capture console errors
        errors = []
        page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)

        # Capture failed network requests
        page.on("requestfailed", lambda req: errors.append(f"[Network Error] {req.method} {req.url} - {req.failure}"))
        
        # Capture API requests
        page.on("response", lambda res: print(f"API: {res.status} {res.url}") if "api" in res.url or "auth" in res.url else None)

        # 1. Go to login
        print("1. Navigating to login page...")
        page.goto(f"{SITE}/login", wait_until="networkidle", timeout=30000)
        page.screenshot(path=f"{SCREENSHOT_DIR}/prod_01_login.png")
        print(f"   URL: {page.url}")
        print(f"   Title: {page.title()}")

        # 2. Fill in credentials and login
        print("2. Logging in with admin@talentops.com / 1012...")
        email_input = page.locator('input[type="email"]')
        if email_input.is_visible():
            email_input.fill("admin@talentops.com")
        else:
            print("   ERROR: Email input not found!")
            
        pwd_input = page.locator('input[type="password"]')
        if pwd_input.is_visible():
            pwd_input.fill("1012")
        else:
            print("   ERROR: Password input not found!")
        
        submit_btn = page.locator('button:has-text("Login to TalentOps")')
        if submit_btn.is_visible():
            submit_btn.click()
        else:
            print("   ERROR: Submit button not found!")

        print("3. Waiting for login to complete...")
        time.sleep(15)
        page.screenshot(path=f"{SCREENSHOT_DIR}/prod_02_after_login.png")
        print(f"   URL after login: {page.url}")
        
        # Check if still on login page
        if "/login" in page.url:
            print("   WARNING: Still on login page! Login may have failed.")
            # Check for error messages
            error_el = page.locator('.text-red-500, .text-red-400, [role="alert"]')
            if error_el.count() > 0:
                print(f"   Error message: {error_el.first.text_content()}")

        # 3. Navigate to campaigns
        print("4. Navigating to campaigns page...")
        page.goto(f"{SITE}/campaigns", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        page.screenshot(path=f"{SCREENSHOT_DIR}/prod_03_campaigns.png")
        print(f"   URL: {page.url}")

        # Check if redirected back to login
        if "/login" in page.url:
            print("   REDIRECTED TO LOGIN - not authenticated!")
            if errors:
                print("\n--- Console Errors/Warnings ---")
                for e in errors[:20]:
                    print(f"   {e}")
            browser.close()
            return

        # 4. Check what's visible
        print("5. Checking visible elements...")
        body_text = page.locator('body').text_content()
        
        # Check for New Campaign button
        new_campaign_btn = page.locator('button:has-text("New Campaign")')
        if new_campaign_btn.is_visible():
            print("   New Campaign button: VISIBLE")
            
            # Click it
            print("6. Clicking New Campaign...")
            new_campaign_btn.click()
            time.sleep(2)
            page.screenshot(path=f"{SCREENSHOT_DIR}/prod_04_new_campaign.png")
            
            # Check wizard steps
            continue_btn = page.locator('button:has-text("Continue")')
            if continue_btn.is_visible():
                print("7. On Recipients step, clicking Continue...")
                continue_btn.click()
                time.sleep(2)
                page.screenshot(path=f"{SCREENSHOT_DIR}/prod_05_compose.png")
                
                # Click Continue again to go to Preview
                continue_btn2 = page.locator('button:has-text("Continue")')
                if continue_btn2.is_visible():
                    print("8. On Compose step, clicking Continue to Preview...")
                    continue_btn2.click()
                    time.sleep(5)
                    page.screenshot(path=f"{SCREENSHOT_DIR}/prod_06_preview.png")
                    print("   Took Preview screenshot.")
                else:
                    print("   Continue button not found on Compose step")
            else:
                print("   Continue button not found on Recipients step")
        else:
            print("   New Campaign button: NOT VISIBLE")
            # Check what IS on the page
            print(f"   Page text (first 500 chars): {body_text[:500]}")

        # Print console errors
        if errors:
            print("\n--- Console Errors/Warnings ---")
            for e in errors[:20]:
                print(f"   {e}")

        browser.close()
        print("\nDone. Screenshots saved.")

if __name__ == "__main__":
    main()
