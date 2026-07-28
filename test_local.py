import requests
import json

BASE = "http://127.0.0.1:8000"

# Test 1: Admin login
print("=== Test 1: Admin Login ===")
resp = requests.post(f"{BASE}/auth/login", json={"email": "admin@talentops.com", "password": "1012"})
print(f"Status: {resp.status_code}")
data = resp.json()
if resp.status_code == 200:
    print(f"Login SUCCESS: user={data.get('user', {}).get('email')}, role={data.get('user', {}).get('role')}")
    token = data.get("token")
elif resp.status_code == 202:
    print(f"Pending approval: {data}")
else:
    print(f"FAILED: {data}")
    token = None

# Test 2: /auth/me with token
if token:
    print("\n=== Test 2: /auth/me ===")
    resp2 = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {resp2.status_code}")
    if resp2.status_code == 200:
        me = resp2.json()
        print(f"Me: {me.get('email')}, Role: {me.get('role')}")
    else:
        print(f"FAILED: {resp2.json()}")

# Test 3: /auth/google endpoint exists
print("\n=== Test 3: /auth/google endpoint exists ===")
resp3 = requests.post(f"{BASE}/auth/google", json={"credential": "test"})
print(f"Status: {resp3.status_code} (expected 500 or 401, NOT 404)")
print(f"Response: {resp3.json()}")

# Test 4: Dashboard metrics
if token:
    print("\n=== Test 4: Dashboard Metrics ===")
    resp4 = requests.get(f"{BASE}/admin/dashboard/metrics", headers={"Authorization": f"Bearer {token}"})
    print(f"Status: {resp4.status_code}")
    if resp4.status_code == 200:
        print("Dashboard metrics OK")
    else:
        print(f"FAILED: {resp4.text[:200]}")

print("\n=== ALL TESTS COMPLETE ===")
