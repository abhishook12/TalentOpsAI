import sys
import json
import re
import duckdb
from datetime import datetime

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal, engine, Base
from app.models.models import Company, Recruiter, DomainIntelligence
from sqlalchemy import text

print("=" * 80)
print("TALENTOPS DATA QUALITY ENGINE — PHASE 1 & 2: COMPREHENSIVE BASELINE PROFILE")
print("=" * 80)

# Ensure all database tables exist in PostgreSQL
try:
    Base.metadata.create_all(bind=engine)
    print("✓ Verified all PostgreSQL tables exist.")
except Exception as e:
    print(f"! Warning creating tables: {e}")

# Connect DuckDB to the Parquet dataset
con = duckdb.connect(':memory:')
con.execute('INSTALL httpfs; LOAD httpfs;')
url = "https://github.com/abhishook12/TalentOpsAI/releases/download/data-v1/recruiters_full.parquet"
con.execute(f"CREATE VIEW recruiters AS SELECT * FROM read_parquet('{url}')")

total_recruiters = con.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
print(f"\n[1] RECRUITER DATASET SIZE: {total_recruiters:,} records")

# ---------------------------------------------------------
# EMAIL METRICS
# ---------------------------------------------------------
print("\n--- Computing Email Quality Metrics ---")
email_metrics = con.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN email IS NULL OR TRIM(email) = '' OR email LIKE '%@missing.local%' THEN 1 END) as missing_email,
        COUNT(CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' 
                        AND regexp_matches(LOWER(TRIM(email)), '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$') THEN 1 END) as valid_syntax,
        COUNT(CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' 
                        AND NOT regexp_matches(LOWER(TRIM(email)), '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$') THEN 1 END) as malformed_syntax
    FROM recruiters
""").fetchone()

total_cnt, missing_email, valid_email, malformed_email = email_metrics

# Duplicate emails
dup_email_stats = con.execute("""
    WITH email_counts AS (
        SELECT LOWER(TRIM(email)) as em, COUNT(*) as cnt
        FROM recruiters
        WHERE email IS NOT NULL AND TRIM(email) != '' AND email NOT LIKE '%@missing.local%'
        GROUP BY em
    )
    SELECT
        COUNT(*) as unique_emails,
        COALESCE(SUM(CASE WHEN cnt > 1 THEN cnt ELSE 0 END), 0) as total_duplicate_rows,
        COUNT(CASE WHEN cnt > 1 THEN 1 END) as unique_duplicate_emails
    FROM email_counts
""").fetchone()
unique_emails, total_duplicate_rows, unique_dup_emails = dup_email_stats

# Free/Personal vs Business domains
free_domains = (
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
)
free_dom_sql = ", ".join(f"'{d}'" for d in free_domains)

domain_type_stats = con.execute(f"""
    SELECT
        COUNT(CASE WHEN LOWER(SPLIT_PART(email, '@', 2)) IN ({free_dom_sql}) THEN 1 END) as freemail_count,
        COUNT(CASE WHEN email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_dom_sql}) 
                        AND LENGTH(SPLIT_PART(email, '@', 2)) > 2 THEN 1 END) as business_email_count,
        COUNT(DISTINCT CASE WHEN email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_dom_sql}) 
                            THEN LOWER(SPLIT_PART(email, '@', 2)) END) as unique_business_domains
    FROM recruiters
    WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%'
