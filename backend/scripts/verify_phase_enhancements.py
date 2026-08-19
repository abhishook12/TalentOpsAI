import sys
import os
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://127.0.0.1:8000"

def log_header(title):
    print("\n" + "=" * 70)
    print(f"  3 PASS VERIFICATION: {title}")
    print("=" * 70)

def get_auth_token():
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@talentops.ai", "password": "Admin@12345"}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get("token") or data.get("access_token")
        else:
            print(f"Login failed: {res.status_code} {res.text}")
            return None
    except Exception as e:
        print(f"Auth exception: {e}")
        return None

def pass_1_api_integration():
    log_header("PASS 1 - API Functional & Integration Verification")
    token = get_auth_token()
    if not token:
        print("[FAIL] Could not obtain auth token.")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    results = []

    # 1. Recruiters List
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/recruiters/?limit=5", headers=headers, timeout=10)
    dt = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Recruiters list failed: {r.status_code}"
    data = r.json()
    count = data.get("total", len(data.get("results", [])))
    print(f"[PASS] 1. GET /recruiters/?limit=5 -> {r.status_code} OK (Latency: {dt:.1f}ms, Total: {count})")
    results.append(True)

    # 2. Recruiters Search
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/recruiters/search?q=Global", headers=headers, timeout=10)
    dt = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Recruiters search failed: {r.status_code}"
    search_data = r.json()
    items = search_data.get('results', search_data) if isinstance(search_data, dict) else search_data
    print(f"[PASS] 2. GET /recruiters/search?q=Global -> {r.status_code} OK (Latency: {dt:.1f}ms, Found: {len(items)})")
    results.append(True)

    # 3. Companies List
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/companies/?limit=5", headers=headers, timeout=10)
    dt = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Companies list failed: {r.status_code}"
    print(f"[PASS] 3. GET /companies/?limit=5 -> {r.status_code} OK (Latency: {dt:.1f}ms)")
    results.append(True)

    # 4. Analytics Dashboard
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/analytics/dashboard", headers=headers, timeout=10)
    dt = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Analytics dashboard failed: {r.status_code}"
    print(f"[PASS] 4. GET /analytics/dashboard -> {r.status_code} OK (Latency: {dt:.1f}ms)")
    results.append(True)

    # 5. AI Multi-Touch Sequence Generator
    t0 = time.time()
    seq_payload = {
        "role_title": "Senior Cloud Solutions Architect",
        "target_audience": "Enterprise Technical Recruiters & TA Leaders",
        "num_touches": 3,
        "campaign_goal": "cold_outreach",
        "value_proposition": "We provide pre-vetted top 1% AWS & Azure certified engineers with immediate availability.",
        "call_to_action": "15-minute intro call this Thursday"
    }
    r = requests.post(f"{BASE_URL}/campaigns/generate-sequence", json=seq_payload, headers=headers, timeout=15)
    dt = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Sequence generator failed: {r.status_code} {r.text}"
    seq_data = r.json()
    touches = seq_data.get("touches", [])
    assert len(touches) == 3, f"Expected 3 touches, got {len(touches)}"
    print(f"[PASS] 5. POST /campaigns/generate-sequence -> {r.status_code} OK ({len(touches)} touches generated, Latency: {dt:.1f}ms)")
    results.append(True)

    # 6. Domain Health & Deliverability Inspector
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/domain-health/check?domain=talentops.ai", headers=headers, timeout=15)
    dt = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Domain health check failed: {r.status_code} {r.text}"
    dh_data = r.json()
    assert "health_score" in dh_data, "Missing health_score in response"
    assert "spf" in dh_data and "dmarc" in dh_data, "Missing SPF/DMARC in response"
    print(f"[PASS] 6. GET /domain-health/check?domain=talentops.ai -> {r.status_code} OK (Score: {dh_data.get('health_score')}/100, Status: {dh_data.get('status')}, SPF: {dh_data['spf']['status']}, Latency: {dt:.1f}ms)")
    results.append(True)

    # 7. Talent Pool CRUD & Membership Lifecycle
    t0 = time.time()
    # 7a. Create Pool
    pool_payload = {
        "name": "Forensic Test Pool 2026",
        "description": "Automated verification talent pool",
        "tags": ["cloud", "urgent", "qa"]
    }
    r = requests.post(f"{BASE_URL}/talent-pools", json=pool_payload, headers=headers, timeout=10)
    assert r.status_code == 200, f"Create pool failed: {r.status_code} {r.text}"
    pool_data = r.json()
    pool_id = pool_data["id"]
    print(f"[PASS] 7a. POST /talent-pools -> {r.status_code} OK (Created Pool ID: {pool_id})")

    # 7b. Add Recruiters
    r = requests.post(f"{BASE_URL}/talent-pools/{pool_id}/add-recruiters", json={"recruiter_ids": [1, 2, 3]}, headers=headers, timeout=10)
    assert r.status_code == 200, f"Add members failed: {r.status_code} {r.text}"
    print(f"[PASS] 7b. POST /talent-pools/{pool_id}/add-recruiters -> {r.status_code} OK (Added 3 recruiters)")

    # 7c. Get Pool Details
    r = requests.get(f"{BASE_URL}/talent-pools/{pool_id}", headers=headers, timeout=10)
    assert r.status_code == 200, f"Get pool details failed: {r.status_code} {r.text}"
    details_data = r.json()
    assert details_data["total_members"] == 3, f"Expected 3 members, got {details_data['total_members']}"
    print(f"[PASS] 7c. GET /talent-pools/{pool_id} -> {r.status_code} OK (Members found: {details_data['total_members']})")

    # 7d. List Pools
    r = requests.get(f"{BASE_URL}/talent-pools", headers=headers, timeout=10)
    assert r.status_code == 200, f"List pools failed: {r.status_code}"
    pools_list = r.json()
    print(f"[PASS] 7d. GET /talent-pools -> {r.status_code} OK (Total Pools: {len(pools_list)})")

    # 7e. Delete Pool
    r = requests.delete(f"{BASE_URL}/talent-pools/{pool_id}", headers=headers, timeout=10)
    assert r.status_code == 200, f"Delete pool failed: {r.status_code}"
    print(f"[PASS] 7e. DELETE /talent-pools/{pool_id} -> {r.status_code} OK (Cleaned up)")
    results.append(True)

    all_passed = all(results)
    verdict = "ALL PASSED" if all_passed else "FAILED"
    print(f"\n>>> PASS 1 VERDICT: {verdict} <<<")
    return all_passed

