import os
import time
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\User\.gemini\antigravity\brain\285f6c8d-71ab-4abe-9e7b-e4d39e260a9f"

targets = [
    ("proof_recruiters_4color.png", "http://127.0.0.1:5173/recruiters"),
    ("proof_campaigns_4color.png", "http://127.0.0.1:5173/campaigns"),
    ("proof_directory_4color.png", "http://127.0.0.1:5173/directory"),
]

for filename, url in targets:
    print(f"Capturing {filename} from {url}...")
    try:
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

            page.goto(url, wait_until="domcontentloaded")
            time.sleep(2.5)
            out_path = os.path.join(artifact_dir, filename)
            page.screenshot(path=out_path, full_page=False)
            browser.close()
            print(f"Successfully saved {out_path}")
    except Exception as e:
        print(f"Error capturing {filename}: {e}")

print("Done captures!")
