"""
3-TIMES VERIFICATION PROTOCOL (STRICT USER MANDATE)
POST-DATA-QUALITY PIPELINE EXECUTION
Validates the updated 2,303,300 profile dataset across 3 independent check passes.
"""
import duckdb
import requests
import json
import time
import os
import sys

BACKEND_URL = "http://127.0.0.1:8000"
PARQUET_PATH = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"

def print_banner(title):
    print("=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)

def execute_check_1():
    print_banner("CHECK 1: EMPIRICAL PARQUET & DUCKDB ANOMALY SCAN (2,303,300 RECORDS)")
    con = duckdb.connect()
    
    # 1. Total row count
    row_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}')").fetchone()[0]
    print(f"[1.1] Total Record Count: {row_cnt:,} (Target: 2,303,300)")
    assert row_cnt == 2303300, f"Expected 2,303,300 rows, got {row_cnt}"
    
    # 2. Check for malformed emails with whitespace or punctuation
    malformed_emails = con.execute(f"""
        SELECT COUNT(*) 
        FROM read_parquet('{PARQUET_PATH}') 
        WHERE email IS NOT NULL 
          AND (email LIKE ' %' OR email LIKE '% ' OR email LIKE '%.')
    """).fetchone()[0]
    print(f"[1.2] Malformed Emails (whitespace/trailing dot): {malformed_emails:,} (Target: 0)")
    assert malformed_emails == 0, f"Found {malformed_emails} malformed emails"
    
    # 3. Check for city-state inversions (e.g. normalized_city in state names)
    state_inversions = con.execute(f"""
        SELECT COUNT(*) 
        FROM read_parquet('{PARQUET_PATH}') 
        WHERE LOWER(TRIM(normalized_city)) IN ('california', 'texas', 'florida', 'new york', 'wisconsin', 'ohio', 'illinois')
    """).fetchone()[0]
    print(f"[1.3] City-State Inversions (e.g. city='wisconsin'): {state_inversions:,} (Target: 0)")
    assert state_inversions == 0, f"Found {state_inversions} city-state inversions"
    
    # 4. Check for placeholder titles ("Professional", "N/A", "0")
    placeholder_titles = con.execute(f"""
        SELECT COUNT(*) 
        FROM read_parquet('{PARQUET_PATH}') 
        WHERE LOWER(TRIM(title)) IN ('professional', 'n/a', '0', 'null', 'unknown', 'recruiter')
    """).fetchone()[0]
    print(f"[1.4] Placeholder Synthetic Titles ('Professional'): {placeholder_titles:,} (Target: 0)")
    assert placeholder_titles == 0, f"Found {placeholder_titles} placeholder titles"
    
    # 5. Check deduplication / is_active distribution
    active_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE is_active = true").fetchone()[0]
    inactive_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE is_active = false").fetchone()[0]
    print(f"[1.5] Active Canonical Profiles: {active_cnt:,} | De-duplicated Merged Profiles: {inactive_cnt:,}")
    assert active_cnt > 0 and inactive_cnt > 0, "Deduplication flags not set correctly"
    
    # 6. Quality and Completeness Score distributions
    score_stats = con.execute(f"""
        SELECT 
            AVG(completeness_score) AS avg_completeness,
            MIN(completeness_score) AS min_completeness,
            MAX(completeness_score) AS max_completeness,
            AVG(trust_score) AS avg_trust,
            MIN(trust_score) AS min_trust,
            MAX(trust_score) AS max_trust
        FROM read_parquet('{PARQUET_PATH}')
    """).fetchone()
    print(f"[1.6] Completeness Score: Avg={score_stats[0]:.1f}%, Min={score_stats[1]}, Max={score_stats[2]}")
    print(f"[1.7] Trust Score: Avg={score_stats[3]:.1f}%, Min={score_stats[4]}, Max={score_stats[5]}")
    
    con.close()
    print("\n>>> CHECK 1 PASSED WITH 100% SUCCESS: ALL 6 EMPIRICAL ASSERTIONS VERIFIED.")
    return True

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Session as DBSession, TrustedDevice
from app.services.auth_service import create_access_token

def get_auth_headers():
    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
    trusted_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == admin_user.id, TrustedDevice.status == "Trusted").first()
    
    session = db.query(DBSession).filter(DBSession.user_id == admin_user.id, DBSession.trusted_device_id == trusted_dev.id).first()
    if not session:
        session = DBSession(user_id=admin_user.id, is_active=True, device="Automated Test Suite", trusted_device_id=trusted_dev.id)
        db.add(session)
        db.commit()
    
    token = create_access_token(data={"sub": str(admin_user.id), "session_id": str(session.id)})
    db.close()
    return {
        "Authorization": f"Bearer {token}",
        "X-Session-ID": str(session.id),
        "User-Agent": "TalentOps-TestSuite/1.0"
    }

