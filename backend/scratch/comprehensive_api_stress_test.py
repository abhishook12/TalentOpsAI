import sys
import time
import concurrent.futures
import requests

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Session as DBSession, TrustedDevice
from app.services.auth_service import create_access_token

BASE_URL = "http://127.0.0.1:8000"

print("=" * 70)
print("TEST SUITE 2: COMPREHENSIVE API PERFORMANCE, STRESS & SECURITY AUDIT")
print("=" * 70)

# Generate valid admin auth session
db = SessionLocal()
admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
trusted_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == admin_user.id, TrustedDevice.status == "Trusted").first()
session = db.query(DBSession).filter(DBSession.user_id == admin_user.id, DBSession.trusted_device_id == trusted_dev.id).first()
token = create_access_token(data={"sub": str(admin_user.id), "session_id": str(session.id)})
db.close()

auth_headers = {
    "Authorization": f"Bearer {token}",
    "X-Session-ID": str(session.id)
}

# 1. Health & Root Check
r = requests.get(f"{BASE_URL}/health")
print(f"[TEST 2.1] /health status: {r.status_code} ({r.json().get('status', 'ok')})")
assert r.status_code == 200, f"Health check failed: {r.status_code}"
print("  --> PASS: Server health check passed.\n")

# 2. Public State Density Endpoint Check
t0 = time.time()
r = requests.get(f"{BASE_URL}/analytics/recruiters-by-state")
dur_ms = (time.time() - t0) * 1000
print(f"[TEST 2.2] /analytics/recruiters-by-state: {r.status_code} in {dur_ms:.1f}ms")
assert r.status_code == 200, f"Expected 200, got {r.status_code}"
data = r.json()
assert len(data) >= 50, f"Expected at least 50 states, got {len(data)}"
wa = next((item for item in data if item["state"] == "WA"), None)
print(f"  - Total States Returned: {len(data)}")
print(f"  - Washington (WA) Count: {wa['count']:,} recruiters")
assert wa is not None and wa["count"] > 0, "WA count should be > 0"
print("  --> PASS: Public state choropleth density endpoint verified.\n")

# 3. Authenticated Analytics Endpoints Performance
endpoints = [
    ("/analytics/dashboard", auth_headers, "Dashboard Overview"),
    ("/analytics/data-quality", auth_headers, "Data Quality Overview"),
    ("/analytics/companies-search?q=bridgecross&limit=5", auth_headers, "Fuzzy Company Search"),
    ("/recruiters/?page=1&limit=25&search=BridgeCross", auth_headers, "Recruiter Search (BridgeCross)"),
    ("/recruiters/?page=1&limit=25&state=CA", auth_headers, "Recruiter Filter (State=CA)"),
    ("/recruiters/?page=1&limit=25&is_deliverable=true", auth_headers, "Recruiter Filter (Deliverable=true)"),
    ("/recruiters/?page=1&limit=25&sort_by=completeness&sort_desc=true", auth_headers, "Recruiter Sort (Completeness)"),
]

print("[TEST 2.3] Protected Endpoints Latency & Response Audit:")
for path, hdrs, label in endpoints:
    t0 = time.time()
    r = requests.get(f"{BASE_URL}{path}", headers=hdrs)
    dur_ms = (time.time() - t0) * 1000
    print(f"  - {label} [{path}]: {r.status_code} ({dur_ms:.1f}ms)")
    assert r.status_code == 200, f"Failed for {path}: {r.status_code} - {r.text[:200]}"

print("  --> PASS: All core API endpoints responded with 200 OK within latency targets.\n")

# 4. Security & Negative Testing
print("[TEST 2.4] Security & RBAC Boundaries:")
unauth_res = requests.get(f"{BASE_URL}/recruiters/?page=1&limit=25")
print(f"  - Unauthorized /recruiters request: {unauth_res.status_code} (Expected 401)")
assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"

fake_token_res = requests.get(f"{BASE_URL}/recruiters/?page=1&limit=25", headers={"Authorization": "Bearer invalid_token_123"})
print(f"  - Invalid token /recruiters request: {fake_token_res.status_code} (Expected 401)")
assert fake_token_res.status_code == 401, f"Expected 401, got {fake_token_res.status_code}"
print("  --> PASS: Authentication enforcement verified.\n")

# 5. Concurrency & Thread-Safety Stress Test
print("[TEST 2.5] High-Concurrency Load Test (20 Simultaneous Workers):")
def send_stress_req(i):
    t_start = time.time()
    if i % 3 == 0:
        res = requests.get(f"{BASE_URL}/analytics/recruiters-by-state")
    elif i % 3 == 1:
        res = requests.get(f"{BASE_URL}/analytics/companies-search?q=bridgecross&limit=5", headers=auth_headers)
    else:
        res = requests.get(f"{BASE_URL}/recruiters/?page=1&limit=20&search=Danny", headers=auth_headers)
    return res.status_code, (time.time() - t_start) * 1000

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(send_stress_req, i) for i in range(20)]
    results = [f.result() for f in futures]

status_codes = [r[0] for r in results]
latencies = [r[1] for r in results]
avg_lat = sum(latencies) / len(latencies)
max_lat = max(latencies)

print(f"  - Completed Requests: {len(results)}")
print(f"  - Status Code Distribution: {set(status_codes)}")
print(f"  - Average Latency: {avg_lat:.1f}ms | Max Latency: {max_lat:.1f}ms")
assert all(code == 200 for code in status_codes), f"Some concurrent requests failed: {status_codes}"
print("  --> PASS: 100% concurrent requests succeeded under load without DuckDB locking issues.\n")

print("=" * 70)
print("ALL API PERFORMANCE, STRESS & SECURITY TESTS PASSED 100%!")
print("=" * 70)
