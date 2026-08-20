import duckdb
import sys
import json
import time

sys.path.append('backend')
from app.database import SessionLocal
from app.models.models import Recruiter, Company, Candidate, Submission
from app.models.campaigns import Campaign

t0 = time.time()
print("="*80)
print("=== DEEP FORENSIC AUDIT OF TALENTOPS DB (POSTGRESQL + DUCKDB 2.3M PARQUET) ===")
print("="*80)

# ==========================================
# PART 1: DUCKDB PARQUET (2.3M MASTER STORE)
# ==========================================
con = duckdb.connect()
PARQUET = 'backend/data/recruiters_full.parquet'

total_parquet_rows = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}'").fetchone()[0]
print(f"\n[1] TOTAL PARQUET MASTER DATASET RECORDS: {total_parquet_rows:,}\n")

# A. Recruiter Name Anomalies
print("--- [A] RECRUITER NAME ANOMALIES ---")
# 1. Name is an email address
name_is_email = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_name LIKE '%@%'").fetchone()[0]
sample_name_is_email = con.execute(f"SELECT recruiter_id, recruiter_name, email FROM '{PARQUET}' WHERE recruiter_name LIKE '%@%' LIMIT 3").fetchall()
print(f"  A1. Name is an email address: {name_is_email:,} ({(name_is_email/total_parquet_rows)*100:.2f}%)")
for s in sample_name_is_email:
    print(f"      Example: ID={s[0]} | Name='{s[1]}' | Email='{s[2]}'")

# 2. Name is a phone number or numeric digits
name_is_digits = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE regexp_matches(recruiter_name, '^[0-9+() -]+$') AND LENGTH(recruiter_name) >= 6").fetchone()[0]
sample_name_is_digits = con.execute(f"SELECT recruiter_id, recruiter_name, email FROM '{PARQUET}' WHERE regexp_matches(recruiter_name, '^[0-9+() -]+$') AND LENGTH(recruiter_name) >= 6 LIMIT 3").fetchall()
print(f"  A2. Name is numeric / phone digits: {name_is_digits:,} ({(name_is_digits/total_parquet_rows)*100:.2f}%)")
for s in sample_name_is_digits:
    print(f"      Example: ID={s[0]} | Name='{s[1]}' | Email='{s[2]}'")

# 3. Name is NULL, empty, or placeholder ('Unknown', 'None', 'N/A')
name_is_empty = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_name IS NULL OR TRIM(recruiter_name) = '' OR LOWER(TRIM(recruiter_name)) IN ('unknown', 'none', 'n/a', 'null')").fetchone()[0]
print(f"  A3. Name is NULL / empty / placeholder: {name_is_empty:,} ({(name_is_empty/total_parquet_rows)*100:.2f}%)")

# 4. Truncated single first name only when email has first.last format
single_first_name = con.execute(f"""
    SELECT COUNT(*) FROM '{PARQUET}' 
    WHERE recruiter_name NOT LIKE '% %' 
      AND email LIKE '%.%@%'
      AND LENGTH(SPLIT_PART(SPLIT_PART(email, '@', 1), '.', 2)) >= 2
""").fetchone()[0]
sample_single_first = con.execute(f"""
    SELECT recruiter_id, recruiter_name, email FROM '{PARQUET}' 
    WHERE recruiter_name NOT LIKE '% %' 
      AND email LIKE '%.%@%'
      AND LENGTH(SPLIT_PART(SPLIT_PART(email, '@', 1), '.', 2)) >= 2
    LIMIT 3
""").fetchall()
print(f"  A4. Name is single first name only (recoverable from email): {single_first_name:,} ({(single_first_name/total_parquet_rows)*100:.2f}%)")
for s in sample_single_first:
    print(f"      Example: ID={s[0]} | Name='{s[1]}' | Email='{s[2]}'")

# B. Email Anomalies
print("\n--- [B] EMAIL FIELD ANOMALIES ---")
# 1. Email is NULL or empty
email_is_null = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE email IS NULL OR TRIM(email) = ''").fetchone()[0]
# 2. Email is NULL or empty but recruiter_name contains the email
email_in_name_field = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE (email IS NULL OR TRIM(email) = '') AND recruiter_name LIKE '%@%'").fetchone()[0]
print(f"  B1. Missing email column: {email_is_null:,} ({(email_is_null/total_parquet_rows)*100:.2f}%)")
print(f"  B2. Missing email BUT valid email exists in Name field: {email_in_name_field:,} ({(email_in_name_field/total_parquet_rows)*100:.2f}%)")

# 3. Malformed emails (missing @ or no domain dot)
malformed_emails = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE email IS NOT NULL AND TRIM(email) != '' AND (email NOT LIKE '%@%' OR SPLIT_PART(email, '@', 2) NOT LIKE '%.%')").fetchone()[0]
print(f"  B3. Malformed email values: {malformed_emails:,}")