""").fetchone()
freemail_count, business_email_count, unique_business_domains = domain_type_stats

# ---------------------------------------------------------
# NAME METRICS
# ---------------------------------------------------------
print("--- Computing Recruiter Name Quality Metrics ---")
name_stats = con.execute("""
    SELECT
        COUNT(CASE WHEN recruiter_name IS NULL OR TRIM(recruiter_name) = '' THEN 1 END) as missing_names,
        COUNT(CASE WHEN recruiter_name IS NOT NULL AND (
            LENGTH(TRIM(recruiter_name)) < 2 OR 
            regexp_matches(recruiter_name, '^[0-9+@._-]+$') OR
            LOWER(TRIM(recruiter_name)) IN ('recruiter', 'hr', 'admin', 'unknown', 'talent', 'hiring manager', 'n/a', 'none', 'null')
        ) THEN 1 END) as malformed_names,
        COUNT(CASE WHEN recruiter_name IS NOT NULL AND LENGTH(TRIM(recruiter_name)) >= 2 
                        AND NOT regexp_matches(recruiter_name, '^[0-9+@._-]+$')
                        AND LOWER(TRIM(recruiter_name)) NOT IN ('recruiter', 'hr', 'admin', 'unknown', 'talent', 'hiring manager', 'n/a', 'none', 'null')
              THEN 1 END) as valid_names
    FROM recruiters
