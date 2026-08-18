import os
import sys
import duckdb
from datetime import datetime, timezone

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import recruiter_store, PARQUET_FILE
from app.database import SessionLocal
from app.models.models import Recruiter

print("=" * 80)
print("DEDUPLICATING & CONSOLIDATING DAVIS LAINE RECORDS IN PARQUET")
print("=" * 80)

con = duckdb.connect()
pq_clean = PARQUET_FILE.replace(os.sep, '/')
tmp_out = f"{PARQUET_FILE}.tmp_dedup.parquet".replace(os.sep, '/')

# Deduplicate by prioritizing enriched rows with full names, phone numbers, and location
con.execute(f"""
COPY (
    WITH ranked AS (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY LOWER(email) 
                ORDER BY 
                    CASE WHEN phone IS NOT NULL THEN 1 ELSE 2 END,
                    CASE WHEN location IS NOT NULL THEN 1 ELSE 2 END,
                    LENGTH(COALESCE(recruiter_name, '')) DESC,
                    recruiter_id DESC
            ) as rn
        FROM read_parquet('{pq_clean}')
    )
    SELECT * EXCLUDE(rn) FROM ranked WHERE rn = 1
) TO '{tmp_out}' (FORMAT PARQUET)
""")

con.close()

os.replace(tmp_out.replace('/', os.sep), PARQUET_FILE)
recruiter_store.reload()

print("[+] Parquet deduplicated by canonical email and RecruiterStore reloaded.")
