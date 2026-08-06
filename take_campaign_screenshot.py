import time
from playwright.sync_api import sync_playwright

def take_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        print("Logging in...")
        page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        page.fill('input[type="email"]', 'admin@talentops.ai')
        page.fill('input[type="password"]', '1012')
        page.click('button[type="submit"]')
        
        print("Waiting for login to complete...")
        time.sleep(5)
        
        print("Navigating directly to campaigns...")
        page.goto("http://127.0.0.1:5173/campaigns", wait_until="networkidle")
        time.sleep(3)
        
        print("Taking screenshot to see what is on the screen...")
        page.screenshot(path="C:\\Users\\User\\.gemini\\antigravity\\brain\\e050007d-77bf-4880-ac17-0d8a6b8d4518\\debug_campaigns_screen.png")
        
        # Now try to click
        if page.locator('button:has-text("New Campaign")').is_visible():
            print("Clicking New Campaign...")
            page.click('button:has-text("New Campaign")')
            
            # We are on step 1 (Audience). Click Continue to go to Compose
            print("Clicking Continue (Step 1)...")
            page.wait_for_selector('button:has-text("Continue")')
            page.click('button:has-text("Continue")')
            
            # We are on step 2 (Compose). Leave subject and body empty. Click Continue to Preview
            print("Clicking Continue (Step 2)...")
            page.wait_for_selector('button:has-text("Continue")')
            time.sleep(1) # wait for transition
            page.click('button:has-text("Continue")')
            
            print("Waiting for Preview to load or Validation toast...")
            time.sleep(3) # Wait for saving and preview to load
            
            # Take screenshot of the preview step showing the empty state message
            print("Taking screenshot...")
            page.screenshot(path="C:\\Users\\User\\.gemini\\antigravity\\brain\\e050007d-77bf-4880-ac17-0d8a6b8d4518\\campaign_fix_proof.png")
        else:
            print("Could not find New Campaign button.")
            
        browser.close()
        print("Done.")

if __name__ == "__main__":
    take_screenshot()