""").fetchone()
missing_names, malformed_names, valid_names = name_stats

# ---------------------------------------------------------
# COMPANY ASSOCIATION METRICS
# ---------------------------------------------------------
print("--- Computing Company Association Metrics ---")
company_stats = con.execute("""
    SELECT
        COUNT(CASE WHEN company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' THEN 1 END) as missing_company,
        COUNT(CASE WHEN LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0') THEN 1 END) as unknown_company,
        COUNT(CASE WHEN company_id IS NOT NULL 
                        AND TRIM(CAST(company_id AS VARCHAR)) != '' 
                        AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0') 
              THEN 1 END) as mapped_company,
        COUNT(DISTINCT CASE WHEN company_id IS NOT NULL 
                                 AND TRIM(CAST(company_id AS VARCHAR)) != '' 
                                 AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0')
                            THEN CAST(company_id AS VARCHAR) END) as distinct_company_keys
    FROM recruiters
""").fetchone()
missing_company, unknown_company, mapped_company, distinct_company_keys = company_stats

# High Impact Opportunity: Recruiters with missing/unknown company BUT having a business email domain
company_repair_opportunity = con.execute(f"""
    SELECT COUNT(*) 
    FROM recruiters
    WHERE (company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' 
           OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0'))
      AND email LIKE '%@%'
      AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_dom_sql})
      AND LENGTH(SPLIT_PART(email, '@', 2)) > 2
""").fetchone()[0]

# ---------------------------------------------------------
# LOCATION & GEOGRAPHY METRICS
# ---------------------------------------------------------
print("--- Computing Location Quality Metrics ---")
location_stats = con.execute("""
    SELECT
        COUNT(CASE WHEN (location IS NULL OR TRIM(location) = '') 
                        AND (state IS NULL OR TRIM(state) = '') THEN 1 END) as completely_missing_location,
        COUNT(CASE WHEN (state IS NOT NULL AND TRIM(state) != '') 
                        AND (normalized_city IS NOT NULL AND TRIM(normalized_city) != '') THEN 1 END) as complete_location,
        COUNT(CASE WHEN (state IS NOT NULL AND TRIM(state) != '') 
                        AND (normalized_city IS NULL OR TRIM(normalized_city) = '') THEN 1 END) as state_only_location,
        COUNT(CASE WHEN state IS NOT NULL AND TRIM(state) != '' 
                        AND LENGTH(TRIM(state)) = 2 
                        AND UPPER(TRIM(state)) IN (
                            'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
                            'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
                            'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
                            'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
                            'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
                            'DC','PR','VI','GU','US'
                        ) THEN 1 END) as valid_us_state,
        COUNT(CASE WHEN state IS NOT NULL AND TRIM(state) != '' 
                        AND (LENGTH(TRIM(state)) != 2 OR UPPER(TRIM(state)) NOT IN (
                            'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
                            'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
                            'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
                            'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
                            'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
                            'DC','PR','VI','GU','US'
                        )) THEN 1 END) as non_standard_state
    FROM recruiters
""").fetchone()
missing_loc, complete_loc, state_only_loc, valid_us_state, non_standard_state = location_stats

# ---------------------------------------------------------
# PHONE, TITLE, SPECIALTY, LINKEDIN METRICS
# ---------------------------------------------------------
print("--- Computing Phone, Title & Profile Metrics ---")
profile_stats = con.execute("""
    SELECT
        COUNT(CASE WHEN phone IS NOT NULL AND TRIM(phone) != '' THEN 1 END) as with_phone,
        COUNT(CASE WHEN phone IS NULL OR TRIM(phone) = '' THEN 1 END) as missing_phone,
        COUNT(CASE WHEN title IS NOT NULL AND TRIM(title) != '' THEN 1 END) as with_title,
        COUNT(CASE WHEN title IS NULL OR TRIM(title) = '' THEN 1 END) as missing_title,
        COUNT(CASE WHEN specialization IS NOT NULL AND TRIM(specialization) != '' THEN 1 END) as with_specialization,
        COUNT(CASE WHEN specialization IS NULL OR TRIM(specialization) = '' THEN 1 END) as missing_specialization,
        COUNT(CASE WHEN linkedin IS NOT NULL AND TRIM(linkedin) != '' THEN 1 END) as with_linkedin,
        COUNT(CASE WHEN linkedin IS NULL OR TRIM(linkedin) = '' THEN 1 END) as missing_linkedin
    FROM recruiters
""").fetchone()
with_phone, missing_phone, with_title, missing_title, with_spec, missing_spec, with_li, missing_li = profile_stats

# ---------------------------------------------------------
# OVERALL QUALITY TIER DISTRIBUTION
# ---------------------------------------------------------
print("--- Computing Quality Score Distribution ---")
quality_tiers = con.execute(f"""
    WITH scored AS (
        SELECT
            (
                CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' THEN 25 ELSE 0 END +
                CASE WHEN email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_dom_sql}) THEN 10 ELSE 0 END +
                CASE WHEN recruiter_name IS NOT NULL AND LENGTH(TRIM(recruiter_name)) >= 2 THEN 20 ELSE 0 END +
                CASE WHEN company_id IS NOT NULL AND TRIM(CAST(company_id AS VARCHAR)) != '' 
                          AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0') THEN 20 ELSE 0 END +
                CASE WHEN state IS NOT NULL AND TRIM(state) != '' THEN 10 ELSE 0 END +
                CASE WHEN normalized_city IS NOT NULL AND TRIM(normalized_city) != '' THEN 5 ELSE 0 END +
                CASE WHEN phone IS NOT NULL AND TRIM(phone) != '' THEN 5 ELSE 0 END +
                CASE WHEN title IS NOT NULL AND TRIM(title) != '' THEN 5 ELSE 0 END
            ) as calc_score
        FROM recruiters
    )
    SELECT
        COUNT(CASE WHEN calc_score >= 80 THEN 1 END) as tier_high,
        COUNT(CASE WHEN calc_score >= 50 AND calc_score < 80 THEN 1 END) as tier_medium,
        COUNT(CASE WHEN calc_score >= 30 AND calc_score < 50 THEN 1 END) as tier_low,
        COUNT(CASE WHEN calc_score < 30 THEN 1 END) as tier_critical,
        ROUND(AVG(calc_score), 2) as avg_score
    FROM scored
""").fetchone()
tier_high, tier_medium, tier_low, tier_critical, avg_score = quality_tiers

# ---------------------------------------------------------
# POSTGRESQL COMPANIES AUDIT
# ---------------------------------------------------------
print("\n--- Computing PostgreSQL Companies Audit ---")
db = SessionLocal()
pg_comp_stats = db.execute(text("""
    SELECT
        COUNT(*) as total_companies,
        COUNT(CASE WHEN primary_domain IS NOT NULL AND primary_domain != '' THEN 1 END) as with_domain,
        COUNT(CASE WHEN primary_domain IS NULL OR primary_domain = '' THEN 1 END) as missing_domain,
        COUNT(CASE WHEN website IS NOT NULL AND website != '' THEN 1 END) as with_website,
        COUNT(CASE WHEN website IS NULL OR website = '' THEN 1 END) as missing_website,
        COUNT(CASE WHEN logo_url IS NOT NULL AND logo_url != '' THEN 1 END) as with_logo,
        COUNT(CASE WHEN logo_url IS NULL OR logo_url = '' THEN 1 END) as missing_logo,
        COUNT(CASE WHEN state IS NOT NULL AND state != '' THEN 1 END) as with_state,
        COUNT(CASE WHEN state IS NULL OR state = '' THEN 1 END) as missing_state
    FROM companies
