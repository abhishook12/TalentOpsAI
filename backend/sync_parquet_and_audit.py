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

print(f"   Fetched {len(rows)} authoritative recruiters from PostgreSQL.", flush=True)
pg_df = pd.DataFrame(rows, columns=parquet_columns)

# Handle string conversions
for col in pg_df.columns:
    if col in ('recruiter_id', 'completeness_score', 'quality_score', 'company_id', 'canonical_company_id', 'historical_company_id', 'company_domain_id'):
        continue
    elif col in ('needs_review', 'is_active', 'email_generated', 'is_archived'):
        continue
    elif col in ('created_at', 'updated_at', 'last_scan_at', 'email_verified_at', 'email_last_checked_at', 'last_verified_at'):
        continue
    else:
        pg_df[col] = pg_df[col].astype(str).replace({'None': '', 'nan': ''})

con = duckdb.connect()
con.register('pg_data', pg_df)

print("3. Exporting to Parquet atomically...", flush=True)
con.execute(f"COPY (SELECT * FROM pg_data) TO '{TEMP_PARQUET_PATH}' (FORMAT PARQUET, COMPRESSION ZSTD);")
con.close()

if os.path.exists(PARQUET_PATH):
    backup_path = PARQUET_PATH + ".bak"
    try:
        if os.path.exists(backup_path): os.remove(backup_path)
        os.rename(PARQUET_PATH, backup_path)
    except Exception as e:
        print(f"   Warning moving backup: {e}")

try:
    os.replace(TEMP_PARQUET_PATH, PARQUET_PATH)
    print(f"4. Replaced {PARQUET_PATH} successfully!", flush=True)
except Exception as e:
    print(f"   Error replacing parquet: {e}")

con = duckdb.connect()
tot = con.execute(f"SELECT count(*) FROM read_parquet('{PARQUET_PATH}')").fetchone()[0]
teams_cnt = con.execute(f"SELECT count(*) FROM read_parquet('{PARQUET_PATH}') WHERE data_source = 'teams'").fetchone()[0]
con.close()

print(f"5. Parquet Store Synchronized: Total={tot:,}, Teams={teams_cnt:,}", flush=True)
