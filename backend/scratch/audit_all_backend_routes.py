import os
import sys
import requests
import json
import time

sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))

BASE_URL = "http://localhost:8000"

def audit_all_endpoints():
    print("=================================================================")
    print("=== TALENTOPSAI COMPREHENSIVE BACKEND ENDPOINTS AUDIT ===")
    print("=================================================================")
    
    # 1. Public & Core Endpoints
    public_endpoints = [
        ("GET", "/health", 200),
        ("GET", "/ping", 200),
        ("GET", "/version", 200),
        ("GET", "/system/enricher/status", 200),
        ("GET", "/analytics/dashboard", 200),
        ("GET", "/analytics/recruiters-by-state", 200),
        ("GET", "/analytics/data-quality", 200),
        ("GET", "/analytics/companies-search?query=aerotek", 200),
        ("GET", "/companies/search?query=aerotek", 200),
        ("GET", "/companies/1", (200, 404)),
        ("GET", "/recruiters/locations", 200),
        ("GET", "/recruiters/stats", 200),
    ]
    
    print("\n--- [AUDIT PHASE 1: PUBLIC / ANONYMOUS ENDPOINTS] ---")
    pass_count = 0
    fail_count = 0
    
    for method, path, expected_status in public_endpoints:
        url = f"{BASE_URL}{path}"
        try:
            t0 = time.time()
            if method == "GET":
                r = requests.get(url, timeout=5)
            elif method == "POST":
                r = requests.post(url, json={}, timeout=5)
            latency = (time.time() - t0) * 1000
            
            allowed = expected_status if isinstance(expected_status, tuple) else (expected_status,)
            if r.status_code in allowed:
                print(f"  [PASS] {method:4} {path:45} -> {r.status_code} ({latency:.1f}ms)", flush=True)
                pass_count += 1
            else:
                print(f"  [FAIL] {method:4} {path:45} -> {r.status_code} (Expected {expected_status}) ({latency:.1f}ms)", flush=True)
                fail_count += 1
        except Exception as e:
            print(f"  [ERR]  {method:4} {path:45} -> Exception: {e}", flush=True)
            fail_count += 1

    # 2. Protected Endpoints (Must return 401 Unauthorized without auth cookie)
    print("\n--- [AUDIT PHASE 2: SECURITY & AUTHENTICATION GATES] ---", flush=True)
    protected_endpoints = [
        ("GET", "/recruiters/"),
        ("GET", "/campaigns/"),
        ("GET", "/candidates/"),
        ("GET", "/submissions/"),
        ("GET", "/vendors/"),
        ("GET", "/accounts/"),
        ("GET", "/users/"),
        ("GET", "/mailintel/dashboard"),
        ("GET", "/admin/workers/status"),
        ("GET", "/admin/metrics"),
        ("GET", "/visitor-analytics/stats"),
    ]
    for method, path in protected_endpoints:
        url = f"{BASE_URL}{path}"
        try:
            t0 = time.time()
            r = requests.get(url, timeout=5)
            latency = (time.time() - t0) * 1000
            if r.status_code in (401, 403):
                print(f"  [PASS] {method:4} {path:45} -> {r.status_code} (Protected) ({latency:.1f}ms)", flush=True)
                pass_count += 1
            else:
                print(f"  [FAIL] {method:4} {path:45} -> {r.status_code} (Expected 401/403) ({latency:.1f}ms)", flush=True)
                fail_count += 1
        except Exception as e:
            print(f"  [ERR]  {method:4} {path:45} -> Exception: {e}", flush=True)
            fail_count += 1

    print("\n=================================================================")
    print(f"AUDIT SUMMARY: {pass_count} Passed | {fail_count} Failed")
    print("=================================================================")
    return fail_count == 0

if __name__ == "__main__":
    success = audit_all_endpoints()
    if not success:
        sys.exit(1)
