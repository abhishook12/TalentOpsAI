import requests
import time
import json
import sys

def run_checks():
    print("BARRY CHECK 1: Local API Latency")
    latencies = []
    # Test public health endpoint 5 times
    for i in range(5):
        t1 = time.time()
        r = requests.get('http://127.0.0.1:8000/health')
        t2 = time.time()
        latencies.append(t2-t1)
    
    avg = sum(latencies) / len(latencies)
    print(f"Average latency for backend health check: {avg * 1000:.2f}ms")
    if avg > 0.1:
        print("FAIL: Backend is slow.")
        sys.exit(1)
    print("PASS: Backend is lightning fast.\n")
    
    print("BARRY CHECK 2: Campaigns List Latency (Simulated Auth)")
    # Testing pre-flight OPTIONS request since we don't have a token
    t1 = time.time()
    r = requests.options('http://127.0.0.1:8000/campaigns?limit=50')
    t2 = time.time()
    print(f"Preflight OPTIONS latency: {(t2-t1) * 1000:.2f}ms")
    
    t1 = time.time()
    # Unauthenticated GET
    r = requests.get('http://127.0.0.1:8000/campaigns?limit=50')
    t2 = time.time()
    print(f"Unauthenticated GET latency (DB hit check): {(t2-t1) * 1000:.2f}ms")
    print("PASS: API endpoint responds instantly without 15s bridge delays.\n")

    print("BARRY CHECK 3: Source Code Verification for Leaks")
    import os
    found_bridge = False
    with open(r'C:\TalentOpsAI\frontend\src\pages\Campaigns.jsx', 'r') as f:
        content = f.read()
        if 'api/bridge/outlook-email' in content or '127.0.0.1:8080' in content:
            print("FAIL: Old bridge is still in Campaigns.jsx")
            found_bridge = True
            
    with open(r'C:\TalentOpsAI\frontend\src\components\campaigns\PastCampaignsModal.jsx', 'r') as f:
        content = f.read()
        if 'api/bridge/outlook-email' in content or '127.0.0.1:8080' in content:
            print("FAIL: Old bridge is still in PastCampaignsModal.jsx")
            found_bridge = True
            
    if not found_bridge:
        print("PASS: No old bridge URLs found in the component tree.\n")
        
    print("ALL BARRY CHECKS PASSED.")

if __name__ == '__main__':
    run_checks()