""")).fetchone()
db.close()

pg_total, pg_with_dom, pg_missing_dom, pg_with_web, pg_missing_web, pg_with_logo, pg_missing_logo, pg_with_st, pg_missing_st = pg_comp_stats

# Compile Baseline Dict
baseline = {
    "generated_at": datetime.utcnow().isoformat(),
    "recruiters": {
        "total": total_recruiters,
        "email": {
            "valid_syntax": valid_email,
            "valid_syntax_pct": round(valid_email / total_recruiters * 100, 2),
            "malformed_syntax": malformed_email,
            "missing_or_placeholder": missing_email,
            "business_emails": business_email_count,
            "business_emails_pct": round(business_email_count / total_recruiters * 100, 2),
            "personal_or_freemail": freemail_count,
            "unique_business_domains": unique_business_domains,
            "unique_emails": unique_emails,
            "total_duplicate_email_rows": total_duplicate_rows,
            "unique_duplicate_emails": unique_dup_emails
        },
        "names": {
            "valid_names": valid_names,
            "valid_names_pct": round(valid_names / total_recruiters * 100, 2),
            "malformed_names": malformed_names,
            "missing_names": missing_names
        },
        "company_association": {
            "mapped_company": mapped_company,
            "mapped_company_pct": round(mapped_company / total_recruiters * 100, 2),
            "unknown_company": unknown_company,
            "missing_company": missing_company,
            "distinct_company_keys": distinct_company_keys,
            "repairable_via_email_domain": company_repair_opportunity
        },
        "location": {
            "complete_city_and_state": complete_loc,
            "state_only": state_only_loc,
            "missing_all_location": missing_loc,
            "valid_us_state": valid_us_state,
            "non_standard_state": non_standard_state
        },
        "profiles": {
            "with_phone": with_phone,
            "missing_phone": missing_phone,
            "with_title": with_title,
            "missing_title": missing_title,
            "with_specialization": with_spec,
            "missing_specialization": missing_spec,
            "with_linkedin": with_li,
            "missing_linkedin": missing_li
        },
        "quality_tiers": {
            "high_quality_80_plus": tier_high,
            "high_quality_pct": round(tier_high / total_recruiters * 100, 2),
            "medium_quality_50_79": tier_medium,
            "medium_quality_pct": round(tier_medium / total_recruiters * 100, 2),
            "low_quality_30_49": tier_low,
            "low_quality_pct": round(tier_low / total_recruiters * 100, 2),
            "critical_under_30": tier_critical,
            "critical_pct": round(tier_critical / total_recruiters * 100, 2),
            "database_avg_score": avg_score
        }
    },
    "companies_postgres": {
        "total": pg_total,
        "with_primary_domain": pg_with_dom,
        "missing_primary_domain": pg_missing_dom,
        "with_website": pg_with_web,
        "missing_website": pg_missing_web,
        "with_logo": pg_with_logo,
        "missing_logo": pg_missing_logo,
        "with_state": pg_with_st,
        "missing_state": pg_missing_st
    }
}

with open(r"C:\TalentOpsAI\DATA_QUALITY_BASELINE.json", "w") as f:
    json.dump(baseline, f, indent=2)

print("\n[SUCCESS] BASELINE PROFILE COMPILED AND SAVED TO C:\\TalentOpsAI\\DATA_QUALITY_BASELINE.json")
