import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def dump_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        print("Logging in...")
        page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        page.fill('input[type="email"]', 'admin@talentops.ai')
        page.fill('input[type="password"]', '1012')
        page.click('button[type="submit"]')
        
        print("Waiting for login to complete...")
        time.sleep(5)
        
        print("Navigating directly to campaigns...")
        page.goto("http://127.0.0.1:5173/campaigns", wait_until="networkidle")
        time.sleep(3)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        with open("C:\\Users\\User\\.gemini\\antigravity\\brain\\e050007d-77bf-4880-ac17-0d8a6b8d4518\\campaigns_page_text.txt", "w", encoding="utf-8") as f:
            f.write(text)
            
        print("Saved page text.")
        browser.close()

if __name__ == "__main__":
    dump_html()
