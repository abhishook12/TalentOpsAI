"""
PURGE GHOST SHADOWS
===================
Permanently deletes legacy empty/ghost records from Parquet that shadow
real, verified Microsoft Teams candidates by name.
"""
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\TalentOpsAI\backend")

import duckdb

PARQUET_PATH = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
TEMP_PARQUET_PATH = "C:/TalentOpsAI/backend/data/recruiters_full_temp.parquet"

print("="*80, flush=True)
print("     TALENTOPS: PURGING GHOST SHADOWS FROM PARQUET", flush=True)
print("="*80, flush=True)

con = duckdb.connect()
con.execute(f"CREATE TABLE master AS SELECT * FROM read_parquet('{PARQUET_PATH}')")
initial_cnt = con.execute("SELECT count(*) FROM master").fetchone()[0]
print(f"Initial Parquet count: {initial_cnt}", flush=True)

con.execute("""
    WITH teams_recs AS (
        SELECT lower(trim(recruiter_name)) AS tname
        FROM master
        WHERE data_source = 'teams' AND phone IS NOT NULL AND phone != ''
        GROUP BY 1
    )
    DELETE FROM master
    WHERE data_source != 'teams' 
      AND (phone IS NULL OR phone = '')
      AND lower(trim(recruiter_name)) IN (SELECT tname FROM teams_recs);
""")

post_cnt = con.execute("SELECT count(*) FROM master").fetchone()[0]
deleted = initial_cnt - post_cnt
print(f"Deleted {deleted} empty ghost records shadowing real Teams candidates.", flush=True)
print(f"Final Parquet count: {post_cnt}", flush=True)

print("Writing clean master to temp parquet...", flush=True)
con.execute(f"COPY master TO '{TEMP_PARQUET_PATH}' (FORMAT PARQUET)")
con.close()

print("Replacing live parquet file...", flush=True)
replaced = False
for attempt in range(10):
    try:
        os.replace(TEMP_PARQUET_PATH, PARQUET_PATH)
        replaced = True
        break
    except (PermissionError, OSError) as e:
        print(f"   Waiting for file lock (attempt {attempt+1}): {e}", flush=True)
        time.sleep(1.0)

if not replaced:
    raise RuntimeError("Failed to replace Parquet due to lock!")

print("\n=== GHOST SHADOWS PURGED SUCCESSFULLY! ===", flush=True)
