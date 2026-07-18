from playwright.sync_api import sync_playwright
import time
import os

URL = "https://talent-ops-ai.vercel.app"

def verify_live():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})
        
        print(f"Navigating to {URL}/login...")
        page.goto(f"{URL}/login")
        
        print("Logging in...")
        page.fill('input[type="email"]', 'admin@example.com')
        page.fill('input[type="password"]', 'adminpass')
        page.click('button:has-text("Sign in")')
        
        page.wait_for_url(f"{URL}/")
        print("Login successful. Navigating to campaigns...")
        
        page.goto(f"{URL}/campaigns")
        page.wait_for_selector('text="New Campaign"', timeout=10000)
        
        # Click new campaign to open the wizard
        page.click('button:has-text("New Campaign")')
        time.sleep(2)
        
        # We are on Step 1: Recipients
        page.screenshot(path="live_campaign_step1.png")
        
        # Go to step 2: Compose
        page.click('button:has-text("Continue")')
        time.sleep(2)
        page.screenshot(path="live_campaign_step2.png")
        
        print("Screenshots captured.")
        browser.close()

if __name__ == "__main__":
    verify_live()
