import asyncio
from playwright.async_api import async_playwright
import time
import os

async def run_test(p, attempt):
    print(f"--- Attempt {attempt} ---")
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    try:
        # Register a new user
        print('Registering new user...')
        await page.goto('http://127.0.0.1:5173/register')
        email = f"testuser_{attempt}_{int(time.time())}@talentops.com"
        await page.fill('input[placeholder="First name"]', 'Test')
        await page.fill('input[placeholder="Last name"]', 'User')
        await page.fill('input[placeholder="name@company.com"]', email)
        await page.fill('input[placeholder="Create a strong password"]', 'TestPassword123!')
        await page.fill('input[placeholder="Confirm your password"]', 'TestPassword123!')
        await page.click('input[type="checkbox"]') # Agree to terms
        await asyncio.sleep(0.5) # Wait for React state to update the submit button
        await page.click('button:has-text("Create Account")')
        
        # Wait for redirect to login
        await page.wait_for_url('http://127.0.0.1:5173/login', timeout=10000)
        
        print('Logging in with newly created user...')
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', 'TestPassword123!')
        await page.keyboard.press('Enter')
        
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2) # Give it a moment to complete login and set auth state
        
        print('Navigating to Campaigns...')
        await page.goto('http://127.0.0.1:5173/campaigns')
        
        print('Clicking New Campaign...')
        await page.click('button:has-text("New Campaign")')
        
        print('Waiting for Step 1...')
        await page.wait_for_selector('text="Upload CSV"', timeout=5000)
        
        # We need a sample CSV file to upload, or we can mock it?
        # Actually, let's create a temp csv file.
        with open('test_recipients.csv', 'w') as f:
            f.write('email,name\ntest1@example.com,Test 1\n')
            
        print('Uploading CSV...')
        # Upload file to the drag drop zone
        async with page.expect_file_chooser() as fc_info:
            await page.click('text="browse"') # clicking the "browse" link
        file_chooser = await fc_info.value
        await file_chooser.set_files('test_recipients.csv')
        
        # wait for it to validate
        await page.wait_for_selector('text="Valid"', timeout=10000)
        
        print('Clicking Continue to Step 2...')
        await page.click('button:has-text("Continue")')
        
        print('Waiting for Step 2...')
        await page.wait_for_selector('text="Email Subject"', timeout=5000)
        
        print('Typing subject and body...')
        await page.fill('input[placeholder="Enter campaign subject line"]', 'Test Subject')
        
        # Tiptap uses contenteditable
        await page.click('.ProseMirror')
        await page.keyboard.type('Hello World')
        
        print('Clicking Continue to Step 3...')
        await page.click('button:has-text("Continue")')
        
        print('Waiting for Step 3...')
        await page.wait_for_selector('text="All Checks Passed"', timeout=5000)
        print('? Success! "All Checks Passed" was found on the first load.')
        
        await page.screenshot(path=f'proof_attempt_{attempt}.png')
        
        return True
    except Exception as e:
        print(f"? Failed: {e}")
        await page.screenshot(path=f'proof_attempt_{attempt}_failed.png')
        return False
    finally:
        await browser.close()
        if os.path.exists('test_recipients.csv'):
            os.remove('test_recipients.csv')

async def main():
    async with async_playwright() as p:
        results = []
        for i in range(1, 4):
            res = await run_test(p, i)
            results.append(res)
            time.sleep(1)
        
        if all(results):
            print("\n? ALL 3 CHECKS PASSED.")
            with open('verification_proof.md', 'w') as f:
                f.write('# 3-Pass Verification Proof\n\n')
                f.write('The bug was fixed. I ran a Playwright script 3 times to simulate creating a new campaign, uploading recipients, entering a subject and body, and navigating to the Flight Check step.\n\n')
                f.write('In all 3 attempts, the preflight validation passed immediately without requiring the user to navigate back and forth.\n\n')
                f.write('## Screenshots\n')
                f.write('![Attempt 1](file:///C:/TalentOpsAI/proof_attempt_1.png)\n')
                f.write('![Attempt 2](file:///C:/TalentOpsAI/proof_attempt_2.png)\n')
                f.write('![Attempt 3](file:///C:/TalentOpsAI/proof_attempt_3.png)\n')
        else:
            print("\n? SOME CHECKS FAILED.")

if __name__ == '__main__':
    asyncio.run(main())
