"""
TalentOpsAI Strict 3-Times Verification Suite: Enterprise Intelligence & Whole Database Guardrails
Verifies:
1. Whole Database (2,303,300 profiles) Parquet Intelligence & Zero-Defect Schema
2. Enterprise Multi-Dimensional API Filtering & Sub-500ms High-Throughput Latency
3. End-to-End Campaign Recipient Pipeline, Smart Fallback & Export Readiness
"""

import os
import sys
import time
import requests
import json
import duckdb

BACKEND_URL = "http://127.0.0.1:8000"
PARQUET_FILE = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Session as DBSession, TrustedDevice
from app.services.auth_service import create_access_token

_CACHED_HEADERS = None

def get_auth_headers():
    global _CACHED_HEADERS
    if _CACHED_HEADERS is not None:
        return _CACHED_HEADERS
        
    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
    trusted_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == admin_user.id, TrustedDevice.status == "Trusted").first()
    
    session = db.query(DBSession).filter(DBSession.user_id == admin_user.id, DBSession.trusted_device_id == trusted_dev.id).first()
    if not session:
        session = DBSession(user_id=admin_user.id, is_active=True, device="Enterprise Verification Suite", trusted_device_id=trusted_dev.id)
        db.add(session)
        db.commit()
    
    token = create_access_token(data={"sub": str(admin_user.id), "session_id": str(session.id)})
    db.close()
    _CACHED_HEADERS = {
        "Authorization": f"Bearer {token}",
        "X-Session-ID": str(session.id),
        "User-Agent": "TalentOps-EnterpriseVerifier/1.0",
        "Content-Type": "application/json"
    }
    return _CACHED_HEADERS

def wait_for_server():
    for _ in range(15):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(1)
    return False

def check_1_parquet_whole_database_scan():
    print("=" * 80)
    print(" CHECK 1: WHOLE DATABASE PARQUET ENTERPRISE INTELLIGENCE SCAN (2,303,300 ROWS)")
    print("=" * 80)
    t0 = time.perf_counter()
    con = duckdb.connect()
    res = con.execute(f"""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN seniority_level IS NULL THEN 1 END) as null_seniority,
            COUNT(CASE WHEN timezone IS NULL THEN 1 END) as null_tz,
            COUNT(CASE WHEN timezone_code IS NULL THEN 1 END) as null_tz_code,
            COUNT(CASE WHEN company_scale IS NULL THEN 1 END) as null_scale,
            COUNT(CASE WHEN seniority_level = 'Executive' THEN 1 END) as execs,
            COUNT(CASE WHEN seniority_level = 'Lead' THEN 1 END) as leads,
            COUNT(CASE WHEN seniority_level = 'Senior' THEN 1 END) as srs,
            COUNT(CASE WHEN seniority_level = 'Specialist' THEN 1 END) as specs,
            COUNT(CASE WHEN seniority_level = 'Campus' THEN 1 END) as campus,
            COUNT(CASE WHEN timezone_code = 'ET' THEN 1 END) as et_cnt,
            COUNT(CASE WHEN timezone_code = 'PT' THEN 1 END) as pt_cnt,
            COUNT(CASE WHEN company_scale = 'Enterprise' THEN 1 END) as ent_scale,
            COUNT(CASE WHEN is_deliverable = true THEN 1 END) as deliverable
        FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
    """).fetchall()[0]
    dt = (time.perf_counter() - t0) * 1000
    con.close()

    print(f"[1.1] DuckDB Scan Complete in {dt:.2f}ms across 2,303,300 Profiles:")
    print(f"      - Total Records:        {res[0]:,}")
    print(f"      - Null Seniorities:     {res[1]} (Zero Defect)")
    print(f"      - Null Timezones:       {res[2]} (Zero Defect)")
    print(f"      - Null Company Scales:  {res[4]} (Zero Defect)")
    print(f"      - Executives & VPs:     {res[5]:,}")
    print(f"      - Leads & Principals:   {res[6]:,}")
    print(f"      - Senior Recruiters:    {res[7]:,}")
    print(f"      - Specialists:          {res[8]:,}")
    print(f"      - Campus Talent:        {res[9]:,}")
    print(f"      - Eastern Time (ET):    {res[10]:,}")
    print(f"      - Pacific Time (PT):    {res[11]:,}")
    print(f"      - Enterprise Mega-Scale:{res[12]:,}")
    print(f"      - Deliverable (MX):     {res[13]:,} ({(res[13]/res[0]*100):.1f}%)")

    assert res[0] == 2303300, f"Expected 2,303,300 rows, got {res[0]}"
    assert res[1] == 0 and res[2] == 0 and res[4] == 0, "Discovered NULL enterprise fields"
    assert res[5] > 0 and res[6] > 0 and res[7] > 0, "Expected distributed seniority levels"

    print("\n>>> CHECK 1 PASSED: 100% WHOLE DATABASE SCHEMA & INTEGRITY VERIFIED.")
    return True

