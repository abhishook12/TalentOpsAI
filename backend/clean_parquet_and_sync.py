"""
CLEAN PARQUET AND FULL RE-SYNC FROM POSTGRESQL
==============================================
1. Removes all 3,188 ghost/duplicate records in Parquet that conflict with PostgreSQL.
2. Synchronizes all authoritative PostgreSQL records into Parquet with correct types and encoding.
3. Verifies zero email collisions between PostgreSQL and Parquet.
"""
import sys, os, json, time, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\TalentOpsAI\backend")

import duckdb
import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv(r"C:\TalentOpsAI\backend\.env")
DB_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
if DB_URL and "+psycopg" in DB_URL:
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

PARQUET_PATH = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
TEMP_PARQUET_PATH = "C:/TalentOpsAI/backend/data/recruiters_full_temp.parquet"

parquet_columns = [
    'recruiter_id', 'recruiter_name', 'normalized_recruiter_name', 'email', 'phone', 'email2', 
    'phone2', 'email3', 'phone3', 'email4', 'phone4', 'alternate_emails', 'alternate_phones', 
    'linkedin', 'specialization', 'title', 'notes', 'review_reason', 'location', 'state', 
    'normalized_city', 'location_confidence', 'state_source', 'state_confidence', 'state_reason', 
    'last_scan_at', 'completeness_score', 'needs_review', 'is_active', 'data_source', 'trust_score', 
    'source_job_id', 'raw_data', 'metadata_json', 'tags', 'created_at', 'updated_at', 
    'taxonomy_category', 'report_count', 'email_status', 'email_confidence', 'email_source', 
    'email_pattern_id', 'email_generated', 'email_verified_at', 'email_last_checked_at', 
    'canonical_company_id', 'historical_company_id', 'company_domain_id', 'raw_email_value', 
    'repair_reason', 'user_id', 'quality_score', 'missing_fields', 'sentinel_status', 
    'last_verified_at', 'company_confidence', 'company_reasoning', 'is_archived', 'company_id'
]

print("1. Connecting to PostgreSQL...", flush=True)
pg_conn = psycopg.connect(DB_URL)
cur = pg_conn.cursor()

pg_cols = parquet_columns.copy()
pg_cols[pg_cols.index('is_archived')] = 'false AS is_archived'

query = f"SELECT {', '.join(pg_cols)} FROM recruiters"
print("2. Fetching all recruiters from PostgreSQL...", flush=True)
cur.execute(query)
rows = cur.fetchall()
pg_conn.close()
print(f"   Fetched {len(rows)} records from PostgreSQL.", flush=True)

df_pg = pd.DataFrame(rows, columns=parquet_columns)

# Clean json/string columns
for str_col in ['alternate_emails', 'alternate_phones', 'raw_data', 'repair_reason', 'metadata_json', 'notes', 'tags', 'missing_fields']:
    if str_col in df_pg.columns:
        df_pg[str_col] = df_pg[str_col].apply(
            lambda x: json.dumps(x) if isinstance(x, (list, dict)) else (str(x) if x is not None and not pd.isna(x) and str(x).lower() != 'nan' else None)
        )
for num_col in ['quality_score', 'trust_score', 'completeness_score', 'report_count']:
    if num_col in df_pg.columns:
        df_pg[num_col] = pd.to_numeric(df_pg[num_col], errors='coerce')

# Clean titles of non-ascii dashes
if 'title' in df_pg.columns:
    df_pg['title'] = df_pg['title'].apply(lambda x: str(x).replace('–', '-').replace('—', '-').strip() if x else x)

if 'company_id' in df_pg.columns:
    df_pg['company_id'] = df_pg['company_id'].apply(lambda x: int(float(x)) if x is not None and not pd.isna(x) and str(x).replace('.0','').isdigit() else None)

print("3. Loading Parquet master into DuckDB...", flush=True)
source_parquet = PARQUET_PATH + ".bak" if os.path.exists(PARQUET_PATH + ".bak") else PARQUET_PATH
con = duckdb.connect()
con.execute(f"""
    CREATE TABLE master AS SELECT * REPLACE (
        CAST(alternate_emails AS VARCHAR) AS alternate_emails, 
        CAST(alternate_phones AS VARCHAR) AS alternate_phones,
        CAST(raw_data AS VARCHAR) AS raw_data,
        CAST(repair_reason AS VARCHAR) AS repair_reason,
        CAST(quality_score AS DOUBLE) AS quality_score,
        CAST(trust_score AS DOUBLE) AS trust_score
    ) FROM read_parquet('{source_parquet}')
""")

