import duckdb
import os
import shutil
import time

t0 = time.time()
print("Starting high-speed in-memory domain unification...", flush=True)

con = duckdb.connect()
con.execute("PRAGMA threads=8;")
con.execute("PRAGMA memory_limit='6GB';")

FREE_DOMAINS = (
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
)
free_sql = ", ".join(f"'{d}'" for d in FREE_DOMAINS)

PARQUET_FILE = 'backend/data/recruiters_full.parquet'
TEMP_PARQUET = 'backend/data/recruiters_unified_temp.parquet'

# 1. Load Parquet into in-memory table with pre-extracted domain column
t_load = time.time()
print("Loading 2.3M records into in-memory table with pre-extracted domain...", flush=True)
con.execute(f"""
    CREATE TABLE recruiters_mem AS 
    SELECT 
        *, 
        CASE 
            WHEN email IS NOT NULL AND email LIKE '%@%' THEN LOWER(SPLIT_PART(email, '@', 2))
            ELSE NULL 
        END AS extracted_domain
    FROM '{PARQUET_FILE}'
""")
print(f"Loaded in {time.time()-t_load:.2f}s", flush=True)

# 2. Canonical domain mapping
t_canon = time.time()
print("Building canonical domain map...", flush=True)
con.execute(f"""
    CREATE TABLE domain_canonical AS
    SELECT 
        extracted_domain as domain,
        MODE(company_id) as canonical_cid
    FROM recruiters_mem
    WHERE extracted_domain IS NOT NULL 
      AND extracted_domain NOT IN ({free_sql})
      AND company_id IS NOT NULL 
      AND TRIM(CAST(company_id AS VARCHAR)) != ''
      AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('need to fill data', 'unknown', 'n/a', 'none', 'null')
    GROUP BY extracted_domain
""")
c_count = con.execute("SELECT COUNT(*) FROM domain_canonical").fetchone()[0]
print(f"Generated canonical mapping for {c_count:,} domains in {time.time()-t_canon:.2f}s", flush=True)

# 3. Direct update via in-memory hash join
t_upd = time.time()
print("Updating company_id across all records...", flush=True)
con.execute("""
    UPDATE recruiters_mem
    SET company_id = dc.canonical_cid,
        canonical_company_id = dc.canonical_cid
    FROM domain_canonical dc
    WHERE recruiters_mem.extracted_domain = dc.domain
""")
print(f"Updated in {time.time()-t_upd:.2f}s", flush=True)

# 4. Copy to temporary parquet file
t_copy = time.time()
print("Writing optimized unified Parquet file...", flush=True)
con.execute(f"""
    COPY (
        SELECT * EXCLUDE (extracted_domain)
        FROM recruiters_mem
    ) TO '{TEMP_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD)
""")
print(f"Exported Parquet in {time.time()-t_copy:.2f}s", flush=True)

# 5. Swap files
if os.path.exists(TEMP_PARQUET):
    if os.path.getsize(TEMP_PARQUET) > 10_000_000:
        shutil.move(TEMP_PARQUET, PARQUET_FILE)
        print("Successfully replaced main dataset with unified dataset.", flush=True)
    else:
        print("Error: Generated file too small, not replacing.", flush=True)

# 6. Verification
print("\n--- VERIFYING RESULTS ---", flush=True)
rht_rows = con.execute(f"""
    SELECT company_id, COUNT(*) as cnt, MIN(email) as sample_email
    FROM '{PARQUET_FILE}'
    WHERE email LIKE '%@rht.com'
    GROUP BY company_id
""").fetchall()

print("--- RHT.COM IN NEW PARQUET ---", flush=True)
for r in rht_rows:
    print(r, flush=True)

rh_rows = con.execute(f"""
    SELECT company_id, COUNT(*) as cnt, MIN(email) as sample_email
    FROM '{PARQUET_FILE}'
    WHERE email LIKE '%@roberthalf.com'
    GROUP BY company_id
""").fetchall()

print("--- ROBERTHALF.COM IN NEW PARQUET ---", flush=True)
for r in rh_rows:
    print(r, flush=True)

frag_left = con.execute(f"""
    SELECT LOWER(SPLIT_PART(email, '@', 2)) as domain, COUNT(DISTINCT company_id) as distinct_cids
    FROM '{PARQUET_FILE}'
    WHERE email IS NOT NULL 
      AND email LIKE '%@%'
      AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql})
    GROUP BY domain
    HAVING COUNT(DISTINCT company_id) > 1
""").fetchall()

print(f"\nRemaining fragmented corporate domains: {len(frag_left)} (Expected: 0)", flush=True)
print(f"Total time elapsed: {time.time()-t0:.2f}s", flush=True)