def pass_2_concurrency_and_stress():
    log_header("PASS 2 - DuckDB Thread-Safety & Concurrent Load Verification")
    token = get_auth_token()
    if not token:
        print("[FAIL] Could not obtain auth token.")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        f"{BASE_URL}/recruiters/?limit=10",
        f"{BASE_URL}/recruiters/search?q=engineer",
        f"{BASE_URL}/companies/?limit=10",
        f"{BASE_URL}/analytics/dashboard",
        f"{BASE_URL}/domain-health/check?domain=google.com",
        f"{BASE_URL}/talent-pools",
        f"{BASE_URL}/campaigns/",
        f"{BASE_URL}/recruiters/?limit=20&page=2",
        f"{BASE_URL}/recruiters/search?q=recruiter",
        f"{BASE_URL}/domain-health/check?domain=microsoft.com",
    ]

    def hit_endpoint(url):
        t0 = time.time()
        try:
            res = requests.get(url, headers=headers, timeout=15)
            dt = (time.time() - t0) * 1000
            return (res.status_code, dt, url.split(BASE_URL)[1])
        except Exception as e:
            return (500, (time.time() - t0) * 1000, str(e))

    print(f"Dispatching {len(endpoints)} parallel requests across thread pool...")
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(hit_endpoint, url) for url in endpoints]
        responses = [f.result() for f in futures]
    total_time = (time.time() - t_start) * 1000

    errors = 0
    for code, latency, ep in responses:
        status_tag = "[PASS]" if code == 200 else "[FAIL]"
        print(f"  {status_tag} {code} in {latency:6.1f}ms -> {ep}")
        if code != 200:
            errors += 1

    avg_lat = sum(r[1] for r in responses) / len(responses)
    print(f"\nConcurrent Stress Results:")
    print(f"  Total Wall Clock Time: {total_time:.1f}ms")
    print(f"  Average Request Latency: {avg_lat:.1f}ms")
    print(f"  Success Rate: {(len(responses) - errors) / len(responses) * 100:.1f}% ({len(responses) - errors}/{len(responses)})")
    
    passed = errors == 0
    verdict = "PASSED (0 THREAD CONTENTION ERRORS)" if passed else "FAILED"
    print(f"\n>>> PASS 2 VERDICT: {verdict} <<<")
    return passed

