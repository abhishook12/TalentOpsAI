"""
TalentOpsAI Enterprise Intelligence Engine
Attaches the following enterprise fields directly to all 2,303,300 profiles:
1. seniority_level: Executive | Lead | Senior | Specialist | Campus
2. timezone: America/New_York | America/Chicago | America/Denver | America/Los_Angeles | America/Anchorage | America/Honolulu
3. timezone_code: ET | CT | MT | PT | AK | HT
4. company_scale: Enterprise | Mid-Market | Boutique
"""

import os
import time
import duckdb

PARQUET_FILE = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"
TEMP_PARQUET = r"C:\TalentOpsAI\backend\data\recruiters_enriched_temp.parquet"

print("=" * 80)
print(" STARTING ENTERPRISE INTELLIGENCE ENRICHMENT (2,303,300 PROFILES)")
print("=" * 80)

t0 = time.time()
con = duckdb.connect()

print("\n[Step 1/3] Computing Seniority, Timezone, and Company Scale in DuckDB...")

query = f"""
CREATE TABLE enriched_recruiters AS
WITH company_counts AS (
    SELECT company_id, COUNT(*) as comp_recruiter_count
    FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
    GROUP BY company_id
)
SELECT 
    r.*,
    -- 1. Seniority Level Classification
    CASE 
        WHEN regexp_matches(LOWER(COALESCE(r.title, '') || ' ' || COALESCE(r.specialization, '')), '\\b(head of|vp|vice president|chief|director|partner|cpo|chro|managing director)\\b') THEN 'Executive'
        WHEN regexp_matches(LOWER(COALESCE(r.title, '') || ' ' || COALESCE(r.specialization, '')), '\\b(lead|principal|staff|team lead|recruiting lead|sourcing lead|practice lead)\\b') THEN 'Lead'
        WHEN regexp_matches(LOWER(COALESCE(r.title, '') || ' ' || COALESCE(r.specialization, '')), '\\b(senior|sr\\b|sr\\.|advanced)\\b') THEN 'Senior'
        WHEN regexp_matches(LOWER(COALESCE(r.title, '') || ' ' || COALESCE(r.specialization, '')), '\\b(university|campus|college|emerging talent|intern|graduate|early career)\\b') THEN 'Campus'
        ELSE 'Specialist'
    END AS seniority_level,

    -- 2. Timezone Code
    CASE 
        WHEN UPPER(COALESCE(r.state, '')) IN ('CT', 'DC', 'DE', 'FL', 'GA', 'IN', 'KY', 'MA', 'MD', 'ME', 'MI', 'NC', 'NH', 'NJ', 'NY', 'OH', 'PA', 'RI', 'SC', 'VA', 'VT', 'WV') THEN 'ET'
        WHEN UPPER(COALESCE(r.state, '')) IN ('AL', 'AR', 'IA', 'IL', 'KS', 'LA', 'MN', 'MO', 'MS', 'ND', 'NE', 'OK', 'SD', 'TN', 'TX', 'WI') THEN 'CT'
        WHEN UPPER(COALESCE(r.state, '')) IN ('AZ', 'CO', 'ID', 'MT', 'NM', 'UT', 'WY') THEN 'MT'
        WHEN UPPER(COALESCE(r.state, '')) IN ('CA', 'NV', 'OR', 'WA') THEN 'PT'
        WHEN UPPER(COALESCE(r.state, '')) = 'AK' THEN 'AK'
        WHEN UPPER(COALESCE(r.state, '')) = 'HI' THEN 'HT'
        ELSE 'ET'
    END AS timezone_code,

    -- 3. IANA Timezone Identifier
    CASE 
        WHEN UPPER(COALESCE(r.state, '')) IN ('CT', 'DC', 'DE', 'FL', 'GA', 'IN', 'KY', 'MA', 'MD', 'ME', 'MI', 'NC', 'NH', 'NJ', 'NY', 'OH', 'PA', 'RI', 'SC', 'VA', 'VT', 'WV') THEN 'America/New_York'
        WHEN UPPER(COALESCE(r.state, '')) IN ('AL', 'AR', 'IA', 'IL', 'KS', 'LA', 'MN', 'MO', 'MS', 'ND', 'NE', 'OK', 'SD', 'TN', 'TX', 'WI') THEN 'America/Chicago'
        WHEN UPPER(COALESCE(r.state, '')) IN ('AZ', 'CO', 'ID', 'MT', 'NM', 'UT', 'WY') THEN 'America/Denver'
        WHEN UPPER(COALESCE(r.state, '')) IN ('CA', 'NV', 'OR', 'WA') THEN 'America/Los_Angeles'
        WHEN UPPER(COALESCE(r.state, '')) = 'AK' THEN 'America/Anchorage'
        WHEN UPPER(COALESCE(r.state, '')) = 'HI' THEN 'America/Honolulu'
        ELSE 'America/New_York'
    END AS timezone,

    -- 4. Company Scale Category
    CASE 
        WHEN COALESCE(c.comp_recruiter_count, 0) >= 500 THEN 'Enterprise'
        WHEN COALESCE(c.comp_recruiter_count, 0) >= 50 THEN 'Mid-Market'
        ELSE 'Boutique'
    END AS company_scale

FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}') r
LEFT JOIN company_counts c ON r.company_id = c.company_id
"""

con.execute(query)

print("\n[Step 2/3] Writing updated dataset to Parquet format (ZSTD compressed)...")
con.execute(f"COPY enriched_recruiters TO '{TEMP_PARQUET.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION ZSTD)")

print("\n[Step 3/3] Validating and swapping production parquet file...")
stats = con.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN seniority_level = 'Executive' THEN 1 END) as execs,
        COUNT(CASE WHEN seniority_level = 'Lead' THEN 1 END) as leads,
        COUNT(CASE WHEN seniority_level = 'Senior' THEN 1 END) as srs,
        COUNT(CASE WHEN seniority_level = 'Specialist' THEN 1 END) as specs,
        COUNT(CASE WHEN seniority_level = 'Campus' THEN 1 END) as campus,
        COUNT(CASE WHEN timezone_code = 'ET' THEN 1 END) as et_count,
        COUNT(CASE WHEN timezone_code = 'PT' THEN 1 END) as pt_count,
        COUNT(CASE WHEN company_scale = 'Enterprise' THEN 1 END) as enterprise_recs
    FROM enriched_recruiters
""").fetchone()

print(f"    - Total Profiles:       {stats[0]:,}")
print(f"    - Executives / Heads:   {stats[1]:,}")
print(f"    - Leads / Principals:   {stats[2]:,}")
print(f"    - Senior Recruiters:    {stats[3]:,}")
print(f"    - Specialists / TA:     {stats[4]:,}")
print(f"    - Campus / University:  {stats[5]:,}")
print(f"    - Eastern Timezone:     {stats[6]:,}")
print(f"    - Pacific Timezone:     {stats[7]:,}")
print(f"    - Enterprise Scale:     {stats[8]:,}")

con.close()

# Atomic swap
if os.path.exists(PARQUET_FILE):
    backup_file = PARQUET_FILE + ".bak"
    if os.path.exists(backup_file):
        os.remove(backup_file)
    os.rename(PARQUET_FILE, backup_file)
    os.rename(TEMP_PARQUET, PARQUET_FILE)
    if os.path.exists(backup_file):
        os.remove(backup_file)

print(f"\n>>> ENTERPRISE INTELLIGENCE ENRICHMENT COMPLETED IN {time.time() - t0:.2f}s!")
print("=" * 80)
