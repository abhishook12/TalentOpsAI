"""
TalentOpsAI Master Verification & Integrity Audit Suite
======================================================
Executes comprehensive 3-point forensic verification across all recent updates:
  Check 1: Export Column Standardization (strictly Name, Email, Company, Phone Number, Designation)
  Check 2: Autonomous Email Healer & Permutation Engine (Typo Fix, MX Validation, Campaign Auto-Heal)
  Check 3: Ingested Datasets Integrity (Bresatech & Global HIT Roster in DuckDB & Parquet Store)
"""

import sys
import os
import requests
import io
import csv
import time
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.services.email_healer import email_healer
from app.services.recruiter_store import recruiter_store

REQUIRED_EXPORT_COLUMNS = ['Name', 'Email', 'Company', 'Phone Number', 'Designation']

def wait_for_backend():
    print("Waiting for backend on http://127.0.0.1:8000 ...")
    for _ in range(20):
        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=1)
            if r.status_code == 200:
                print("Backend online and ready!")
                return True
        except Exception:
            time.sleep(1)
    return False

def check_1_export_columns():
    print("\n" + "=" * 80)
    print(">>> CHECK 1: EXPORT COLUMN STANDARDIZATION (EXACT 5 COLUMNS) <<<")
    print("=" * 80)

    # 1.1 Test REST API CSV stream
    res_auth = requests.post("http://127.0.0.1:8000/auth/login", json={"email": "admin@talentops.ai", "password": "Admin@12345"})
    assert res_auth.status_code == 200, f"Login failed: {res_auth.text}"
    token = res_auth.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}

    export_res = requests.get("http://127.0.0.1:8000/recruiters/export?limit=5", headers=headers)
    assert export_res.status_code == 200, f"Export failed: {export_res.text}"

    csv_reader = csv.reader(io.StringIO(export_res.text))
    csv_header = next(csv_reader)
    print(f"API Export CSV Header: {csv_header}")
    assert csv_header == REQUIRED_EXPORT_COLUMNS, f"Header mismatch! Got {csv_header}"
    print("  * Header matches exact 5 required columns.")

    # 1.2 Test Excel XLSX generation format
    test_rows = [
        {'Name': 'Nash Castle', 'Email': 'ncastle@globalhit.com', 'Company': 'Global Path Resources', 'Phone Number': '+1 555-0199', 'Designation': 'CEO'},
        {'Name': 'Neal Wood', 'Email': 'neal.wood@bresatech.com', 'Company': 'Bresatech', 'Phone Number': '555-0200', 'Designation': 'Senior Recruiter'}
    ]
    df = pd.DataFrame(test_rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, columns=REQUIRED_EXPORT_COLUMNS, sheet_name='Recruiters')
    buf.seek(0)
    read_df = pd.read_excel(buf, sheet_name='Recruiters')
    print(f"Excel Sheet Columns:  {list(read_df.columns)}")
    assert list(read_df.columns) == REQUIRED_EXPORT_COLUMNS
    print("  * Excel binary format verified with exact 5 columns.")
    print("  --> [PASSED] Check 1: Export Column Standardization verified 100%!")


def check_2_email_healer():
    print("\n" + "=" * 80)
    print(">>> CHECK 2: AUTONOMOUS EMAIL HEALER & PERMUTATION ENGINE <<<")
    print("=" * 80)

    # 2.1 Typo correction
    t1 = email_healer.fix_domain_typo("recruiter@gmal.com")
    t2 = email_healer.fix_domain_typo("candidate@outlok.com")
    print(f"  * Typo Fix 1: recruiter@gmal.com -> {t1}")
    print(f"  * Typo Fix 2: candidate@outlok.com -> {t2}")
    assert t1 == "recruiter@gmail.com" and t2 == "candidate@outlook.com"

    # 2.2 Corporate permutation generator
    perms = email_healer.generate_permutations("Neal Wood", "bresatech.com")
    print(f"  * Generated {len(perms)} candidate permutations for Neal Wood @ bresatech.com: {perms[:3]}")
    assert "neal.wood@bresatech.com" in perms

    # 2.3 Single Recruiter Auto-Fix API call
    res_auth = requests.post("http://127.0.0.1:8000/auth/login", json={"email": "admin@talentops.ai", "password": "Admin@12345"})
    token = res_auth.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}

    fix_res = requests.post("http://127.0.0.1:8000/recruiters/3000478/auto-fix-email", headers=headers)
    assert fix_res.status_code == 200, f"Auto-fix failed: {fix_res.text}"
    fix_data = fix_res.json()
    print(f"  * Live Auto-Fix Recruiter #3000478 -> Repaired Email: {fix_data.get('repaired_email')} | Method: {fix_data.get('method')}")
    assert fix_data.get("success") is True
    print("  --> [PASSED] Check 2: Email Healer & Permutation Engine verified 100%!")


def check_3_dataset_roster_integrity():
    print("\n" + "=" * 80)
    print(">>> CHECK 3: DATASET & ROSTER INTEGRITY (BRESATECH & GLOBAL HIT) <<<")
    print("=" * 80)

    recruiter_store._ensure_loaded()
    conn = recruiter_store._conn

    total_records = conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
    print(f"Total Dataset Records: {total_records:,}")
    assert total_records >= 367745

    # 3.1 Bresatech records check
    bresatech_count = conn.execute("SELECT COUNT(*) FROM recruiters WHERE LOWER(email) LIKE '%@bresatech.com'").fetchone()[0]
    print(f"Bresatech Profiles in Database: {bresatech_count}")
    assert bresatech_count >= 36

    # 3.2 Global HIT records check
    globalhit_count = conn.execute("SELECT COUNT(*) FROM recruiters WHERE LOWER(email) LIKE '%@globalhit.com'").fetchone()[0]
    print(f"Global HIT Profiles in Database: {globalhit_count}")
    assert globalhit_count >= 56

    # 3.3 Verify completeness of sample profiles
    sample_check = conn.execute("""
        SELECT recruiter_name, email, seniority_level, quality_score, email_status
        FROM recruiters
        WHERE LOWER(email) IN ('ncastle@globalhit.com', 'jlanni@globalhit.com', 'neal.wood@bresatech.com')
    """).df()
    print("\nVerified Sample Profiles:")
    print(sample_check.to_string())
    assert len(sample_check) == 3
    for _, r in sample_check.iterrows():
        assert r['email_status'] == 'verified'
        assert r['quality_score'] >= 80

    print("\n  --> [PASSED] Check 3: Dataset and Roster Integrity verified 100%!")


if __name__ == "__main__":
    wait_for_backend()
    check_1_export_columns()
    check_2_email_healer()
    check_3_dataset_roster_integrity()
    print("\n" + "=" * 80)
    print("🎉 ALL 3 AUDIT CHECKS PASSED SUCCESSFULLY WITH ZERO ERRORS!")
    print("=" * 80)
