"""
TalentOps AI 3-Pass Forensic Verification Suite
===============================================
Executes rigorous triple-check verification on:
  1. Core Email Healer & Permutation Engine Logic
  2. Live REST API Campaign Auto-Heal & Recruiter Auto-Fix Endpoints
  3. Parquet/DuckDB Dataset Integrity & Bresatech Roster Deliverability
"""

import sys
import os
import requests
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.email_healer import email_healer, DOMAIN_TYPOS
from app.services.recruiter_store import recruiter_store

def run_pass_1():
    print("\n" + "="*80)
    print(">>> VERIFICATION CHECK 1: EMAIL HEALER SERVICE & PERMUTATION ENGINE <<<")
    print("="*80)

    # 1.1 Test domain typo correction
    print("\n[1.1] Testing Domain Typo Auto-Correction:")
    test_typos = [
        ("user@gmal.com", "user@gmail.com"),
        ("dev@outlok.com", "dev@outlook.com"),
        ("hire@yaho.com", "hire@yahoo.com"),
        ("recruiter@hotmial.com", "recruiter@hotmail.com"),
        ("talent@iclud.com", "talent@icloud.com")
    ]
    for raw, expected in test_typos:
        corrected = email_healer.fix_domain_typo(raw)
        print(f"  * {raw:25s} -> {corrected:25s} | Match: {corrected == expected}")
        assert corrected == expected, f"Typo fix failed for {raw}"
    print("  --> Typo correction logic PASSED (5/5).")

    # 1.2 Test corporate permutation generation
    print("\n[1.2] Testing Corporate Permutation Synthesis:")
    perms = email_healer.generate_permutations("Neal Wood", "bresatech.com")
    print(f"  * Generated {len(perms)} candidate permutations for 'Neal Wood @ bresatech.com':")
    for p in perms:
        print(f"    - {p}")
    assert "neal.wood@bresatech.com" in perms, "Expected neal.wood@bresatech.com in permutations"
    assert "nwood@bresatech.com" in perms, "Expected nwood@bresatech.com in permutations"
    print("  --> Corporate permutation engine PASSED.")

    # 1.3 Test MX record lookup cache
    print("\n[1.3] Testing MX DNS Cache & Resolution:")
    valid_mx = email_healer.has_mx_record("gmail.com")
    invalid_mx = email_healer.has_mx_record("nonexistent-domain-xyz-987.invalid")
    print(f"  * gmail.com has MX: {valid_mx} (Expected: True)")
    print(f"  * nonexistent domain has MX: {invalid_mx} (Expected: False)")
    assert valid_mx is True, "gmail.com should resolve MX"
    assert invalid_mx is False, "invalid domain should not resolve MX"
    print("  --> DNS MX verification PASSED.")
    print("\n[RESULT] CHECK 1 PASSED 100%!")


def run_pass_2():
    print("\n" + "="*80)
    print(">>> VERIFICATION CHECK 2: LIVE REST API CAMPAIGN AUTO-HEAL & RECRUITER AUTO-FIX <<<")
    print("="*80)

    # 2.1 Authenticate
    print("\n[2.1] Authenticating Admin Session:")
    for _ in range(15):
        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(1)

    res_auth = requests.post("http://127.0.0.1:8000/auth/login", json={
        "email": "admin@talentops.ai",
        "password": "Admin@12345"
    })
    assert res_auth.status_code == 200, f"Login failed: {res_auth.text}"
    token = res_auth.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  * Authenticated successfully. JWT Token acquired.")

    # 2.2 Create Test Campaign
    print("\n[2.2] Creating Test Campaign for Auto-Heal Probe:")
    camp_res = requests.post("http://127.0.0.1:8000/campaigns", headers=headers, json={
        "name": f"Forensic Verification Campaign {int(time.time())}",
        "status": "draft",
        "subject": "Talent Partnership",
        "body": "Hi {{first_name}}, let's connect."
    })
    assert camp_res.status_code in (200, 201), f"Campaign create failed: {camp_res.text}"
    cid = camp_res.json().get("campaign_id")
    print(f"  * Campaign created with ID: {cid}")

    # 2.3 Test Campaign Auto-Heal
    print("\n[2.3] Executing POST /campaigns/{id}/auto-heal:")
    payload = {
        "emails": [
            "neal.wood@bresatech.com", # Valid deliverable
            "candidate.test@gmal.com",  # Typo (should fix to @gmail.com)
            "recruiter.test@outlok.com",# Typo (should fix to @outlook.com)
            "dead_email_no_mx@invalid-domain-xyz-123.com" # Unfixable
        ],
        "names": [
            "Neal Wood",
            "Candidate Test",
            "Recruiter Test",
            "Dead Account"
        ]
    }
    heal_res = requests.post(f"http://127.0.0.1:8000/campaigns/{cid}/auto-heal", headers=headers, json=payload)
    print(f"  * HTTP Response Status: {heal_res.status_code}")
    assert heal_res.status_code == 200, f"Auto-heal failed: {heal_res.text}"
    data = heal_res.json()
    
    heal_summary = data.get("heal_summary", {})
    updated_preflight = data.get("updated_preflight", {})
    
    print(f"  * Total Submitted: {heal_summary.get('total_submitted')}")
    print(f"  * Total Auto-Healed: {heal_summary.get('total_healed')}")
    for h in heal_summary.get("healed", []):
        print(f"    - Healed: {h.get('original_email')} -> {h.get('repaired_email')} (via {h.get('method')})")
    
    print(f"  * Updated Pre-Flight Safe to Send: {updated_preflight.get('safe_to_send')}")
    print(f"  * Updated Pre-Flight Deliverability Rate: {updated_preflight.get('deliverability_rate')}%")
    assert heal_summary.get("total_healed") >= 2, "Expected at least 2 typos to be healed"
    print("  --> Campaign Auto-Heal API PASSED.")

    # 2.4 Test Single Recruiter Auto-Fix API
    print("\n[2.4] Executing POST /recruiters/{id}/auto-fix-email:")
    fix_res = requests.post("http://127.0.0.1:8000/recruiters/3000478/auto-fix-email", headers=headers)
    print(f"  * HTTP Response Status: {fix_res.status_code}")
    assert fix_res.status_code == 200, f"Recruiter auto-fix failed: {fix_res.text}"
    fix_data = fix_res.json()
    print(f"  * Repaired Email: {fix_data.get('repaired_email')}")
    print(f"  * Method: {fix_data.get('method')}")
    print(f"  * Confidence: {fix_data.get('confidence')}%")
    assert fix_data.get("success") is True
    print("  --> Single Recruiter Auto-Fix API PASSED.")
    print("\n[RESULT] CHECK 2 PASSED 100%!")