# C. Duplicate Records Audit
print("\n--- [C] DUPLICATION & SCRAPING RESIDUE AUDIT ---")
# 1. Negative ID rows (raw scraping residue)
neg_ids = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_id < 0").fetchone()[0]
print(f"  C1. Negative Recruiter IDs (Scraper Duplicates): {neg_ids:,} ({(neg_ids/total_parquet_rows)*100:.2f}%)")

# 2. Duplicate rows by identical email address
dup_email_stats = con.execute(f"""
    SELECT 
        COUNT(*) as distinct_duplicated_emails,
        SUM(cnt) as total_rows_in_duplicate_sets
    FROM (
        SELECT LOWER(TRIM(email)) as em, COUNT(*) as cnt
        FROM '{PARQUET}'
        WHERE email IS NOT NULL AND email LIKE '%@%'
        GROUP BY LOWER(TRIM(email))
        HAVING COUNT(*) > 1
    )
""").fetchone()
print(f"  C2. Distinct Emails with Duplicate Profiles: {dup_email_stats[0]:,}")
print(f"      -> Total Duplicate Rows Created: {dup_email_stats[1]:,} rows")

# 3. Exact identical name + email + company + phone duplicates
exact_full_dups = con.execute(f"""
    SELECT COUNT(*) - COUNT(DISTINCT (COALESCE(LOWER(email),'') || '|' || COALESCE(LOWER(recruiter_name),'') || '|' || COALESCE(CAST(company_id AS VARCHAR),'') || '|' || COALESCE(phone,'')))
    FROM '{PARQUET}'
""").fetchone()[0]
print(f"  C3. Exact Identical Tuple Duplicates (Name+Email+Company+Phone): {exact_full_dups:,} duplicate rows")

# D. Phone Field Anomalies
print("\n--- [D] PHONE FIELD ANOMALIES ---")
phone_is_email = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE phone LIKE '%@%'").fetchone()[0]
phone_has_letters = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE phone IS NOT NULL AND regexp_matches(phone, '[a-zA-Z]')").fetchone()[0]
phone_valid = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE phone IS NOT NULL AND TRIM(phone) != ''").fetchone()[0]
print(f"  D1. Valid Phone numbers present: {phone_valid:,} ({(phone_valid/total_parquet_rows)*100:.2f}%)")
print(f"  D2. Phone field containing email address: {phone_is_email:,}")
print(f"  D3. Phone field containing letters/words: {phone_has_letters:,}")

# E. Location / State Anomalies
print("\n--- [E] LOCATION & STATE ANOMALIES ---")
missing_state = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE state IS NULL OR TRIM(state) = '' OR LENGTH(TRIM(state)) != 2").fetchone()[0]
missing_location = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE location IS NULL OR TRIM(location) = ''").fetchone()[0]
print(f"  E1. Missing / Invalid 2-letter US State: {missing_state:,} ({(missing_state/total_parquet_rows)*100:.2f}%)")
print(f"  E2. Missing Location string: {missing_location:,} ({(missing_location/total_parquet_rows)*100:.2f}%)")

# ==========================================
# PART 2: POSTGRESQL DATABASE AUDIT
# ==========================================
print("\n" + "="*80)
print("=== [PART 2]: POSTGRESQL RELATIONAL TABLES AUDIT ===")
print("="*80)

db = SessionLocal()
try:
    pg_recs = db.query(Recruiter).count()
    pg_comps = db.query(Company).count()
    pg_camps = db.query(Campaign).count()
    pg_cands = db.query(Candidate).count()
    pg_subs = db.query(Submission).count()
    print(f"PostgreSQL Table Counts:")
    print(f"  - Recruiters (PostgreSQL Cache): {pg_recs:,}")
    print(f"  - Companies: {pg_comps:,}")
    print(f"  - Campaigns: {pg_camps:,}")
    print(f"  - Candidates: {pg_cands:,}")
    print(f"  - Submissions: {pg_subs:,}")
    
    # Check for empty company names in PG
    pg_comp_empty_names = db.query(Company).filter((Company.company_name == None) | (Company.company_name == '')).count()
    pg_comp_empty_domains = db.query(Company).filter((Company.primary_domain == None) | (Company.primary_domain == '')).count()
    print(f"\nPostgreSQL Companies Quality:")
    print(f"  - Companies with missing names: {pg_comp_empty_names}")
    print(f"  - Companies with missing primary domains: {pg_comp_empty_domains}")
finally:
    db.close()

print(f"\nDeep forensic DB audit completed in {time.time()-t0:.2f}s")
print("="*80)
