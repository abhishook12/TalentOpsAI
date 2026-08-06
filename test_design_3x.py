import subprocess
import time
import os
import requests
from playwright.sync_api import sync_playwright

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            res = requests.get(url)
            if res.status_code != 500:
                return True
        except:
            pass
        time.sleep(1)
    return False

def test_design_3x():
    print("Starting frontend...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", "5173", "--strictPort"],
        cwd=r"C:\TalentOpsAI\frontend",
        shell=True
    )
    
    try:
        print("Waiting for frontend to boot...")
        time.sleep(5) # give vite extra time
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            
            print("Navigating to test-campaigns...")
            page.goto("http://localhost:5173/test-campaigns")
            
            try:
                page.wait_for_selector(".campaigns-bento-grid", timeout=15000)
            except Exception as e:
                print("Failed to find .campaigns-bento-grid, taking error screenshot...")
                os.makedirs(r"C:\TalentOpsAI\screenshots", exist_ok=True)
                page.screenshot(path=r"C:\TalentOpsAI\screenshots\error_state.png", full_page=True)
                raise e
            
            os.makedirs(r"C:\TalentOpsAI\screenshots", exist_ok=True)
            
            print("\n--- ATTEMPT 1 ---")
            page.reload()
            page.wait_for_selector(".campaigns-bento-grid")
            time.sleep(2)
            page.screenshot(path=r"C:\TalentOpsAI\screenshots\campaigns_bento_1.png", full_page=True)
            print("SUCCESS: Campaigns Bento Grid rendered successfully.")
            
            print("\n--- ATTEMPT 2 ---")
            page.reload()
            page.wait_for_selector(".campaigns-bento-grid")
            time.sleep(2)
            page.screenshot(path=r"C:\TalentOpsAI\screenshots\campaigns_bento_2.png", full_page=True)
            print("SUCCESS: Campaigns Bento Grid rendered successfully.")
            
            print("\n--- ATTEMPT 3 ---")
            page.reload()
            page.wait_for_selector(".campaigns-bento-grid")
            time.sleep(2)
            page.screenshot(path=r"C:\TalentOpsAI\screenshots\campaigns_bento_3.png", full_page=True)
            print("SUCCESS: Campaigns Bento Grid rendered successfully.")
            
            print("\nFINAL RESULT: 3/3 Passes completed successfully.")
            print("3-PASS VERIFICATION SUCCESSFUL")
            browser.close()
            
    finally:
        print("Shutting down servers...")
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    test_design_3x()