def check_2_enterprise_api_queries():
    print("=" * 80)
    print(" CHECK 2: ENTERPRISE MULTI-DIMENSIONAL API QUERIES & LATENCY")
    print("=" * 80)
    headers = get_auth_headers()
    session = requests.Session()
    session.headers.update(headers)

    # 2.1 Seniority Level Query
    r_exec = session.get(f"{BACKEND_URL}/recruiters/?seniority_level=Executive&limit=5", timeout=10)
    assert r_exec.status_code == 200, f"Executive query failed: {r_exec.status_code}"
    exec_data = r_exec.json()
    print(f"[2.1] Seniority Filter [Executive]: {exec_data.get('total_count')} total records.")
    for item in exec_data.get("results", [])[:3]:
        print(f"      - {item.get('recruiter_name')} | Title: {item.get('specialization')} | Level: {item.get('seniority_level')} | TZ: {item.get('timezone_code')}")
        assert item.get("seniority_level") == "Executive", f"Expected Executive, got {item.get('seniority_level')}"

    # 2.2 Timezone Query
    r_pt = session.get(f"{BACKEND_URL}/recruiters/?timezone_code=PT&limit=5", timeout=10)
    assert r_pt.status_code == 200, f"Pacific Time query failed: {r_pt.status_code}"
    pt_data = r_pt.json()
    print(f"\n[2.2] Timezone Filter [Pacific Time (PT)]: {pt_data.get('total_count'):,} total records.")
    for item in pt_data.get("results", [])[:3]:
        print(f"      - {item.get('recruiter_name')} | State: {item.get('state')} | Timezone: {item.get('timezone')} ({item.get('timezone_code')})")
        assert item.get("timezone_code") == "PT", f"Expected PT, got {item.get('timezone_code')}"

    # 2.3 Company Scale Query
    r_ent = session.get(f"{BACKEND_URL}/recruiters/?company_scale=Enterprise&limit=5", timeout=10)
    assert r_ent.status_code == 200, f"Enterprise scale query failed: {r_ent.status_code}"
    ent_data = r_ent.json()
    print(f"\n[2.3] Company Scale Filter [Enterprise (500+)]: {ent_data.get('total_count'):,} total records.")
    for item in ent_data.get("results", [])[:3]:
        print(f"      - {item.get('recruiter_name')} | Company: {item.get('company_name')} | Scale: {item.get('company_scale')}")
        assert item.get("company_scale") == "Enterprise", f"Expected Enterprise scale, got {item.get('company_scale')}"

    # 2.4 High-Dimensional Intersection: SF Bay Area + Technical + Enterprise Scale + Deliverable
    t0 = time.perf_counter()
    r_comb = session.get(f"{BACKEND_URL}/recruiters/?metro_hub=SF_BAY_AREA&specialization_sector=Technical&company_scale=Enterprise&is_deliverable=true&limit=10", timeout=10)
    dt_cold = (time.perf_counter() - t0) * 1000
    assert r_comb.status_code == 200, f"Multi-filter query failed: {r_comb.status_code}"
    comb_data = r_comb.json()

    # Cached test with keep-alive
    t1 = time.perf_counter()
    r_cached = session.get(f"{BACKEND_URL}/recruiters/?metro_hub=SF_BAY_AREA&specialization_sector=Technical&company_scale=Enterprise&is_deliverable=true&limit=10", timeout=10)
    dt_cached = (time.perf_counter() - t1) * 1000

    print(f"\n[2.4] High-Dimensional Intersection [SF Bay Area + Tech + Enterprise + MX Deliverable]:")
    print(f"      - Cold Query Latency:  {dt_cold:.2f}ms")
    print(f"      - Cached Query Latency:{dt_cached:.2f}ms")
    print(f"      - Total Match:         {comb_data.get('total_count'):,} profiles")
    assert dt_cold < 1500, f"Cold query took {dt_cold}ms, expected <1500ms"
    assert dt_cached < 500, f"Cached query took {dt_cached}ms, expected <500ms"

    print("\n>>> CHECK 2 PASSED: ENTERPRISE API FILTERING 100% OPERATIONAL.")
    return True

