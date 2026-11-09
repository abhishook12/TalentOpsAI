import sys, os, json, re
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

print("1. Finalizing Brandon Ochoa and cleaning remaining placeholders in PostgreSQL...")
conn = psycopg.connect(DB_URL)
with conn.cursor() as cur:
    # 1. Get or create Progressive company
    cur.execute("SELECT company_id FROM companies WHERE company_name ILIKE 'Progressive%' OR website ILIKE '%progressive.com%' LIMIT 1;")
    row = cur.fetchone()
    if row:
        prog_comp_id = row[0]
    else:
        cur.execute("INSERT INTO companies (company_name, canonical_name, website, is_active, data_source) VALUES ('Progressive', 'Progressive', 'https://www.progressive.com', true, 'teams') RETURNING company_id;")
        prog_comp_id = cur.fetchone()[0]
        
    # Check if Brandon Ochoa with brandon_ochoa@progressive.com exists
    cur.execute("SELECT recruiter_id FROM recruiters WHERE email = 'brandon_ochoa@progressive.com';")
    b_row = cur.fetchone()
    if not b_row:
        print("   Inserting dedicated Brandon Ochoa record...")
        cur.execute("""
            INSERT INTO recruiters (
                recruiter_name, title, location, company_id,
                email, email2, email3,
                phone, phone2, phone3,
                data_source, is_active
            ) VALUES (
                'Brandon Ochoa', 'Technical Recruiter', 'United States', %s,
                'brandon_ochoa@progressive.com', 'bochoa@att.com', 'brandertots@hotmail.com',
                '+1 (254) 339-6765', '+1 (254) 339-6766', '+1 (254) 252-7415',
                'teams', true
            ) RETURNING recruiter_id;
        """, (prog_comp_id,))
        new_b_id = cur.fetchone()[0]
        print(f"   Created Brandon Ochoa with ID={new_b_id}")
    else:
        print(f"   Brandon Ochoa exists with ID={b_row[0]}, ensuring accurate phones and company...")
        cur.execute("""
            UPDATE recruiters SET
                recruiter_name = 'Brandon Ochoa',
                company_id = %s,
                phone = '+1 (254) 339-6765',
                phone2 = '+1 (254) 339-6766',
                phone3 = '+1 (254) 252-7415',
                phone4 = NULL,
                alternate_phones = NULL,
                email2 = 'bochoa@att.com',
                email3 = 'brandertots@hotmail.com',
                email4 = NULL,
                alternate_emails = NULL
            WHERE recruiter_id = %s;
        """, (prog_comp_id, b_row[0]))

    # 2. Fix remaining 20 Teams Candidate placeholders
    cur.execute("SELECT recruiter_id, email, phone FROM recruiters WHERE recruiter_name ILIKE '%Teams Candidate%';")
    placeholders = cur.fetchall()
    for rid, em, ph in placeholders:
        if em:
            user = em.split("@")[0]
            user_clean = re.sub(r"\d+$", "", user)
            parts = re.split(r"[._-]+", user_clean)
            if len(parts) >= 2:
                name_fix = " ".join(p.capitalize() for p in parts[:2])
            else:
                name_fix = parts[0].capitalize()
        elif ph:
            name_fix = f"Candidate ({ph})"
        else:
            name_fix = "Technical Sourcing Specialist"
            
        cur.execute("UPDATE recruiters SET recruiter_name = %s WHERE recruiter_id = %s;", (name_fix, rid))
        
    conn.commit()
    print("   All placeholder records updated successfully.")
conn.close()

# 3. Synchronize Parquet with PostgreSQL
print("2. Synchronizing Parquet with live PostgreSQL...")
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

pg_conn = psycopg.connect(DB_URL)
cur = pg_conn.cursor()

pg_cols = parquet_columns.copy()
pg_cols[pg_cols.index('is_archived')] = 'false AS is_archived'

query = f"SELECT {', '.join(pg_cols)} FROM recruiters"
cur.execute(query)
rows = cur.fetchall()
pg_conn.close()

print(f"   Fetched {len(rows)} authoritative records from PostgreSQL.", flush=True)
pg_df = pd.DataFrame(rows, columns=parquet_columns)

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
cand_check = con.execute(f"SELECT count(*) FROM read_parquet('{PARQUET_PATH}') WHERE recruiter_name ILIKE '%Teams Candidate%'").fetchone()[0]
con.close()

print(f"5. Parquet Store Synchronized: Total={tot:,}, Teams={teams_cnt:,}, Teams Candidate Placeholders={cand_check}")
