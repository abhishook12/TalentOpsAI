import sys
import os

sys.path.insert(0, r"c:\TalentOpsAI\backend")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 60)
print("CHECK 1: BACKEND ETAG & 304 ZERO-EGRESS VERIFICATION")
print("=" * 60)

# Test 1: Public /ping endpoint
r1 = client.get("/ping")
assert r1.status_code == 200, f"Expected 200, got {r1.status_code}"
etag1 = r1.headers.get("etag")
cc1 = r1.headers.get("cache-control")
len1 = len(r1.content)

print(f"[TEST 1] Initial GET /ping:")
print(f"  - Status Code:   {r1.status_code} OK")
print(f"  - ETag:          {etag1}")
print(f"  - Cache-Control: {cc1}")
print(f"  - Body Payload:  {len1} bytes")
assert etag1 is not None, "ETag missing on /ping"
assert "s-maxage" in cc1, "s-maxage missing from Cache-Control"

# Test 1b: Conditional GET /ping
r1_cond = client.get("/ping", headers={"If-None-Match": etag1})
len1_cond = len(r1_cond.content)
print(f"[TEST 1b] Conditional GET /ping (with If-None-Match):")
print(f"  - Status Code:   {r1_cond.status_code} Not Modified")
print(f"  - Body Payload:  {len1_cond} bytes (0 bytes egress!)")
assert r1_cond.status_code == 304, f"Expected 304, got {r1_cond.status_code}"
assert len1_cond == 0, f"Expected 0 body bytes, got {len1_cond}"

# Test 2: Public /version endpoint
r2 = client.get("/version")
etag2 = r2.headers.get("etag")
cc2 = r2.headers.get("cache-control")
len2 = len(r2.content)
print(f"\n[TEST 2] Initial GET /version:")
print(f"  - Status Code:   {r2.status_code} OK")
print(f"  - ETag:          {etag2}")
print(f"  - Cache-Control: {cc2}")
print(f"  - Body Payload:  {len2} bytes")

r2_cond = client.get("/version", headers={"If-None-Match": etag2})
len2_cond = len(r2_cond.content)
print(f"[TEST 2b] Conditional GET /version (with If-None-Match):")
print(f"  - Status Code:   {r2_cond.status_code} Not Modified")
print(f"  - Body Payload:  {len2_cond} bytes (0 bytes egress!)")
assert r2_cond.status_code == 304
assert len2_cond == 0

# Test 3: CORS Headers Verification
r3 = client.get("/ping", headers={"Origin": "https://talent-ops-ai.vercel.app"})
cors_allow = r3.headers.get("access-control-allow-origin")
cors_expose = r3.headers.get("access-control-expose-headers")
print(f"\n[TEST 3] CORS & Exposure Headers:")
print(f"  - Allow-Origin:  {cors_allow}")
print(f"  - Expose-Headers:{cors_expose}")
assert cors_allow == "https://talent-ops-ai.vercel.app"
assert "ETag" in cors_expose
assert "Cache-Control" in cors_expose

print("\n" + "=" * 60)
print("PROOFS VERIFIED: Check 1 PASSED (ETag, 304 Zero-Egress, Edge Caching, CORS Expose)")
print("=" * 60)
