from playwright.sync_api import sync_playwright
import time

URL = "https://talent-ops-1emsfwxp0-abhishek-s-projects10.vercel.app"

def verify_live():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})
        
        # Listen to console logs
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        
        print(f"Navigating to {URL}/login...")
        page.goto(f"{URL}/login")
        
        print("Logging in...")
        page.fill('input[type="email"]', 'admin@example.com')
        page.fill('input[type="password"]', 'adminpass')
        page.click('button:has-text("Sign in")')
        
        time.sleep(5)
        # Take a screenshot to see if login failed
        page.screenshot(path="live_login_error_new.png")
        print("Login attempt screenshot captured.")
        
        browser.close()

if __name__ == "__main__":
    verify_live()
