import duckdb
import os
import shutil
import time

t0 = time.time()
print("Starting fast domain unification in DuckDB...", flush=True)

con = duckdb.connect()

FREE_DOMAINS = (
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
)
free_sql = ", ".join(f"'{d}'" for d in FREE_DOMAINS)

PARQUET_FILE = 'backend/data/recruiters_full.parquet'
TEMP_PARQUET = 'backend/data/recruiters_unified_temp.parquet'

# 1. Native domain canonical table
print("Building native domain canonical table...", flush=True)
con.execute(f"""
    CREATE TABLE domain_canonical AS
    SELECT 
        LOWER(SPLIT_PART(email, '@', 2)) as domain,
        MODE(company_id) as canonical_cid
    FROM '{PARQUET_FILE}'
    WHERE email IS NOT NULL 
      AND email LIKE '%@%'
      AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql})
      AND company_id IS NOT NULL 
      AND TRIM(CAST(company_id AS VARCHAR)) != ''
      AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('need to fill data', 'unknown', 'n/a', 'none', 'null')
    GROUP BY domain
""")

c_count = con.execute("SELECT COUNT(*) FROM domain_canonical").fetchone()[0]
print(f"Computed canonical IDs for {c_count:,} corporate domains in {time.time()-t0:.2f}s", flush=True)

# 2. Write unified parquet
t1 = time.time()
print("Exporting unified Parquet...", flush=True)
con.execute(f"""
    COPY (
        SELECT 
            r.recruiter_id,
            r.recruiter_name,
            r.normalized_recruiter_name,
            r.email,
            r.phone,
            r.email2,
            r.phone2,
            r.email3,
            r.phone3,
            r.email4,
            r.phone4,
            r.alternate_emails,
            r.alternate_phones,
            r.linkedin,
            r.specialization,
            r.title,
            r.notes,
            r.review_reason,
            COALESCE(dc.canonical_cid, r.company_id) AS company_id,
            r.location,
            r.state,
            r.normalized_city,
            r.location_confidence,
            r.state_source,
            r.state_confidence,
            r.state_reason,
            r.last_scan_at,
            r.completeness_score,
            r.needs_review,
            r.is_active,
            r.data_source,
            r.trust_score,
            r.source_job_id,
            r.raw_data,
            r.metadata_json,
            r.tags,
            r.created_at,
            r.updated_at,
            r.taxonomy_category,
            r.report_count,
            r.email_status,
            r.email_confidence,
            r.email_source,
            r.email_pattern_id,
            r.email_generated,
            r.email_verified_at,
            r.email_last_checked_at,
            COALESCE(dc.canonical_cid, r.canonical_company_id, r.company_id) AS canonical_company_id,
            r.historical_company_id,
            r.company_domain_id,
            r.raw_email_value,
            r.repair_reason,
            r.user_id,
            r.quality_score,
            r.missing_fields,
            r.sentinel_status,
            r.last_verified_at,
            r.company_confidence,
            r.company_reasoning,
            r.is_archived,
            r.merged_into_id,
            r.logo_url,
            r.is_deliverable,
            r.seniority_level,
            r.timezone_code,
            r.timezone,
            r.company_scale
        FROM '{PARQUET_FILE}' r
        LEFT JOIN domain_canonical dc 
          ON LOWER(SPLIT_PART(r.email, '@', 2)) = dc.domain
         AND r.email LIKE '%@%'
    ) TO '{TEMP_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(f"Parquet generated in {time.time()-t1:.2f}s", flush=True)

if os.path.exists(TEMP_PARQUET):
    shutil.move(TEMP_PARQUET, PARQUET_FILE)
    print("Replaced main Parquet with unified Parquet.", flush=True)

# 3. Verification
t2 = time.time()
rht_rows = con.execute(f"""
    SELECT company_id, COUNT(*) as cnt, MIN(email) as sample_email
    FROM '{PARQUET_FILE}'
    WHERE email LIKE '%@rht.com'
    GROUP BY company_id
""").fetchall()

print("\n--- RHT.COM IN UNIFIED PARQUET ---", flush=True)
for r in rht_rows:
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
