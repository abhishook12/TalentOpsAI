from playwright.sync_api import sync_playwright
import time
import sys

def main():
    print("Waiting 60 seconds for Vercel deployment...")
    time.sleep(60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to live register page...")
        page.goto("https://talent-ops-ai.vercel.app/register")
        
        # Wait for form to load
        page.wait_for_selector(".auth-form-container")
        
        screenshot_path = "C:\\TalentOpsAI\\register_production_fix.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")
        
        browser.close()

if __name__ == "__main__":
    main()