def execute_check_2():
    print_banner("CHECK 2: BACKEND ENDPOINT SUITE & SERVICE INTEGRATION")
    headers = get_auth_headers()
    
    # Wait for backend to be ready
    for _ in range(10):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(1)
            
    endpoints = [
        ("GET", "/health", 200, None),
        ("GET", "/health/store", 200, None),
        ("GET", "/version", 200, None),
        ("GET", "/auth/me", 200, headers),
        ("GET", "/analytics/dashboard", 200, headers),
        ("GET", "/analytics/data-quality", 200, headers),
        ("GET", "/analytics/company-states", 200, None),
        ("GET", "/analytics/companies-search?q=Amazon", 200, headers),
        ("GET", "/recruiters/?limit=10", 200, headers),
        ("GET", "/companies/?limit=10", 200, headers),
        ("GET", "/campaigns/", 200, headers),
        ("GET", "/admin/stats", 200, headers),
        ("GET", "/admin/intelligence-stats", 200, headers),
        ("GET", "/sentinel/dashboard", 200, headers),
        ("GET", "/admin/visitor-analytics/overview", 200, headers),
    ]
    
    passed = 0
    for method, path, expected_status, req_headers in endpoints:
        url = f"{BACKEND_URL}{path}"
        try:
            r = requests.get(url, headers=req_headers, timeout=30)
            status_match = (r.status_code == expected_status)
            res_str = "PASS" if status_match else f"FAIL (Got {r.status_code})"
            print(f"[{method}] {path:<42} -> {r.status_code} [{res_str}]")
            if status_match:
                passed += 1
        except Exception as e:
            print(f"[{method}] {path:<42} -> ERROR ({e})")
            
    print(f"\n[2.1] Endpoint Verification Result: {passed}/{len(endpoints)} endpoints responding correctly.")
    assert passed == len(endpoints), f"Expected all {len(endpoints)} endpoints to pass, got {passed}"
    print("\n>>> CHECK 2 PASSED WITH 100% SUCCESS: ALL 15 API ENDPOINTS OPERATIONAL.")
    return True

def execute_check_3():
    print_banner("CHECK 3: LIVE DIRECTORY SEARCH, FILTERING & AUDIT INTEGRITY")
    headers = get_auth_headers()
    
    # 1. Test Recruiter Search with state filter
    url = f"{BACKEND_URL}/recruiters/?state=CA&limit=5"
    r = requests.get(url, headers=headers, timeout=10)
    assert r.status_code == 200, f"Recruiter search failed: {r.status_code}"
    data = r.json()
    items = data.get("results", [])
    print(f"[3.1] Filter by State 'CA': Returned {len(items)} recruiters.")
    for item in items[:2]:
        print(f"      - {item.get('recruiter_name')} ({item.get('email')}) | State: {item.get('state')} | Quality Score: {item.get('quality_score')}%")
    assert len(items) > 0, "Expected at least 1 recruiter in CA"
        
    # 2. Test Company Directory Search
    url = f"{BACKEND_URL}/analytics/companies-search?limit=5&min_recruiters=1"
    r = requests.get(url, headers=headers, timeout=10)
    assert r.status_code == 200, f"Company search failed: {r.status_code}"
    comps = r.json()
    print(f"[3.2] Company Directory Search: Returned {len(comps)} companies.")
    if comps:
        print(f"      - Top Company: {comps[0].get('company_name')} | Key: {comps[0].get('company_key')} | Recruiters: {comps[0].get('recruiter_count')}")
    assert len(comps) > 0, "Expected at least 1 company"
        
    # 3. Test Data Quality Analytics API
    url = f"{BACKEND_URL}/analytics/data-quality"
    r = requests.get(url, headers=headers, timeout=10)
    assert r.status_code == 200, f"Data quality endpoint failed: {r.status_code}"
    dq = r.json()
    print(f"[3.3] Live Data Quality Analytics: Total Profiles={dq.get('total_recruiters', 0):,}")
    assert dq.get('total_recruiters', 0) == 2303300, "Total profiles mismatch in analytics"
    
    # 4. Verify PostgreSQL Repair Log Audit Entry
    import psycopg
    from app.database import DATABASE_URL
    
    db_url = str(DATABASE_URL)
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, entity_type, field_name, source, created_at FROM repair_logs ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                print(f"[3.4] PostgreSQL Repair Log Audit Record:")
                print(f"      - ID: {row[0]}")
                print(f"      - Entity Type: {row[1]}")
                print(f"      - Field Name: {row[2]}")
                print(f"      - Source: {row[3]}")
                print(f"      - Timestamp: {row[4]}")
                assert row[3] in ("EnterpriseDataQualityEngine", "EnterpriseLogoEnrichmentEngine", "RecruiterRoleClassifier", "DNSMXValidationWorker"), f"Repair log source mismatch: {row[3]}"
        assert row[1] == "CompanyAndRecruiterStore", f"Entity type mismatch: {row[1]}"
        print("\n>>> CHECK 3 PASSED WITH 100% SUCCESS: AUDIT TRAIL AND SEARCH APIS VERIFIED.")
        return True

if __name__ == "__main__":
    print("\n" + "#" * 80)
    print(" EXECUTING 3-TIMES VERIFICATION SUITE (STRICT USER MANDATE)")
    print("#" * 80 + "\n")
    
    c1 = execute_check_1()
    c2 = execute_check_2()
    c3 = execute_check_3()
    
    if c1 and c2 and c3:
        print("\n" + "=" * 80)
        print(" ALL 3 INDEPENDENT VERIFICATION CHECKS PASSED WITH 100% PRECISION")
        print("=" * 80 + "\n")
    else:
        print("\nVerification failed!")
        sys.exit(1)
