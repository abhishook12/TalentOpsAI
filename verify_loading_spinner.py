from playwright.sync_api import sync_playwright
import time
import sys

def verify_live_site():
    print("Starting live site verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        print("Navigating to https://talent-ops-ai.vercel.app ...")
        try:
            # We don't want to wait until "load" state because if it hangs, it might time out. 
            # We just want to see what renders immediately.
            page.goto("https://talent-ops-ai.vercel.app", wait_until="commit", timeout=15000)
        except Exception as e:
            print(f"Navigation issue: {e}")

        # Wait a moment for React to render the initial state
        page.wait_for_timeout(2000)
        
        # Take a screenshot of the loading state
        page.screenshot(path="C:\\TalentOpsAI\\frontend\\screenshots\\loading_state.png")
        print("Saved screenshot of initial state to C:\\TalentOpsAI\\frontend\\screenshots\\loading_state.png")

        # Check for the loader text
        loader_text = page.locator("text=Waking up the server...")
        if loader_text.count() > 0:
            print("SUCCESS: Loading spinner is visible on the screen!")
        else:
            print("WARNING: Loading spinner text not found. The screen might still be blank or already loaded.")
            
        # Check if we eventually hit the login page
        print("Waiting for login page or dashboard to appear (up to 20s)...")
        try:
            page.wait_for_selector("input[type='email']", timeout=20000)
            print("SUCCESS: Site successfully loaded past the loading screen.")
            page.screenshot(path="C:\\TalentOpsAI\\frontend\\screenshots\\loaded_state.png")
        except Exception as e:
            print("Trying dashboard selector...")
            try:
                page.wait_for_selector(".cc-shell", timeout=5000)
                print("SUCCESS: Site successfully loaded past the loading screen (Dashboard).")
                page.screenshot(path="C:\\TalentOpsAI\\frontend\\screenshots\\loaded_state.png")
            except Exception as e2:
                print("WARNING: Site did not load past the loading screen within 20s.")

        browser.close()

if __name__ == "__main__":
    verify_live_site()