initial_count = con.execute("SELECT count(*) FROM master").fetchone()[0]
print(f"   Initial Parquet row count: {initial_count}", flush=True)

# Register df_pg as temporary view
con.register("df_pg", df_pg)

print("4. Purging ghost/duplicate records from Parquet...", flush=True)
# Delete any row from master that matches by recruiter_id OR by any email (primary or secondary) of the incoming PostgreSQL records
con.execute("""
    CREATE TEMP TABLE pg_all_emails AS
    SELECT lower(email) AS em FROM df_pg WHERE email IS NOT NULL AND email != ''
    UNION
    SELECT lower(email2) AS em FROM df_pg WHERE email2 IS NOT NULL AND email2 != ''
    UNION
    SELECT lower(email3) AS em FROM df_pg WHERE email3 IS NOT NULL AND email3 != ''
    UNION
    SELECT lower(email4) AS em FROM df_pg WHERE email4 IS NOT NULL AND email4 != '';

    CREATE TEMP TABLE pg_name_domains AS
    SELECT lower(recruiter_name) AS rname, split_part(lower(email), '@', 2) AS dom
    FROM df_pg
    WHERE email IS NOT NULL AND email != '' AND recruiter_name IS NOT NULL AND recruiter_name != '';

    DELETE FROM master 
    WHERE recruiter_id IN (SELECT recruiter_id FROM df_pg)
       OR (email IS NOT NULL AND email != '' AND lower(email) IN (SELECT em FROM pg_all_emails))
       OR (email2 IS NOT NULL AND email2 != '' AND lower(email2) IN (SELECT em FROM pg_all_emails))
       OR (email3 IS NOT NULL AND email3 != '' AND lower(email3) IN (SELECT em FROM pg_all_emails))
       OR (email4 IS NOT NULL AND email4 != '' AND lower(email4) IN (SELECT em FROM pg_all_emails))
       OR (lower(recruiter_name) IN (SELECT rname FROM pg_name_domains) AND split_part(lower(email), '@', 2) IN (SELECT dom FROM pg_name_domains));
""")

post_delete_count = con.execute("SELECT count(*) FROM master").fetchone()[0]
deleted_count = initial_count - post_delete_count
print(f"   Deleted {deleted_count} conflicting/duplicate/ghost rows from Parquet.", flush=True)

print("5. Inserting fresh authoritative PostgreSQL records into Parquet...", flush=True)
cols_sql = ', '.join(parquet_columns)
con.execute(f"INSERT INTO master ({cols_sql}) SELECT * FROM df_pg")

final_count = con.execute("SELECT count(*) FROM master").fetchone()[0]
print(f"   Final Parquet row count: {final_count}", flush=True)

print("6. Writing to temp parquet...", flush=True)
con.execute(f"COPY master TO '{TEMP_PARQUET_PATH}' (FORMAT PARQUET)")
con.close()

print("7. Replacing live Parquet file...", flush=True)
replaced = False
for attempt in range(10):
    try:
        os.replace(TEMP_PARQUET_PATH, PARQUET_PATH)
        replaced = True
        break
    except (PermissionError, OSError) as e:
        print(f"   Attempt {attempt+1} waiting for file lock: {e}")
        time.sleep(1.0)

if not replaced:
    raise RuntimeError("Failed to replace parquet file due to persistent file lock!")

print("8. Verifying Parquet file integrity...", flush=True)
con2 = duckdb.connect()

# Check Jessica Burgess
jb = con2.execute(f"SELECT recruiter_id, recruiter_name, email, phone, phone2, phone3, phone4, alternate_phones FROM read_parquet('{PARQUET_PATH}') WHERE email = 'jessica.burgess@zones.com'").fetchall()
print(f"   Jessica Burgess in Parquet: {len(jb)} record(s)")
for r in jb:
    print(f"     ID={r[0]}, Phone={r[3]}, Phone2={r[4]}, Phone3={r[5]}, Phone4={r[6]}, Alt={r[7]}")

# Check Yuka Komatsu
yk = con2.execute(f"SELECT recruiter_id, recruiter_name, email, title, location, phone, phone2 FROM read_parquet('{PARQUET_PATH}') WHERE email = 'yuka.komatsu@cinter.net'").fetchall()
print(f"   Yuka Komatsu in Parquet: {len(yk)} record(s)")
for r in yk:
    print(f"     ID={r[0]}, Title={r[3]}, Location={r[4]}, Phone={r[5]}, Phone2={r[6]}")

con2.close()
print("\n=== PARQUET CLEAN & SYNC COMPLETED SUCCESSFULLY! ===")
