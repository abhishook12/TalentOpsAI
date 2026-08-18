import os
import sys
import duckdb

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import PARQUET_FILE

def run_pass2():
    print("=" * 80, flush=True)
    print("CHECK 2 (PASS 2): DUCKDB PARQUET COLUMNAR STORE FORENSIC VERIFICATION", flush=True)
    print("=" * 80, flush=True)

    con = duckdb.connect()
    pq_clean = PARQUET_FILE.replace(os.sep, '/')

    res = con.execute(f"""
        SELECT 
            recruiter_id,
            recruiter_name,
            email,
            phone,
            email_status,
            is_deliverable,
            email_confidence,
            location,
            state
        FROM read_parquet('{pq_clean}')
        WHERE email LIKE '%@davislaine.com'
        ORDER BY recruiter_id ASC
    """).fetchdf()

    uploaded_emails = [
        "dblythe@davislaine.com", "twilliams@davislaine.com", "ldavis@davislaine.com",
        "kroehm@davislaine.com", "jhall@davislaine.com", "uahmed@davislaine.com",
        "mlawler@davislaine.com", "conyia@davislaine.com", "baustensen@davislaine.com",
        "mnicholas@davislaine.com"
    ]

    print(f"[2.1] Total Records in Parquet for @davislaine.com: {len(res)}", flush=True)
    for email in uploaded_emails:
        match = res[res['email'] == email]
        assert len(match) == 1, f"Missing uploaded email in Parquet: {email}"
        row = match.iloc[0]
        print(f"      - Verified in Parquet: {row['recruiter_name']} <{row['email']}> | Deliverable: {row['is_deliverable']} | Conf: {row['email_confidence']}%")
        assert row['email_status'] == 'verified'
        assert row['is_deliverable'] == True
        assert row['email_confidence'] == 95

    con.close()
    print("\n" + "=" * 80, flush=True)
    print("CHECK 2 (PASS 2) RESULT: ALL 10 RECORDS 100% VERIFIED IN DUCKDB PARQUET STORE!", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_pass2()
