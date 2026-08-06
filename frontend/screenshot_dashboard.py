from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5173/")
    page.wait_for_selector("text=Unknown State")
    page.screenshot(path="dashboard_after_sorting.png", full_page=True)
    browser.close()
