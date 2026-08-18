import os
import sys
import duckdb

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import PARQUET_FILE

def run_pass2():
    print("=" * 80)
    print("CHECK 2 (PASS 2): DUCKDB PARQUET COLUMNAR STORE FORENSIC VERIFICATION")
    print("=" * 80)

    con = duckdb.connect()
    pq_clean = PARQUET_FILE.replace(os.sep, '/')

    res = con.execute(f"""
        SELECT 
            recruiter_id,
            recruiter_name,
            email,
            email_status,
            is_deliverable,
            email_confidence,
            location,
            state
        FROM read_parquet('{pq_clean}')
        WHERE email LIKE '%@corneralliance.com'
        ORDER BY recruiter_id ASC
    """).fetchdf()

    print(f"[2.1] Total Records in Parquet for @corneralliance.com: {len(res)}")
    assert len(res) == 14, f"Expected 14 records in Parquet, found {len(res)}"

    print(res.to_string())

    for idx, row in res.iterrows():
        assert row['email_status'] == 'verified', f"Expected status 'verified', got {row['email_status']}"
        assert row['is_deliverable'] == True, "Expected is_deliverable=True"
        assert row['email_confidence'] == 95, f"Expected confidence 95, got {row['email_confidence']}"

    con.close()
    print("\n" + "=" * 80)
    print("CHECK 2 (PASS 2) RESULT: ALL 14 RECORDS 100% VERIFIED IN DUCKDB PARQUET STORE!")
    print("=" * 80)

if __name__ == "__main__":
    run_pass2()
