from playwright.sync_api import sync_playwright
import time
import os

URL = 'https://talent-ops-ai.vercel.app'
OUTPUT = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\af41bbca-eae6-4fe8-82b8-160609b01afb'

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={'width': 1280, 'height': 800})
        
        print("Logging in...")
        page.goto(URL)
        page.fill('input[type="email"]', 'testfake1@example.com')
        page.fill('input[type="password"]', 'Admin123!')
        page.click('button[type="submit"]')
        
        try:
            page.wait_for_selector('text=Command Center Dashboard', timeout=15000)
            print("Logged in!")
        except:
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_login_error.png'))
            print("Login error.")
            b.close()
            return
            
        print("Going to campaigns...")
        page.goto(f'{URL}/campaigns')
        page.wait_for_selector('text=New Campaign', timeout=10000)
        
        time.sleep(5)
        page.screenshot(path=os.path.join(OUTPUT, 'live_uat_campaigns_status.png'))
        
        page.click('text=New Campaign')
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT, 'live_uat_modal_open.png'))
        
        print("Adding recipients...")
        try:
            page.click('text=Manual & CSV')
            time.sleep(1)
            
            import sys
            num_recipients = int(sys.argv[1]) if len(sys.argv) > 1 else 1
            emails = [f'talentops.test.{int(time.time())}.{i}@mailinator.com' for i in range(1, num_recipients + 1)]
            
            page.fill('textarea[placeholder="Paste email addresses here (one per line)..."]', '\n'.join(emails))
            page.click('button:has-text("Validate & Add")')
            
            # Wait for validation API to finish
            page.wait_for_selector(f'text="Selected Recipients ({num_recipients})"', timeout=30000)
            time.sleep(1)
                
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_recipients.png'))
            page.click('button:has-text("Continue")')
            time.sleep(1)
        except Exception as e:
            print("Failed at recipients: ", e)
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_fail_2.png'))
            b.close()
            return
            
        print("Composing email...")
        try:
            page.fill('input[placeholder*="Enter subject"]', 'Urgent: Action Required for {{first_name}}')
            # Wait for ProseMirror
            page.click('.ProseMirror')
            page.keyboard.type('Hello {{first_name}}, this is a production test for TalentOps AI. Do not reply.')
            
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_composer.png'))
            
            page.click('button:has-text("Continue")')
            time.sleep(1)
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_review.png'))
        except Exception as e:
            print("Failed at composer: ", e)
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_fail_3.png'))
            b.close()
            return
            
        print("Launching campaign...")
        try:
            # Wait for preflight to finish and button to appear AND turn green (ready)
            print("Waiting for preflight validation...")
            page.wait_for_selector('button.bg-green-600:has-text("Launch Campaign")', timeout=120000)
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_review.png'))
            page.click('button.bg-green-600:has-text("Launch Campaign")')
            
            # Wait for success toast or redirect to dashboard
            page.wait_for_selector('text=Campaign engine started successfully!', timeout=15000)
            time.sleep(2)
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_launched.png'))
            
            # Go back to campaigns list to check status
            page.click('text=Campaigns')
            time.sleep(3)
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_final_list.png'))
        except Exception as e:
            print("Failed at launch: ", e)
            page.screenshot(path=os.path.join(OUTPUT, 'live_uat_fail_4.png'))
            b.close()
            return
            
        b.close()
        print("Done.")

if __name__ == "__main__":
    main()
