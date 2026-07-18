import requests
import time
import json

BASE = "http://127.0.0.1:8000"

def profile_endpoint(name, url, timeout=120):
    print(f"\n--- Profiling: {name} ---")
    t0 = time.time()
    try:
        r = requests.get(url, timeout=timeout)
        t1 = time.time()
        elapsed = t1 - t0
        size = len(r.content)
        print(f"  Status: {r.status_code}")
        print(f"  Response time: {elapsed:.2f}s")
        print(f"  Response size: {size:,} bytes ({size/1024:.1f} KB)")
        
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(f"  Items returned: {len(data)}")
                if data:
                    print(f"  Keys per item: {list(data[0].keys())}")
                    # Check for nested data bloat
                    sample = json.dumps(data[0])
                    print(f"  Single item size: {len(sample):,} bytes")
            elif isinstance(data, dict):
                print(f"  Keys: {list(data.keys())}")
        return elapsed
    except Exception as e:
        t1 = time.time()
        print(f"  ERROR after {t1-t0:.2f}s: {e}")
        return t1 - t0

# 1. Health (baseline latency)
profile_endpoint("Health (baseline)", f"{BASE}/health")

# 2. GET /campaigns (the main list endpoint - THIS is what the page loads)
profile_endpoint("GET /campaigns (list all)", f"{BASE}/campaigns")

# 3. GET /campaigns/108 (single campaign with all nested data)
profile_endpoint("GET /campaigns/108 (detail)", f"{BASE}/campaigns/108")

# 4. GET /campaigns/107 (another one)
profile_endpoint("GET /campaigns/107 (detail)", f"{BASE}/campaigns/107")

# 5. Signatures list
profile_endpoint("GET /campaigns/signatures/list", f"{BASE}/campaigns/signatures/list")

# 6. Recruiters (for recipient selection)
profile_endpoint("GET /recruiters?limit=10", f"{BASE}/recruiters?limit=10")

print("\n=== PROFILING COMPLETE ===")
