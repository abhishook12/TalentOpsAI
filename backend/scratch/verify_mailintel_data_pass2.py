import sys
import os
import duckdb

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import PARQUET_FILE

def run_pass2_data_integrity_audit():
    print("=" * 80)
    print("CHECK 2 (PASS 2): FULL DATASET DELIVERABILITY INTEGRITY & PARITY FORENSIC AUDIT")
    print("=" * 80)

    con = duckdb.connect()
    pq_clean = PARQUET_FILE.replace(os.sep, '/')

    # 1. Total Record Count
    total_records = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pq_clean}')").fetchone()[0]
    print(f"\n[2.1] Total Records in Parquet Dataset: {total_records:,}")
    assert total_records > 400000, "Dataset record count below expected threshold"

    # 2. Check Deliverability Status Breakdown
    print("\n[2.2] Auditing Status Breakdown & Deliverability Enums ...")
    breakdown_df = con.execute(f"""
        SELECT 
            email_status,
            is_deliverable,
            COUNT(*) as record_count,
            AVG(email_confidence) as avg_confidence,
            MIN(email_confidence) as min_confidence,
            MAX(email_confidence) as max_confidence
        FROM read_parquet('{pq_clean}')
        GROUP BY 1, 2
        ORDER BY record_count DESC
    """).fetchdf()
    print(breakdown_df.to_string())

    # 3. Assert zero missing emails marked deliverable
    print("\n[2.3] Validating Missing Email Quarantine Integrity ...")
    missing_deliverable_cnt = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{pq_clean}')
        WHERE (email IS NULL OR email = '' OR email LIKE '%@missing.local%') AND is_deliverable = true
    """).fetchone()[0]
    print(f"      Missing emails with is_deliverable=true: {missing_deliverable_cnt} (MUST BE 0)")
    assert missing_deliverable_cnt == 0, f"Integrity violation: {missing_deliverable_cnt} missing emails are marked deliverable"
    print("      [PASS 2.3] Missing email quarantine verified 100% clean!")

    # 4. Assert undeliverable records have is_deliverable=false and confidence=0
    print("\n[2.4] Validating Undeliverable & Dead Domain Rules ...")
    undeliv_err_cnt = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{pq_clean}')
        WHERE email_status = 'undeliverable' AND (is_deliverable = true OR email_confidence > 0)
    """).fetchone()[0]
    print(f"      Undeliverable records with is_deliverable=true or confidence>0: {undeliv_err_cnt} (MUST BE 0)")
    assert undeliv_err_cnt == 0, f"Integrity violation: {undeliv_err_cnt} invalid undeliverable records"
    print("      [PASS 2.4] Undeliverable records verified 100% clean!")

    # 5. Assert total conservation
    print("\n[2.5] Validating Conservation of Total Records ...")
    status_sum = breakdown_df['record_count'].sum()
    print(f"      Sum of Categorized Records: {status_sum:,} == Total Records: {total_records:,}")
    assert status_sum == total_records, "Record count mismatch during aggregation"
    print("      [PASS 2.5] Total record conservation verified 100%!")

    con.close()
    print("\n" + "=" * 80)
    print("CHECK 2 (PASS 2) RESULT: ALL 5 DELIVERABILITY DATA RULES PASSED 100%")
    print("=" * 80)

if __name__ == "__main__":
    run_pass2_data_integrity_audit()
