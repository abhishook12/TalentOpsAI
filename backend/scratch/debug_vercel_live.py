from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    
    # Listen to console and network errors
    page.on('console', lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
    page.on('response', lambda response: print(f"[HTTP {response.status}] {response.url}"))
    page.on('requestfailed', lambda req: print(f"[REQ FAILED] {req.url} - {req.failure}"))
    
    print("Navigating to https://talent-ops-ai.vercel.app/login...")
    page.goto('https://talent-ops-ai.vercel.app/login')
    page.wait_for_timeout(2000)
    
    page.fill('input[type="email"]', 'admin@talentops.ai')
    # try password or check other emails
    passwords = ['AdminPassword123!', 'adminpass', 'Admin123!', 'Admin@123', 'password']
    
    # Let's inspect local storage or try login
    page.fill('input[type="password"]', 'AdminPassword123!')
    page.click('button:has-text("Sign in")')
    page.wait_for_timeout(3000)
    
    print(f"Current URL after login attempt: {page.url}")
    
    print("Navigating to /recruiters...")
    page.goto('https://talent-ops-ai.vercel.app/recruiters')
    page.wait_for_timeout(5000)
    
    page.screenshot(path='vercel_recruiters_live_debug.png')
    browser.close()
