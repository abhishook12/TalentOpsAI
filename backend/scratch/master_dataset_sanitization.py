import duckdb
import os
import shutil
import time
import re

t0 = time.time()
print("="*80)
print("=== STARTING MASTER DATASET REPAIR & SANITIZATION PIPELINE ===")
print("="*80)

PARQUET_FILE = 'backend/data/recruiters_full.parquet'
TEMP_PARQUET = 'backend/data/recruiters_sanitized_temp.parquet'

con = duckdb.connect()
con.execute("PRAGMA threads=8;")
con.execute("PRAGMA memory_limit='6GB';")

print("1. Loading raw dataset into in-memory table...", flush=True)
con.execute(f"CREATE TABLE raw_rec AS SELECT * FROM '{PARQUET_FILE}'")
total_raw = con.execute("SELECT COUNT(*) FROM raw_rec").fetchone()[0]
print(f"   Loaded {total_raw:,} records in {time.time()-t0:.2f}s", flush=True)

# 2. Extract email from recruiter_name when email is empty/None
print("2. Extracting emails and phones from name fields...", flush=True)
con.execute("""
    -- 2a. If email is null/empty and name contains email, extract it
    UPDATE raw_rec
    SET email = LOWER(regexp_extract(recruiter_name, '([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})', 1))
    WHERE (email IS NULL OR TRIM(email) = '' OR LOWER(email) = 'none')
      AND recruiter_name LIKE '%@%'
      AND regexp_matches(recruiter_name, '([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})');
""")

# 2b. Extract phone from name if phone is empty
con.execute("""
    UPDATE raw_rec
    SET phone = regexp_extract(recruiter_name, '(\\+?[0-9]{1,3}[- .]?\\(?[0-9]{3}\\)?[- .]?[0-9]{3}[- .]?[0-9]{4})', 1)
    WHERE (phone IS NULL OR TRIM(phone) = '')
      AND regexp_matches(recruiter_name, '(\\+?[0-9]{1,3}[- .]?\\(?[0-9]{3}\\)?[- .]?[0-9]{3}[- .]?[0-9]{4})');
""")

# 3. Clean and reconstruct recruiter_name
print("3. Reconstructing and normalizing recruiter names...", flush=True)

# Helper: name from email prefix (e.g. 'first.last' -> 'First Last')
con.execute("""
    CREATE OR REPLACE MACRO email_to_name(em) AS (
        CASE 
            WHEN em IS NOT NULL AND em LIKE '%@%' THEN
                -- check if prefix has dot, hyphen, or underscore
                CASE 
                    WHEN SPLIT_PART(em, '@', 1) LIKE '%.%' THEN
                        UPPER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '.', 1), 1, 1)) || 
                        LOWER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '.', 1), 2)) || ' ' ||
                        UPPER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '.', 2), 1, 1)) || 
                        LOWER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '.', 2), 2))
                    WHEN SPLIT_PART(em, '@', 1) LIKE '%_%' THEN
                        UPPER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '_', 1), 1, 1)) || 
                        LOWER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '_', 1), 2)) || ' ' ||
                        UPPER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '_', 2), 1, 1)) || 
                        LOWER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '_', 2), 2))
                    WHEN SPLIT_PART(em, '@', 1) LIKE '%-%' THEN
                        UPPER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '-', 1), 1, 1)) || 
                        LOWER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '-', 1), 2)) || ' ' ||
                        UPPER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '-', 2), 1, 1)) || 
                        LOWER(SUBSTRING(SPLIT_PART(SPLIT_PART(em, '@', 1), '-', 2), 2))
                    ELSE
                        UPPER(SUBSTRING(SPLIT_PART(em, '@', 1), 1, 1)) || 
                        LOWER(SUBSTRING(SPLIT_PART(em, '@', 1), 2))
                END
            ELSE 'Unknown Recruiter'
        END
    );
""")

# 3a. When recruiter_name is email, phone digits, empty/placeholder, or equal to company/domain, reconstruct from email
con.execute("""
    UPDATE raw_rec
    SET recruiter_name = email_to_name(email)
    WHERE recruiter_name IS NULL 
       OR TRIM(recruiter_name) = ''
       OR recruiter_name LIKE '%@%'
       OR regexp_matches(recruiter_name, '^[0-9+() -]+$')
       OR LOWER(TRIM(recruiter_name)) IN ('unknown', 'none', 'n/a', 'null')
       OR (email IS NOT NULL AND email LIKE '%@%' AND LOWER(TRIM(recruiter_name)) = LOWER(SPLIT_PART(SPLIT_PART(email, '@', 2), '.', 1)))
       OR (email IS NOT NULL AND email LIKE '%@%' AND LOWER(TRIM(recruiter_name)) IN ('staffing', 'recruiting', 'technologies', 'solutions', 'consulting', 'services', 'group', 'partners'));
""")

