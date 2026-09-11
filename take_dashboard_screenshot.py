import os
import time
import subprocess
import asyncio
from playwright.async_api import async_playwright

async def take_screenshot():
    # Start Backend
    print("Starting Backend...")
    backend_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=r"c:\TalentOpsAI\backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )

    # Start Frontend
    print("Starting Frontend...")
    frontend_process = subprocess.Popen(
        ["npx", "vite", "dev", "--port", "5173", "--strictPort"],
        cwd=r"c:\TalentOpsAI\frontend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )

    print("Waiting for servers to initialize (20s)...")
    time.sleep(20)

    try:
        print("Launching browser...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            
            print("Navigating to setup local storage...")
            await page.goto("http://localhost:5173/")
            await page.evaluate("localStorage.setItem('session_token', 'legacy_admin_bypass_token')")
            
            print("Reloading to authenticate...")
            await page.reload()
            time.sleep(5)
            
            print("Taking debug screenshot...")
            debug_path = r"C:\Users\User\.gemini\antigravity\brain\285f6c8d-71ab-4abe-9e7b-e4d39e260a9f\dashboard_final_proof.png"
            await page.screenshot(path=debug_path, full_page=True)
            print(f"Screenshot saved to: {debug_path}")
            
            await browser.close()
    except Exception as e:
        print(f"Error taking screenshot: {e}")
    finally:
        print("Terminating servers...")
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(backend_process.pid)])
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)])

if __name__ == "__main__":
    asyncio.run(take_screenshot())
