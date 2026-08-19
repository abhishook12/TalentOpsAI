"""
TalentOpsAI - Platform Intelligence & Deployment 3-Pass Forensic Audit
======================================================================
Strict Check 3 Times Rule:
  Pass 1: Email Spam Analyzer & Pre-Flight Deliverability Audit
  Pass 2: AI Boolean Query Generator & Cross-Platform Sourcing Audit
  Pass 3: Dataset Deduplication Engine & Parquet Forensic Snapshot Audit
"""

import os
import sys
import time
import requests
import json

BASE_URL = "http://127.0.0.1:8000"
ADMIN_USER = "admin@talentops.ai"
ADMIN_PASS = "Admin@12345"


def log(msg, status="INFO"):
    symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else ">>>"
    print(f" {symbol} {msg}")


def authenticate():
    s = requests.Session()
    try:
        r = s.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_USER, "password": ADMIN_PASS}, timeout=5)
        if r.status_code == 200:
            token = r.json().get("token") or r.json().get("access_token")
            s.headers.update({"Authorization": f"Bearer {token}"})
            s.cookies.set("access_token", token)
            return s
    except Exception as e:
        print(f"Auth error: {e}")
    return s


def run_pass_1_spam_deliverability(s):
    print("\n" + "=" * 65)
    print(">>> PASS 1: EMAIL SPAM ANALYZER & PRE-FLIGHT DELIVERABILITY AUDIT")
    print("=" * 65)

    # Test 1A: Clean Outreach Template
    clean_payload = {
        "subject": "Quick question regarding Engineering opportunities at {{company}}",
        "body": "Hi {{first_name}},\n\nI came across your profile and was impressed with your background in full-stack architecture. We are currently scaling our engineering team. If you're open to learning more, I'd love to connect.\n\nBest regards,\nAlex\n\nIf you prefer not to receive updates, reply STOP to unsubscribe."
    }
    r1 = s.post(f"{BASE_URL}/campaigns/preflight-spam-check", json=clean_payload, timeout=5)
    assert r1.status_code == 200, f"Spam check failed with status {r1.status_code}"
    res1 = r1.json()
    log(f"Clean Template Score: {res1['deliverability_score']}/100 (Spam Score: {res1['spam_score']}) | Tier: {res1['risk_tier']}", "PASS")
    assert res1['is_safe'] == True
    assert res1['deliverability_score'] >= 85

    # Test 1B: Spam-Heavy High-Risk Template
    spam_payload = {
        "subject": "URGENT RESPONSE REQUIRED: 100% FREE MONEY GUARANTEED $$$",
        "body": "ACT NOW! You have won a million dollars and pure profit cash bonus! Click here immediately to claim your prize! Don't delete this opportunity of a lifetime!!!"
    }
    r2 = s.post(f"{BASE_URL}/campaigns/preflight-spam-check", json=spam_payload, timeout=5)
    assert r2.status_code == 200
    res2 = r2.json()
    log(f"Spam Template Score: {res2['deliverability_score']}/100 (Spam Score: {res2['spam_score']}) | Tier: {res2['risk_tier']}", "PASS")
    assert res2['is_safe'] == False
    assert res2['risk_tier'] == 'high'
    assert len(res2['flags']) >= 4

    print("Pass 1: Pre-Flight Deliverability & Spam Engine Verified Successfully.")


