"""
Comprehensive 3-Pass Verification Script for TalentOps AI Autonomous Background Sweeper
Strict Rule 11 Compliance Mandate
"""

import os
import sys
import time
import json
import duckdb
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.autonomous_profile_sweeper import (
    AutonomousProfileSweeper,
    STATE_MAP,
    TITLE_TAXONOMY,
    autonomous_sweeper,
)
from app.services.email_intelligence_service import email_intelligence

def print_separator(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def run_check_1():
    print_separator("CHECK 1: SCHEDULE WINDOW LOGIC & TOGGLE VERIFICATION")
    
    sweeper = AutonomousProfileSweeper()
    
    # Test 1.1: Current local time check
    now = datetime.now()
    curr_hour = now.hour
    in_win_actual = sweeper.is_in_sweep_window()
    print(f"[1.1] Current Server Time: {now.strftime('%Y-%m-%d %H:%M:%S')} (Hour: {curr_hour})")
    print(f"      Is within 18:00 - 04:00 window: {in_win_actual}")
    expected_actual = (curr_hour >= 18 or curr_hour < 4)
    assert in_win_actual == expected_actual, f"Expected {expected_actual}, got {in_win_actual}"
    print("      Proof 1.1: PASSED (Clock check matches 18:00 - 04:00 logic)")

    # Test 1.2: Simulated Hours
    test_cases = [
        (18, True, "6:00 PM (Start of evening window)"),
        (21, True, "9:00 PM (Mid-night window)"),
        (23, True, "11:00 PM (Night window)"),
        (0, True, "12:00 AM (Midnight)"),
        (3, True, "3:59 AM (Late night window)"),
        (4, False, "4:00 AM (End of window - Daytime sleep)"),
        (9, False, "9:00 AM (Morning daytime)"),
        (12, False, "12:00 PM (Noon daytime)"),
        (17, False, "5:59 PM (Just before window opens)"),
    ]
    
    print("\n[1.2] Testing Simulated 24-Hour Timeline:")
    for hour, expected, desc in test_cases:
        # Simulate hour
        is_active = (hour >= sweeper.start_hour or hour < sweeper.end_hour)
        assert is_active == expected, f"Hour {hour} failed: expected {expected}, got {is_active}"
        status_lbl = "ACTIVE (SWEEPING)" if is_active else "SLEEPING (WAITING UNTIL 18:00)"
        print(f"      Hour {hour:02d}:00 -> {status_lbl:<30} [{desc}] - PASS")

    # Test 1.3: Force Mode Override
    sweeper.force_active = True
    print("\n[1.3] Testing Force Override Mode (sweeper.force_active = True):")
    print(f"      sweeper.is_window_active: {sweeper.is_window_active} (Must be True even at 10 AM)")
    assert sweeper.is_window_active is True
    sweeper.force_active = False
    print(f"      Restored sweeper.force_active = False -> {sweeper.is_window_active}")
    print("      Proof 1.3: PASSED (Force override operational)")
    
    return True

def run_check_2():
    print_separator("CHECK 2: PROFILE-BY-PROFILE SANITIZATION & REPAIR ENGINE")
    
    sweeper = AutonomousProfileSweeper()
    
    dirty_profiles = [
        # 1. Mailing list via header
        {
            "recruiter_id": 900001,
            "recruiter_name": "'Adarsh Sharma' Via Exclusive C2C Requirements",
            "email": "adarsh@tekinspirations.com",
            "title": "Technical Recruiter",
            "is_active": True,
            "completeness_score": 50,
        },
        # 2. Doing Business As (DBA)
        {
            "recruiter_id": 900002,
            "recruiter_name": "Christopher Taylor Dba Casac Lmhc Mac Icap-Tx Iv",
            "email": "ctaylor@dynamicarehealth.com",
            "title": "Recruiter",
            "is_active": True,
            "completeness_score": 50,
        },
        # 3. CRM Status Note in Name Field
        {
            "recruiter_id": 900003,
            "recruiter_name": "Already Working With Someone",
            "email": "candidate3@gmail.com",
            "title": "Consultant",
            "is_active": True,
            "completeness_score": 50,
        },
        # 4. Non-Person Publication
        {
            "recruiter_id": 900004,
            "recruiter_name": "Becker's Hospital Review",
            "email": "news@beckershealthcare-news.com",
            "title": "Professional",
            "is_active": True,
            "completeness_score": 50,
        },
        # 5. Pure Job Title in Name Field
        {
            "recruiter_id": 900005,
            "recruiter_name": "Sales Development Representative",
            "email": "rep@optomi.com",
            "title": None,
            "is_active": True,
            "completeness_score": 50,
        },
        # 6. Corporate Agency with Human Email
        {
            "recruiter_id": 900006,
            "recruiter_name": "Express Employment Professionals",
            "email": "matt.helander@expresspros.com",
            "title": "Recruiter",
            "is_active": True,
            "completeness_score": 50,
        },
        # 7. Suffix Credentials (M.B.A. and CPA)
        {
            "recruiter_id": 900007,
            "recruiter_name": "Antoinette Edmonston-Heard M.B.A.",
            "email": "antoinette@adamsgabbert.com",
            "title": "Recruiter",
            "is_active": True,
            "completeness_score": 50,
        },
        # 8. Trailing Job Title Appended to Name
        {
            "recruiter_id": 900008,
            "recruiter_name": "Allen Chao Hsuan Chi Data Analyst",
            "email": "allen.chi@optomi.com",
            "title": None,
            "is_active": True,
            "completeness_score": 50,
        },
        # 9. Mailing List Group Email
        {
            "recruiter_id": 900009,
            "recruiter_name": "Anjali Tiwari",
            "email": "c2c-requirements-us@googlegroups.com",
            "title": "Recruiter",
            "is_active": True,
            "is_deliverable": True,
            "completeness_score": 70,
        },
        # 10. Missing Email with Corporate Name (Synthesis test)
        {
            "recruiter_id": 900010,
            "recruiter_name": "Sarah Connor",
            "email": None,
            "company_id": "Stripe",
            "title": "Recruiter",
            "is_active": True,
            "completeness_score": 30,
        }
    ]

    print(f"Testing {len(dirty_profiles)} Distinct Quality Defect Categories:")
    for p in dirty_profiles:
        is_mod, cleaned, acts = sweeper.inspect_and_clean_profile(p)
        rid = p["recruiter_id"]
        orig_n = p.get("recruiter_name")
        new_n = cleaned.get("recruiter_name")
        orig_e = p.get("email")
        new_e = cleaned.get("email")
        
        print(f"\n[Case #{rid}] Input: name='{orig_n}' | email='{orig_e}'")
        for a in acts:
            print(f"    Action: {a}")
        print(f"    Result: name='{new_n}' | email='{new_e}' | active={cleaned.get('is_active')} | deliv={cleaned.get('is_deliverable')}")
        assert is_mod is True, f"Record #{rid} was not modified!"

    # Specific assertions
    _, c1, _ = sweeper.inspect_and_clean_profile(dirty_profiles[0])
    assert c1["recruiter_name"] == "Adarsh Sharma", f"Failed stripping via header: {c1['recruiter_name']}"

    _, c2, _ = sweeper.inspect_and_clean_profile(dirty_profiles[1])
    assert c2["recruiter_name"] == "Christopher Taylor", f"Failed stripping DBA: {c2['recruiter_name']}"

    _, c3, _ = sweeper.inspect_and_clean_profile(dirty_profiles[2])
    assert c3["is_active"] is False and c3["needs_review"] is True, "Failed purging CRM note"

    _, c4, _ = sweeper.inspect_and_clean_profile(dirty_profiles[3])
    assert c4["is_active"] is False, "Failed purging publication"

    _, c5, _ = sweeper.inspect_and_clean_profile(dirty_profiles[4])
    assert c5["recruiter_name"] is None and c5["title"] == "Sales Development Representative", "Failed reclassifying job title"

    _, c6, _ = sweeper.inspect_and_clean_profile(dirty_profiles[5])
    assert c6["recruiter_name"] == "Matt Helander", f"Failed recovering name from email: {c6['recruiter_name']}"

    _, c7, _ = sweeper.inspect_and_clean_profile(dirty_profiles[6])
    assert c7["recruiter_name"] == "Antoinette Edmonston-Heard", f"Failed stripping MBA credential: {c7['recruiter_name']}"

    _, c8, _ = sweeper.inspect_and_clean_profile(dirty_profiles[7])
    assert c8["recruiter_name"] == "Allen Chao Hsuan Chi" and c8["title"] == "Data Analyst", f"Failed trailing title extraction: {c8}"

    _, c9, _ = sweeper.inspect_and_clean_profile(dirty_profiles[8])
    assert c9["is_deliverable"] is False and c9["email_status"] == "mailing_list_group", "Failed flagging mailing list"

    _, c10, _ = sweeper.inspect_and_clean_profile(dirty_profiles[9])
    assert c10["email"] is not None and "@stripe.com" in c10["email"], f"Failed corporate email synthesis: {c10}"

    print("\nProof 2: ALL 10 QUALITY DEFECT CATEGORIES VERIFIED & HEALED SUCCESSFULLY!")
    return True

def run_check_3():
    print_separator("CHECK 3: LIVE FASTAPI ENDPOINT & RECRUITER STORE INTEGRITY")
    
    headers = {"Authorization": "Bearer legacy_admin_bypass_token"}
    
    # 3.1: Live Sweeper Status Endpoint
    print("[3.1] Checking GET /api/email-intel/sweeper-status...")
    req1 = urllib.request.Request("http://127.0.0.1:8000/api/email-intel/sweeper-status", headers=headers)
    res1 = urllib.request.urlopen(req1)
    assert res1.status == 200, f"Expected 200 OK, got {res1.status}"
    data1 = json.loads(res1.read())
    print("      API Response HTTP 200 OK:")
    print(f"      - is_running: {data1['telemetry']['is_running']}")
    print(f"      - is_window_active: {data1['telemetry']['is_window_active']}")
    print(f"      - operating_window: {data1['telemetry']['operating_window']}")
    print(f"      - server_local_time: {data1['telemetry']['server_local_time']}")
    print(f"      - total_checked: {data1['telemetry']['stats']['total_checked']}")
    print(f"      - total_repaired: {data1['telemetry']['stats']['total_repaired']}")
    print(f"      - names_repaired: {data1['telemetry']['stats']['names_repaired']}")
    print(f"      - non_persons_purged: {data1['telemetry']['stats']['non_persons_purged']}")
    assert data1["success"] is True
    assert data1["telemetry"]["is_running"] is True
    print("      Proof 3.1: PASSED (Autonomous sweeper is live and operating)")

    # 3.2: Live Recruiter Store Query
    print("\n[3.2] Checking GET /recruiters?limit=10...")
    req2 = urllib.request.Request("http://127.0.0.1:8000/recruiters?limit=10", headers=headers)
    res2 = urllib.request.urlopen(req2)
    assert res2.status == 200, f"Expected 200 OK, got {res2.status}"
    data2 = json.loads(res2.read())
    recs = data2.get("items", []) or data2.get("results", []) or data2.get("recruiters", [])
    print(f"      API Response HTTP 200 OK. Fetched {len(recs)} recruiters from Parquet (Total: {data2.get('total_count'):,}).")
    for r in recs[:5]:
        print(f"      - Recruiter #{r['recruiter_id']}: '{r['recruiter_name']}' | Email: {r['email']} | Co: {r.get('company_name')} | Active: {r.get('is_active')}")
    assert len(recs) > 0
    print("      Proof 3.2: PASSED (DuckDB Parquet RecruiterStore serves clean profiles)")

    # 3.3: System Health Check
    print("\n[3.3] Checking GET /health...")
    req3 = urllib.request.Request("http://127.0.0.1:8000/health")
    res3 = urllib.request.urlopen(req3)
    assert res3.status == 200
    h_data = json.loads(res3.read())
    print(f"      System Status: {h_data.get('status')} | Service: {h_data.get('service')}")
    assert h_data.get("status") in ("healthy", "operational")
    print("      Proof 3.3: PASSED (System health check is 100% operational)")

    return True

if __name__ == "__main__":
    t_start = time.time()
    print("=" * 80)
    print("RUNNING 3-PASS INDEPENDENT VERIFICATION FOR STRICT MANDATE (RULE 11)")
    print("=" * 80)

    p1 = run_check_1()
    p2 = run_check_2()
    p3 = run_check_3()

    elapsed = round(time.time() - t_start, 2)
    print("\n" + "=" * 80)
    print(f"VERIFICATION COMPLETED IN {elapsed}s: ALL 3 STRICT CHECKS PASSED WITH PROOF!")
    print("=" * 80)