def pass_3_frontend_bundle_integrity():
    log_header("PASS 3 - Frontend Production Build & Asset Integrity Verification")
    dist_path = os.path.abspath("c:/TalentOpsAI/frontend/dist")
    
    assert os.path.exists(dist_path), f"Dist folder not found at {dist_path}"
    
    # 1. Check index.html
    index_file = os.path.join(dist_path, "index.html")
    assert os.path.exists(index_file), "index.html missing"
    with open(index_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    assert "<script" in html_content, "Script tag missing in index.html"
    print(f"[PASS] 1. index.html exists and valid ({os.path.getsize(index_file)} bytes)")

    # 2. Check assets folder
    assets_path = os.path.join(dist_path, "assets")
    assert os.path.exists(assets_path), "assets folder missing"
    files = os.listdir(assets_path)
    print(f"[PASS] 2. assets/ folder verified ({len(files)} compiled artifacts)")

    # 3. Check for critical component chunks
    required_chunks = ["Campaigns", "Search", "Directory", "Recruiters", "Analytics"]
    found_chunks = {}
    for chunk in required_chunks:
        matching = [f for f in files if f.startswith(chunk) and f.endswith(".js")]
        if matching:
            found_chunks[chunk] = matching[0]
            print(f"[PASS] 3. Core Page Chunk: {matching[0]} ({os.path.getsize(os.path.join(assets_path, matching[0])) / 1024:.1f} KB)")
        else:
            print(f"[FAIL] 3. Missing chunk for {chunk}")

    assert len(found_chunks) == len(required_chunks), "Not all required chunks found"

    # 4. Check for SaveToTalentPoolModal chunk
    pool_modal_chunks = [f for f in files if "SaveToTalentPoolModal" in f and f.endswith(".js")]
    assert len(pool_modal_chunks) > 0, "SaveToTalentPoolModal chunk missing"
    print(f"[PASS] 4. SaveToTalentPoolModal lazy chunk: {pool_modal_chunks[0]} ({os.path.getsize(os.path.join(assets_path, pool_modal_chunks[0])) / 1024:.1f} KB)")

    print(f"\n>>> PASS 3 VERDICT: ALL PRODUCTION ASSETS INTEGRITY VERIFIED <<<")
    return True

if __name__ == "__main__":
    p1 = pass_1_api_integration()
    p2 = pass_2_concurrency_and_stress()
    p3 = pass_3_frontend_bundle_integrity()

    print("\n" + "#" * 70)
    print("                FINAL 3-PASS AUDIT SUMMARY")
    print("#" * 70)
    print(f"  PASS 1: API Functional & Integration:       {'PASSED' if p1 else 'FAILED'}")
    print(f"  PASS 2: DuckDB Concurrency & Stress:        {'PASSED' if p2 else 'FAILED'}")
    print(f"  PASS 3: Frontend Asset & Bundle Integrity:  {'PASSED' if p3 else 'FAILED'}")
    print("#" * 70)

    if p1 and p2 and p3:
        print("\n>>> ALL 3 PASSES SUCCESSFUL - READY FOR USER PRESENTATION <<<\n")
        sys.exit(0)
    else:
        print("\n>>> ONE OR MORE PASSES FAILED <<<\n")
        sys.exit(1)