# 3b. When recruiter_name is single first name only and email has first.last format, expand to full name
con.execute("""
    UPDATE raw_rec
    SET recruiter_name = email_to_name(email)
    WHERE recruiter_name NOT LIKE '% %'
      AND email LIKE '%.%@%'
      AND LENGTH(SPLIT_PART(SPLIT_PART(email, '@', 1), '.', 2)) >= 2;
""")

# 3c. Clean trailing/leading spaces and punctuation in names
con.execute("""
    UPDATE raw_rec
    SET recruiter_name = TRIM(REGEXP_REPLACE(recruiter_name, '[\\s]+', ' '))
    WHERE recruiter_name IS NOT NULL;
""")

# 4. Master Deduplication (Consolidate into 1 Master Record per Unique Person)
print("4. Consolidating duplicate profiles into unified master records...", flush=True)

# For deduplication, assign positive clean ID and pick best non-null fields
con.execute("""
    CREATE TABLE deduplicated_rec AS
    WITH ranked AS (
        SELECT 
            *,
            -- Generate a deduplication key (lowercase email if present, else name+company+state)
            CASE 
                WHEN email IS NOT NULL AND TRIM(email) != '' AND email LIKE '%@%' THEN 'EM:' || LOWER(TRIM(email))
                ELSE 'NSC:' || LOWER(COALESCE(recruiter_name,'')) || '|' || COALESCE(CAST(company_id AS VARCHAR),'') || '|' || COALESCE(state,'')
            END AS dedup_key,
            -- Score record richness (positive ID preferred, phone present, linkedin present, full name)
            (
                (CASE WHEN recruiter_id > 0 THEN 100 ELSE 0 END) +
                (CASE WHEN phone IS NOT NULL AND TRIM(phone) != '' THEN 50 ELSE 0 END) +
                (CASE WHEN linkedin IS NOT NULL AND TRIM(linkedin) != '' THEN 30 ELSE 0 END) +
                (CASE WHEN location IS NOT NULL AND TRIM(location) != '' THEN 20 ELSE 0 END) +
                (CASE WHEN title IS NOT NULL AND TRIM(title) != '' THEN 10 ELSE 0 END)
            ) AS richness_score,
            ROW_NUMBER() OVER (
                PARTITION BY 
                    CASE 
                        WHEN email IS NOT NULL AND TRIM(email) != '' AND email LIKE '%@%' THEN 'EM:' || LOWER(TRIM(email))
                        ELSE 'NSC:' || LOWER(COALESCE(recruiter_name,'')) || '|' || COALESCE(CAST(company_id AS VARCHAR),'') || '|' || COALESCE(state,'')
                    END
                ORDER BY 
                    (CASE WHEN recruiter_id > 0 THEN 100 ELSE 0 END) +
                    (CASE WHEN phone IS NOT NULL AND TRIM(phone) != '' THEN 50 ELSE 0 END) +
                    (CASE WHEN linkedin IS NOT NULL AND TRIM(linkedin) != '' THEN 30 ELSE 0 END) +
                    (CASE WHEN location IS NOT NULL AND TRIM(location) != '' THEN 20 ELSE 0 END) +
                    (CASE WHEN title IS NOT NULL AND TRIM(title) != '' THEN 10 ELSE 0 END) DESC,
                    recruiter_id DESC
            ) as rn
        FROM raw_rec
    )
    SELECT 
        * EXCLUDE (dedup_key, richness_score, rn)
    FROM ranked
    WHERE rn = 1;
""")

# Convert any remaining negative recruiter_id to clean positive sequence ID
con.execute("""
    CREATE SEQUENCE IF NOT EXISTS clean_rec_id_seq START 3000000;
    UPDATE deduplicated_rec
    SET recruiter_id = nextval('clean_rec_id_seq')
    WHERE recruiter_id < 0;
""")

final_count = con.execute("SELECT COUNT(*) FROM deduplicated_rec").fetchone()[0]
print(f"   Deduplicated dataset: {final_count:,} unique clean recruiter profiles (from {total_raw:,} raw rows)", flush=True)

# 5. Export clean compressed Parquet
print("5. Writing optimized master Parquet file...", flush=True)
con.execute(f"""
    COPY deduplicated_rec TO '{TEMP_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD);
""")
print(f"   Parquet written in {time.time()-t0:.2f}s", flush=True)

# Swap Parquet file
if os.path.exists(TEMP_PARQUET) and os.path.getsize(TEMP_PARQUET) > 10_000_000:
    shutil.move(TEMP_PARQUET, PARQUET_FILE)
    print("   Successfully replaced master Parquet file with clean dataset!", flush=True)
else:
    print("   Error: Output parquet file invalid.", flush=True)

print("="*80)
print(f"=== MASTER DATASET REPAIR COMPLETE IN {time.time()-t0:.2f}s ===")
print("="*80)
