import asyncio
from playwright.async_api import async_playwright
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

ARTIFACTS_DIR = r"C:\Users\User\.gemini\antigravity\brain\af41bbca-eae6-4fe8-82b8-160609b01afb"

# Dummy Outlook Bridge Server
class DummyOutlookBridge(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print(f"Dummy Bridge Received: {post_data.decode('utf-8')}")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"success":true}')

def run_dummy_server():
    server = HTTPServer(('127.0.0.1', 1337), DummyOutlookBridge)
    server.serve_forever()

async def run_verification():
    # Start dummy server in background
    server_thread = threading.Thread(target=run_dummy_server, daemon=True)
    server_thread.start()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Setup context with localStorage
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Injecting Auth State...")
        # Go to root to set localStorage on the origin
        await page.goto("http://localhost:5173/")
        await page.evaluate('''() => {
            localStorage.setItem('auth_session', JSON.stringify({token: "dummy", user: {id: 1, email: "admin@talentops.ai", role: "admin"}}));
            localStorage.setItem('talentops_app_token', 'dummy');
        }''')
        
        await page.goto("http://localhost:5173/campaigns", wait_until="networkidle")
        
        print("Taking 3x verification screenshot of Outlook Bridge UI...")
        
        for i in range(1, 4):
            print(f"--- Verification Loop {i} ---")
            
            # Fill out the form
            await page.fill("textarea", f"test{i}@example.com")
            
            # Use Tab or class selector to find the body.
            await page.fill("textarea[placeholder='Type your email here...']", f"Body {i}")
            
            # Click Send button
            await page.click("button:has-text('Send')")
            
            # Wait for Toast
            await page.wait_for_selector(".go3958317564", state="attached", timeout=5000)
            
            screenshot_path = os.path.join(ARTIFACTS_DIR, f"outlook_verify_{i}.png")
            await page.screenshot(path=screenshot_path)
            
            success_toast = await page.evaluate('''() => {
                const toast = document.querySelector('.go3958317564');
                return toast ? toast.innerText : "Not found";
            }''')
            
            print(f"SUCCESS: Captured Toast -> {success_toast}")
            
            # Refresh to clear toast
            await page.reload(wait_until="networkidle")
            await asyncio.sleep(1)
            
        await browser.close()
        print("All 3 checks complete.")

if __name__ == "__main__":
    asyncio.run(run_verification())