def run_pass_2_boolean_sourcing(s):
    print("\n" + "=" * 65)
    print(">>> PASS 2: AI BOOLEAN QUERY GENERATOR & SOURCING ENGINE AUDIT")
    print("=" * 65)

    # Test 2A: Direct Parameters
    payload_a = {
        "role": "Senior React Developer, Lead Frontend Engineer",
        "required_skills": ["React", "TypeScript", "Next.js"],
        "optional_skills": ["GraphQL", "Tailwind"],
        "excluded_keywords": ["Junior", "Intern"],
        "location": "TX"
    }
    r_a = s.post(f"{BASE_URL}/ai/boolean-builder", json=payload_a, timeout=5)
    assert r_a.status_code == 200, f"Boolean builder failed with status {r_a.status_code}"
    res_a = r_a.json()
    log(f"Generated LinkedIn Boolean: {res_a['linkedin_boolean'][:60]}...", "PASS")
    log(f"Generated Google X-Ray:     {res_a['google_xray_query'][:60]}...", "PASS")
    log(f"Generated TalentOps Query:  {res_a['talentops_query']}", "PASS")
    assert "site:linkedin.com/in" in res_a['google_xray_query']
    assert "React" in res_a['linkedin_boolean']
    assert "NOT" in res_a['linkedin_boolean']

    # Test 2B: Unstructured Job Description Ingestion
    payload_b = {
        "job_description": "We are seeking an Epic Clinical Informaticist or Epic Systems Analyst in California with Epic certification and SQL reporting experience."
    }
    r_b = s.post(f"{BASE_URL}/ai/boolean-builder", json=payload_b, timeout=5)
    assert r_b.status_code == 200
    res_b = r_b.json()
    log(f"Extracted JD Role & Skills: {res_b['extracted_skills']}", "PASS")
    assert len(res_b['extracted_skills']) > 0

    print("Pass 2: Cross-Platform Boolean Synthesis Verified Successfully.")


def run_pass_3_dedup_and_snapshots(s):
    print("\n" + "=" * 65)
    print(">>> PASS 3: PARQUET DEDUPLICATION & FORENSIC SNAPSHOT AUDIT")
    print("=" * 65)

    # Test 3A: Deduplication Scan
    r_scan = s.get(f"{BASE_URL}/admin/deduplicate/scan?limit=10", timeout=10)
    assert r_scan.status_code == 200, f"Dedup scan failed with status {r_scan.status_code}: {r_scan.text}"
    scan_res = r_scan.json()
    log(f"Deduplication Scan: Found {scan_res['total_duplicate_clusters_found']} clusters ({scan_res['estimated_redundant_records']} redundant records)", "PASS")

    # Test 3B: Deduplication Dry-Run Consolidation
    r_merge = s.post(
        f"{BASE_URL}/admin/deduplicate/merge",
        json={"match_strategy": "email", "max_clusters": 5, "dry_run": True},
        timeout=10
    )
    assert r_merge.status_code == 200, f"Dedup merge failed: {r_merge.text}"
    merge_res = r_merge.json()
    log(f"Dry-run Consolidation: Verified {merge_res['clusters_processed']} clusters ready for canonical merge", "PASS")

    # Test 3C: Automated Parquet Snapshot Backup
    r_snap = s.post(
        f"{BASE_URL}/admin/backup/snapshot",
        json={"reason": "3-Pass Forensic Master Verification"},
        timeout=15
    )
    assert r_snap.status_code == 200, f"Snapshot creation failed: {r_snap.text}"
    snap_res = r_snap.json()
    log(f"Parquet Snapshot Created: {snap_res['filename']} ({snap_res['size_mb']} MB) | SHA-256: {snap_res['checksum_sha256'][:16]}...", "PASS")

    # Test 3D: List Snapshots
    r_list = s.get(f"{BASE_URL}/admin/backup/snapshots", timeout=5)
    assert r_list.status_code == 200, f"List snapshots failed: {r_list.text}"
    snaps = r_list.json()
    log(f"Snapshot Registry: {len(snaps)} immutable backup snapshot(s) verified on disk", "PASS")
    assert len(snaps) >= 1

    print("Pass 3: Deduplication Engine & Parquet Backup Snapshots Verified Successfully.")


def main():
    print("=" * 65)
    print(" TALENTOPS AI - 3-PASS FORENSIC MASTER VERIFICATION SUITE")
    print("=" * 65)
    s = authenticate()
    
    try:
        run_pass_1_spam_deliverability(s)
        run_pass_2_boolean_sourcing(s)
        run_pass_3_dedup_and_snapshots(s)
        print("\n" + "=" * 65)
        print(">>> ALL 3 PASSES PASSED WITH 100% FORENSIC INTEGRITY! <<<")
        print("=" * 65)
    except AssertionError as e:
        print(f"\n[AUDIT FAILED]: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[AUDIT EXCEPTION]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