def run_pass_3():
    print("\n" + "="*80)
    print(">>> VERIFICATION CHECK 3: BRESATECH ROSTER & DUCKDB PARQUET DATASET INTEGRITY <<<")
    print("="*80)

    recruiter_store._ensure_loaded()
    conn = recruiter_store._conn

    # 3.1 Total Dataset Count
    total_records = conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
    print(f"\n[3.1] Total Profiles in Parquet: {total_records:,}")
    assert total_records >= 367726, f"Expected at least 367,726 records, got {total_records}"

    # 3.2 Bresatech Roster Verification
    print("\n[3.2] Querying All Bresatech Records:")
    bresatech_df = conn.execute("""
        SELECT recruiter_id, recruiter_name, email, title, seniority_level, quality_score, logo_url, linkedin, email_status
        FROM recruiters
        WHERE LOWER(email) LIKE '%@bresatech.com'
        ORDER BY recruiter_id
    """).df()
    print(f"  * Found {len(bresatech_df)} Bresatech Profiles:")
    print(bresatech_df[['recruiter_name', 'email', 'seniority_level', 'quality_score', 'email_status']].to_string())
    
    assert len(bresatech_df) >= 28, f"Expected 28+ Bresatech profiles, found {len(bresatech_df)}"
    
    # 3.3 Check No Missing Critical Fields in Bresatech
    for _, row in bresatech_df.iterrows():
        assert row['email'] and '@bresatech.com' in row['email'].lower(), f"Invalid email: {row['email']}"
        assert row['logo_url'] and row['logo_url'].startswith('http'), f"Invalid logo: {row['logo_url']}"
        assert row['linkedin'] and 'linkedin.com' in row['linkedin'], f"Invalid linkedin: {row['linkedin']}"
        assert row['quality_score'] >= 75, f"Low quality score: {row['quality_score']}"
        assert row['email_status'] == 'verified', f"Unverified email status: {row['email_status']}"
    print("  --> Bresatech data completeness & deliverability verification PASSED.")

    # 3.4 API Search Query Test
    print("\n[3.4] Testing Live Full-Text & Company Search for 'bresatech':")
    res_auth = requests.post("http://127.0.0.1:8000/auth/login", json={"email": "admin@talentops.ai", "password": "Admin@12345"})
    token = res_auth.json().get("token")
    search_res = requests.get("http://127.0.0.1:8000/recruiters?search=bresatech&limit=10", headers={"Authorization": f"Bearer {token}"})
    assert search_res.status_code == 200, f"Search failed: {search_res.text}"
    search_data = search_res.json()
    print(f"  * API Search matched {search_data.get('total_count')} recruiters for keyword 'bresatech'")
    assert search_data.get('total_count') >= 28, "Search should match all Bresatech profiles"
    print("  --> Search endpoint integration PASSED.")
    print("\n[RESULT] CHECK 3 PASSED 100%!")


if __name__ == "__main__":
    run_pass_1()
    run_pass_2()
    run_pass_3()
    print("\n" + "="*80)
    print("🎉 ALL 3 CHECKS SUCCESSFULLY COMPLETED AND VERIFIED!")
    print("="*80)
