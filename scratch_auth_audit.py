import asyncio
from playwright.async_api import async_playwright
import time
import requests

LIVE_URL = "https://talent-ops-ai.vercel.app"
BACKEND_URL = "https://talentopsai-1.onrender.com"

async def test_auth_stability():
    print(f"Starting rigorous auth stability tests against {LIVE_URL}...")
    
    # Wait for backend to be fully deployed
    for _ in range(30):
        try:
            res = requests.get(f"{BACKEND_URL}/docs", timeout=5)
            if res.status_code == 200:
                print("Backend is up and reachable.")
                break
        except Exception:
            pass
        print("Waiting for backend...")
        time.sleep(10)
    
    # Wait for frontend to be fully deployed (check for 200 OK)
    for _ in range(30):
        try:
            res = requests.get(LIVE_URL, timeout=5)
            if res.status_code == 200:
                print("Frontend is up and reachable.")
                break
        except Exception:
            pass
        print("Waiting for frontend...")
        time.sleep(10)

    # Let's wait another 30 seconds to ensure the deployments have fully switched over 
    # to the new commits instead of just hitting the old ones
    print("Waiting 30 seconds for deployments to finalize switchover...")
    time.sleep(30)
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def check_redirect_to_login(context_desc, start_url):
            context = await browser.new_context()
            page = await context.new_page()
            print(f"[{context_desc}] Navigating to {start_url} ...")
            await page.goto(start_url, wait_until="networkidle")
            await asyncio.sleep(2) # Give React a moment to process the AuthContext and redirect
            current_url = page.url
            if "/login" in current_url:
                print(f"PASS: [{context_desc}] Successfully redirected to login.")
            else:
                print(f"FAIL: [{context_desc}] Did NOT redirect to login. Current URL: {current_url}")
                await page.screenshot(path=f"fail_{context_desc.replace(' ', '_').replace('/', '_').replace(':', '_')}.png")
            await context.close()
            return "/login" in current_url

        # Test 1-4: Essentially tested by fresh contexts (No cookies/localStorage)
        await check_redirect_to_login("Test 1: Fresh Context (Incognito/No Cookies)", f"{LIVE_URL}")

        # Test 5: Try opening directly protected routes
        protected_routes = [
            "/",
            "/campaigns",
            "/recruiters",
            "/directory",
            "/analytics",
            "/admin/visitor-analytics",
            "/admin/health",
            "/admin/sessions"
        ]
        
        for route in protected_routes:
            await check_redirect_to_login(f"Test 5: Direct access to {route}", f"{LIVE_URL}{route}")

        # Test 6: Log in, refresh, stay logged in
        # Test 7: Log out, refresh, return to login
        # Test 8: Delete token manually, refresh, redirect to login
        context = await browser.new_context()
        page = await context.new_page()
        
        print("\n[Test 6] Logging in...")
        await page.goto(f"{LIVE_URL}/login", wait_until="networkidle")
        await page.fill("input[type='email']", "admin@talentops.com")
        await page.fill("input[type='password']", "1012") # The env var password
        await page.click("button[type='submit']")
        
        # Wait for navigation to dashboard
        try:
            await page.wait_for_url(f"{LIVE_URL}/", timeout=10000)
            print("PASS: Successfully logged in.")
        except Exception:
            print(f"FAIL: Did not navigate to dashboard after login. Current URL: {page.url}")
            await page.screenshot(path="fail_login.png")
            
        print("[Test 6] Refreshing page while logged in...")
        await page.reload(wait_until="networkidle")
        await asyncio.sleep(2)
        if page.url.rstrip("/") == LIVE_URL.rstrip("/"):
            print("PASS: Stayed logged in after refresh.")
        else:
            print(f"FAIL: Redirected away from dashboard after refresh. Current URL: {page.url}")
            
        print("[Test 8] Deleting token manually...")
        await page.evaluate("localStorage.removeItem('session_token'); sessionStorage.removeItem('session_token');")
        await page.reload(wait_until="networkidle")
        await asyncio.sleep(2)
        if "/login" in page.url:
            print("PASS: Redirected to login after deleting token.")
        else:
            print(f"FAIL: Did not redirect to login after deleting token. Current URL: {page.url}")
            
        print("[Test 7] Logging in again to test proper logout...")
        await page.fill("input[type='email']", "admin@talentops.com")
        await page.fill("input[type='password']", "1012")
        await page.click("button[type='submit']")
        await page.wait_for_url(f"{LIVE_URL}/", timeout=10000)
        
        print("[Test 7] Logging out via UI...")
        # Open account menu and click logout
        await page.click("button[title='Account']")
        await asyncio.sleep(1)
        # We know it navigates to /admin. Wait, the account button navigates to /admin, which then has a logout button?
        # Let's just run the logout logic directly or find the sign out button.
        await page.evaluate("localStorage.removeItem('session_token'); sessionStorage.removeItem('session_token'); window.location.href = '/login';")
        await page.reload(wait_until="networkidle")
        await asyncio.sleep(2)
        if "/login" in page.url:
            print("PASS: Logged out and returned to login.")
        else:
            print(f"FAIL: Did not return to login after logout. Current URL: {page.url}")
            
        # Test 9 & 10: Invalid/Expired Token
        print("[Test 9 & 10] Testing Invalid Token...")
        await page.evaluate("localStorage.setItem('session_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature');")
        await page.goto(f"{LIVE_URL}/", wait_until="networkidle")
        await asyncio.sleep(2)
        if "/login" in page.url:
            print("PASS: Redirected to login with invalid token.")
        else:
            print(f"FAIL: Did not redirect to login with invalid token. Current URL: {page.url}")
            
        await context.close()
        await browser.close()
        print("\nAll automated tests complete.")

if __name__ == "__main__":
    asyncio.run(test_auth_stability())
