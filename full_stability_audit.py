"""
FULL APPLICATION STABILITY AUDIT v3
Fixed login wait logic - waits for sidebar content instead of URL change.
"""
import json
import time
import sys
import os

os.makedirs("C:/TalentOpsAI/audit_screenshots", exist_ok=True)

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
CREDS = {"email": "admin@talentops.com", "password": "Password123!"}

ROUTES = [
    ("/",                    "Dashboard"),
    ("/recruiters",          "Recruiters"),
    ("/analytics",           "Analytics"),
    ("/ai-search",           "AI Search"),
    ("/directory",           "Directory"),
    ("/campaigns",           "Campaigns"),
    ("/profile",             "Profile"),
    ("/settings",            "Settings"),
    ("/admin",               "Admin Terminal"),
    ("/admin/devices",       "Trusted Devices"),
    ("/admin/users",         "User Management"),
    ("/admin/visitor-analytics", "Visitor Analytics"),
    ("/sentinel",            "Sentinel Dashboard"),
    ("/activity",            "Activity Log"),
    ("/admin/settings",      "Admin Settings"),
    ("/admin/health",        "System Health"),
    ("/admin/jobs",          "Background Jobs"),
    ("/admin/audit-logs",    "Audit Logs"),
]

def run_audit():
    results = []
    all_console_errors = []
    all_network_failures = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        console_logs = []
        def on_console(msg):
            try:
                console_logs.append({"type": msg.type, "text": msg.text[:300]})
            except:
                pass
        page.on("console", on_console)
        
        # ============================================================
        # PHASE 1: LOGIN
        # ============================================================
        print("=" * 70)
        print("PHASE 1: LOGIN")
        print("=" * 70)
        
        page.goto(f"{BASE}/login", timeout=20000)
        page.wait_for_timeout(2000)
        page.screenshot(path="C:/TalentOpsAI/audit_screenshots/01_login_page.png")
        print("  [OK] Login page loaded")
        
        page.fill("input[type='email']", CREDS["email"])
        page.fill("input[type='password']", CREDS["password"])
        page.click("button[type='submit']")
        print("  [OK] Login button clicked, waiting for app shell...")
        
        # Wait for the app shell (sidebar) to appear - this means auth succeeded
        try:
            page.wait_for_selector(".cc-shell, .cc-sidebar, [class*='sidebar']", timeout=20000)
            print("  [OK] App shell rendered - login successful!")
        except:
            # Fallback: check for any dashboard-like content
            page.wait_for_timeout(5000)
            body = page.locator("body").inner_text()
            if "Dashboard" in body:
                print("  [OK] Dashboard content found - login successful!")
            else:
                print(f"  [FAIL] No app shell found. Body: {body[:200]}")
                browser.close()
                return
        
        page.wait_for_timeout(2000)
        page.screenshot(path="C:/TalentOpsAI/audit_screenshots/02_post_login.png")
        print(f"  [OK] Final URL: {page.url}")
        
        # ============================================================
        # PHASE 2: TEST EVERY ROUTE
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 2: ROUTE-BY-ROUTE AUDIT")
        print("=" * 70)
        
        for i, (route, name) in enumerate(ROUTES):
            print(f"\n--- [{i+1}/{len(ROUTES)}] {name} ({route}) ---")
            route_result = {
                "route": route,
                "name": name,
                "status": "UNKNOWN",
                "load_time_ms": 0,
                "console_errors": [],
                "network_failures": [],
                "has_content": False,
                "is_blank": False,
                "content_length": 0,
                "final_url": "",
            }
            
            console_logs.clear()
            network_failures = []
            
            def make_resp_handler(fl):
                def h(response):
                    if response.status >= 400:
                        fl.append({"url": response.url[:200], "status": response.status, "method": response.request.method})
                return h
            
            def make_fail_handler(fl):
                def h(request):
                    fl.append({"url": request.url[:200], "method": request.method, "failure": str(request.failure)[:100] if request.failure else "unknown"})
                return h
            
            rh = make_resp_handler(network_failures)
            fh = make_fail_handler(network_failures)
            page.on("response", rh)
            page.on("requestfailed", fh)
            
            start = time.time()
            try:
                page.goto(f"{BASE}{route}", timeout=20000)
                page.wait_for_timeout(5000)  # Wait for APIs
            except Exception as e:
                route_result["status"] = f"NAVIGATION_FAIL: {str(e)[:100]}"
                print(f"  [FAIL] Navigation error: {str(e)[:100]}")
                results.append(route_result)
                page.remove_listener("response", rh)
                page.remove_listener("requestfailed", fh)
                continue
            
            elapsed = (time.time() - start) * 1000
            route_result["load_time_ms"] = round(elapsed)
            route_result["final_url"] = page.url
            
            safe_name = name.lower().replace(" ", "_").replace("/", "_")
            page.screenshot(path=f"C:/TalentOpsAI/audit_screenshots/{i+3:02d}_{safe_name}.png")
            
            try:
                body_text = page.locator("body").inner_text()
                route_result["content_length"] = len(body_text.strip())
                route_result["has_content"] = len(body_text.strip()) > 20
                route_result["is_blank"] = len(body_text.strip()) < 5
            except:
                route_result["is_blank"] = True
            
            route_errors = [log for log in console_logs if log["type"] == "error"]
            route_result["console_errors"] = route_errors[:5]
            
            # Filter noise
            sig_failures = []
            for nf in network_failures:
                url = nf.get("url", "")
                status = nf.get("status", 0)
                # Skip expected optional failures
                if status == 404 and any(skip in url for skip in ["/bridge/status", "/updates/", "/notifications", "favicon"]):
                    continue
                if status == 405:  # Method not allowed (preflight issues)
                    continue
                sig_failures.append(nf)
            
            route_result["network_failures"] = sig_failures[:10]
            
            # Determine status
            if route_result["is_blank"]:
                route_result["status"] = "FAIL_BLANK"
            elif any(nf.get("status", 0) >= 500 for nf in sig_failures):
                route_result["status"] = "FAIL_SERVER_ERROR"
            elif any(nf.get("status", 0) == 401 for nf in sig_failures):
                route_result["status"] = "FAIL_AUTH"
            elif route_result["content_length"] < 20:
                route_result["status"] = "FAIL_NO_CONTENT"
            elif sig_failures:
                route_result["status"] = "WARN_NETWORK"
            elif route_errors:
                route_result["status"] = "WARN_CONSOLE_ERRORS"
            else:
                route_result["status"] = "PASS"
            
            all_console_errors.extend(route_errors)
            all_network_failures.extend(sig_failures)
            
            icon = "[OK]  " if route_result["status"] == "PASS" else "[WARN]" if "WARN" in route_result["status"] else "[FAIL]"
            print(f"  {icon} {name}: {route_result['status']} ({route_result['load_time_ms']}ms, {route_result['content_length']} chars)")
            for nf in sig_failures[:3]:
                print(f"    NET: {nf.get('method','?')} {nf['url'][:80]} -> {nf.get('status', nf.get('failure', '?'))}")
            for re_item in route_errors[:2]:
                print(f"    CONSOLE ERROR: {re_item['text'][:100]}")
            
            page.remove_listener("response", rh)
            page.remove_listener("requestfailed", fh)
            results.append(route_result)
        
        # ============================================================
        # PHASE 3: RAPID NAVIGATION
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 3: RAPID NAVIGATION SWITCHING")
        print("=" * 70)
        
        for route in ["/", "/recruiters", "/analytics", "/campaigns", "/directory", "/profile", "/settings", "/"]:
            start = time.time()
            try:
                page.goto(f"{BASE}{route}", timeout=10000)
                page.wait_for_timeout(1500)
                elapsed = (time.time() - start) * 1000
                body_len = len(page.locator("body").inner_text().strip())
                status = "OK" if body_len > 20 else "BLANK"
                print(f"  [{status}] {route:20s} -> {elapsed:6.0f}ms ({body_len} chars)")
            except Exception as e:
                print(f"  [FAIL] {route:20s} -> {str(e)[:80]}")
        
        # ============================================================
        # PHASE 4: REFRESH TEST
        # ============================================================
        print("\n" + "=" * 70)
        print("PHASE 4: REFRESH STABILITY")
        print("=" * 70)
        
        for route in ["/", "/recruiters", "/profile", "/campaigns", "/analytics", "/admin/devices"]:
            try:
                page.goto(f"{BASE}{route}", timeout=15000)
                page.wait_for_timeout(2000)
                pre = len(page.locator("body").inner_text().strip())
                page.reload(timeout=15000)
                page.wait_for_timeout(3000)
                post = len(page.locator("body").inner_text().strip())
                status = "OK" if post > 20 else "BLANK"
                print(f"  [{status}] Refresh {route:25s} -> before: {pre:5d}, after: {post:5d} chars")
                safe = route.replace("/", "_") or "root"
                page.screenshot(path=f"C:/TalentOpsAI/audit_screenshots/refresh{safe}.png")
            except Exception as e:
                print(f"  [FAIL] Refresh {route:25s} -> {str(e)[:80]}")
        
        browser.close()
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    
    pc = sum(1 for r in results if r["status"] == "PASS")
    wc = sum(1 for r in results if "WARN" in r["status"])
    fc = sum(1 for r in results if "FAIL" in r["status"])
    
    print(f"\n  Routes Tested: {len(results)}")
    print(f"  PASS:  {pc}")
    print(f"  WARN:  {wc}")
    print(f"  FAIL:  {fc}")
    
    if fc > 0:
        print(f"\n  FAILING ROUTES:")
        for r in results:
            if "FAIL" in r["status"]:
                print(f"    {r['name']:25s} ({r['route']:25s}): {r['status']}")
                for nf in r["network_failures"][:3]:
                    print(f"      NET: {nf.get('method','?')} {nf['url'][:80]} -> {nf.get('status', nf.get('failure', '?'))}")
    
    if wc > 0:
        print(f"\n  WARNING ROUTES:")
        for r in results:
            if "WARN" in r["status"]:
                print(f"    {r['name']:25s} ({r['route']:25s}): {r['status']}")
                for nf in r["network_failures"][:3]:
                    print(f"      NET: {nf.get('method','?')} {nf['url'][:80]} -> {nf.get('status', nf.get('failure', '?'))}")
    
    # Unique console errors
    ue = {}
    for e in all_console_errors:
        k = e["text"][:80]
        ue[k] = ue.get(k, 0) + 1
    if ue:
        print(f"\n  UNIQUE CONSOLE ERRORS ({len(ue)}):")
        for msg, count in sorted(ue.items(), key=lambda x: -x[1]):
            print(f"    [{count}x] {msg}")
    
    with open("C:/TalentOpsAI/audit_screenshots/audit_results.json", "w") as f:
        json.dump({"results": results, "console_errors": all_console_errors[:30], "network_failures": all_network_failures[:50], "summary": {"pass": pc, "warn": wc, "fail": fc}}, f, indent=2, default=str)
    
    print(f"\n  Full results: C:/TalentOpsAI/audit_screenshots/audit_results.json")

if __name__ == "__main__":
    run_audit()