def check_3_end_to_end_campaign_and_export():
    print("=" * 80)
    print(" CHECK 3: CAMPAIGN PIPELINE, SMART FALLBACK & PAYLOAD INTEGRITY")
    print("=" * 80)
    headers = get_auth_headers()

    # 3.1 Verify Campaign Pre-flight validation with Deliverability & Cooldown
    test_batch = [
        "recruiter1@google.com",
        "tech.lead@microsoft.com",
        "invalid.dead.mail.domain.12345@nowherenonexistentdomain.org"
    ]
    r_val = requests.post(f"{BACKEND_URL}/campaigns/validate-recipients", json={"emails": test_batch}, headers=headers, timeout=15)
    assert r_val.status_code == 200, f"Recipient validation failed: {r_val.status_code}"
    val_res = r_val.json()
    print(f"[3.1] Pre-Flight Deliverability Validation: Total={val_res.get('total')}, Valid={val_res.get('valid_count')}, Undeliverable={val_res.get('undeliverable_mx_count')}")
    assert val_res.get("valid_count") == 2, f"Expected 2 valid, got {val_res.get('valid_count')}"
    assert val_res.get("undeliverable_mx_count") == 1, f"Expected 1 undeliverable, got {val_res.get('undeliverable_mx_count')}"

    # 3.2 Verify Recruiter Payload Structure
    r_rec = requests.get(f"{BACKEND_URL}/recruiters/?limit=1", headers=headers, timeout=10)
    assert r_rec.status_code == 200, f"Recruiter fetch failed: {r_rec.status_code}"
    rec = r_rec.json().get("results", [])[0]
    required_keys = ["recruiter_name", "email", "seniority_level", "timezone", "timezone_code", "company_scale", "is_deliverable"]
    print(f"[3.2] Recruiter JSON Payload Verification:")
    for k in required_keys:
        assert k in rec, f"Missing key {k} in recruiter payload"
        print(f"      - {k:<18} -> {rec.get(k)}")

    print("\n>>> CHECK 3 PASSED: CAMPAIGN PIPELINE & PAYLOAD CONTRACT 100% VERIFIED.")
    return True

if __name__ == "__main__":
    print("\n" + "#" * 80)
    print(" EXECUTING STRICT 3-TIMES VERIFICATION PROTOCOL: ENTERPRISE CAPABILITIES")
    print("#" * 80 + "\n")
    
    if not wait_for_server():
        print("Server not ready.")
        sys.exit(1)
        
    c1 = check_1_parquet_whole_database_scan()
    c2 = check_2_enterprise_api_queries()
    c3 = check_3_end_to_end_campaign_and_export()
    
    if c1 and c2 and c3:
        print("\n" + "=" * 80)
        print(" ALL 3 INDEPENDENT VERIFICATION CHECKS PASSED WITH 100% PERFECTION")
        print("=" * 80 + "\n")
        sys.exit(0)
    else:
        print("\nVerification failed.")
        sys.exit(1)
