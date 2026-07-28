from playwright.sync_api import sync_playwright
import time
import os

def verify_dashboard(pass_num):
    print(f"Starting Verification Pass {pass_num}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            print(f"[{pass_num}] Navigating to Dashboard...")
            page.goto("http://localhost:5174/", timeout=30000)
            page.wait_for_timeout(5000)
            
            # Take a screenshot
            screenshot_path = os.path.abspath(f"C:/Users/User/.gemini/antigravity/brain/8ca93279-e790-4ae4-b3a8-41b138956926/dashboard_verification_pass_{pass_num}.png")
            page.screenshot(path=screenshot_path)
            
            # Check for the key text
            content = page.content()
            
            # Try to scrape some stats if possible
            if "Total Recruiters" in content or "Recruiters" in content:
                print(f"[{pass_num}] SUCCESS: Dashboard loaded successfully.")
            else:
                print(f"[{pass_num}] WARNING: Dashboard text missing, might still be loading.")
                
            print(f"[{pass_num}] Screenshot saved to {screenshot_path}")
            
        except Exception as e:
            print(f"[{pass_num}] FAILED: {e}")
        finally:
            browser.close()
            print(f"Verification Pass {pass_num} completed.\n")

if __name__ == "__main__":
    for i in range(1, 4):
        verify_dashboard(i)
        time.sleep(2)
