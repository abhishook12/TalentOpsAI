import os
import time
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\User\.gemini\antigravity\brain\285f6c8d-71ab-4abe-9e7b-e4d39e260a9f"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-gpu', '--no-sandbox'])
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    # Pre-populate localStorage
    page.goto("http://127.0.0.1:5173/login", wait_until="commit")
    time.sleep(0.5)
    page.evaluate("""() => {
        localStorage.setItem('session_token', 'legacy_admin_bypass_token');
        localStorage.setItem('auth_session', JSON.stringify({
            id: 'admin',
            email: 'abhishekjadon824@gmail.com',
            first_name: 'Abhishek',
            role: 'superadmin'
        }));
    }""")
    time.sleep(0.5)

    print("Navigating to Dashboard...")
    page.goto("http://127.0.0.1:5173/", wait_until="networkidle")
    time.sleep(3.0)

    # Scroll down 800px so Data Integrity Health is right in the center
    page.evaluate("window.scrollTo(0, 800)")
    time.sleep(1.0)

    out_path = os.path.join(artifact_dir, "proof_data_integrity_health.png")
    page.screenshot(path=out_path, full_page=False)
    print(f"Captured: {out_path}")

    browser.close()
    print("Done!")
