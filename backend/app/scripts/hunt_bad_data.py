"""
Comprehensive Bad Data Forensics Hunter
=======================================
Deeply scans all datasets across:
1. Parquet Master Catalog (444k records)
2. PostgreSQL CRM Tables (recruiters, companies, discovery_staging)

Checks:
- Garbage/Noise Names (e.g. 'LinkedIn Member', email as name, emojis, numbers)
- Garbage/UI Noise Titles (e.g. 'View Profile', 'Connect', 'Message', HTML tags)
- Malformed & Generic Emails (e.g. info@, support@, admin@, double dots, bad TLDs)
- Garbage/Noise Companies (e.g. 'LinkedIn', 'Google', URLs, 'N/A', 'Unknown', single chars)
- Dummy/Fake Phone Numbers (e.g. 1234567890, 0000000000, 555-...)
- Invalid/Malformed States & Locations
- Broken / Generic LinkedIn URLs
- Duplicates & Anomalies
"""

import os
import sys
import re
import duckdb
from typing import Dict, Any, List

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

from app.database import SessionLocal
from sqlalchemy import text

US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}

GENERIC_EMAIL_PREFIXES = [
    'info', 'support', 'sales', 'admin', 'contact', 'careers', 'jobs', 
    'recruiting', 'hr', 'billing', 'help', 'team', 'service', 'office',
    'mail', 'marketing', 'press', 'inquiry', 'general', 'feedback', 'noreply', 'no-reply'
]

GARBAGE_COMPANY_TERMS = [
    'linkedin', 'google', 'facebook', 'twitter', 'instagram', 'unknown',
    'n/a', 'na', 'none', 'null', 'missing', 'missing.local', 'independent staffing',
    'self employed', 'freelance', 'contractor', 'stealth', 'confidential',
    'self-employed', 'freelancer', 'various', 'anonymous', 'unemployed'
]

GARBAGE_NAME_TERMS = [
    'linkedin member', 'unknown', 'user', 'admin', 'recruiter', 'talent',
    'candidate', 'null', 'none', 'n/a', 'na', 'test', 'dummy', 'profile'
]

UI_ACTION_WORDS = [
    'connect', 'message', 'view profile', 'follow', 'pending', 'more info',
    'contact info', 'see more', 'full profile', 'send inmail'
]

DUMMY_PHONE_PATTERNS = [
    r'^[01]{7,15}$',
    r'^(.)\1{6,}$',
    r'^12345',
    r'^555',
    r'^(\+?1[-.\s]?)?\(?555\)?[-.\s]?555[-.\s]?\d{4}$',
]


def scan_parquet_bad_data():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print("\n" + "="*70)
    print("1. SCANNING PARQUET MASTER CATALOG FOR BAD DATA (444,529 Records)")
    print("="*70)

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    total = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Total rows inspected: {total:,}")

    findings = {}

    # 1. Names
    name_noise_terms_sql = ", ".join(f"'{t}'" for t in GARBAGE_NAME_TERMS)
    bad_names = con.execute(f"""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NULL 
           OR TRIM(recruiter_name) = ''
           OR LENGTH(TRIM(recruiter_name)) < 2
           OR LOWER(TRIM(recruiter_name)) IN ({name_noise_terms_sql})
           OR recruiter_name LIKE '%@%'
           OR recruiter_name LIKE 'http%'
           OR REGEXP_MATCHES(recruiter_name, '^[0-9\\s\\-\\+\\(\\)]+$')
    """).fetchone()[0]
    findings["bad_names"] = bad_names
    print(f"\n[A] Recruiter Names:")
    print(f"    • Bad / Noise Names: {bad_names:,}")
    if bad_names > 0:
        samples = con.execute(f"""
            SELECT recruiter_name, email FROM rec
            WHERE recruiter_name IS NULL 
               OR TRIM(recruiter_name) = ''
               OR LENGTH(TRIM(recruiter_name)) < 2
               OR LOWER(TRIM(recruiter_name)) IN ({name_noise_terms_sql})
               OR recruiter_name LIKE '%@%'
               OR recruiter_name LIKE 'http%'
               OR REGEXP_MATCHES(recruiter_name, '^[0-9\\s\\-\\+\\(\\)]+$')
            LIMIT 5
        """).fetchall()
        print(f"      Samples: {samples}")

    # 2. Titles / Job Roles
    bad_titles = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE title IS NOT NULL 
          AND (
            LOWER(title) LIKE '%view profile%'
            OR LOWER(title) LIKE '%connect%'
            OR LOWER(title) LIKE '%message%'
            OR LOWER(title) LIKE '%see more%'
            OR title LIKE '%<%>%'
            OR LENGTH(TRIM(title)) < 2
          )
    """).fetchone()[0]
    findings["bad_titles"] = bad_titles
    print(f"\n[B] Job Titles:")
    print(f"    • UI Action Noise in Titles: {bad_titles:,}")
    if bad_titles > 0:
        samples = con.execute("""
            SELECT title FROM rec
            WHERE title IS NOT NULL 
              AND (
                LOWER(title) LIKE '%view profile%'
                OR LOWER(title) LIKE '%connect%'
                OR LOWER(title) LIKE '%message%'
                OR title LIKE '%<%>%'
              )
            LIMIT 5
        """).fetchall()
        print(f"      Samples: {samples}")

    # 3. Emails
    bad_emails = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE email IS NOT NULL 
          AND (
            email NOT LIKE '%@%.%'
            OR email LIKE '%..%'
            OR email LIKE '%@%@%'
            OR email LIKE '%.local'
            OR email LIKE '%example.com'
            OR email LIKE '%test.com'
            OR email LIKE '%dummy%'
            OR email LIKE '%@unknown%'
          )
    """).fetchone()[0]

    generic_prefixes_sql = ", ".join(f"'{p}'" for p in GENERIC_EMAIL_PREFIXES)
    role_based_emails = con.execute(f"""
        SELECT COUNT(*) FROM rec
        WHERE email IS NOT NULL 
          AND LOWER(SPLIT_PART(email, '@', 1)) IN ({generic_prefixes_sql})
    """).fetchone()[0]

    findings["bad_emails"] = bad_emails
    findings["role_based_emails"] = role_based_emails
    print(f"\n[C] Emails:")
    print(f"    • Malformed / Dummy Emails: {bad_emails:,}")
    if bad_emails > 0:
        samples = con.execute("""
            SELECT recruiter_name, email, company_id FROM rec
            WHERE email IS NOT NULL 
              AND (
                email NOT LIKE '%@%.%'
                OR email LIKE '%..%'
                OR email LIKE '%@%@%'
                OR email LIKE '%.local'
                OR email LIKE '%example.com'
                OR email LIKE '%test.com'
                OR email LIKE '%dummy%'
                OR email LIKE '%@unknown%'
              )
            LIMIT 10
        """).fetchall()
        print(f"      Samples: {samples}")
    print(f"    • Generic / Role-Based Emails (e.g. info@, sales@, hr@): {role_based_emails:,}")

    # 4. Companies
    noise_comps_sql = ", ".join(f"'{c}'" for c in GARBAGE_COMPANY_TERMS)
    bad_companies = con.execute(f"""
        SELECT COUNT(*) FROM rec
        WHERE company_id IS NULL 
           OR TRIM(CAST(company_id AS VARCHAR)) = ''
           OR LENGTH(TRIM(CAST(company_id AS VARCHAR))) < 2
           OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ({noise_comps_sql})
           OR CAST(company_id AS VARCHAR) LIKE 'http%'
           OR CAST(company_id AS VARCHAR) LIKE '%@%'
    """).fetchone()[0]
    findings["bad_companies"] = bad_companies
    print(f"\n[D] Companies:")
    print(f"    • Missing or Platform Noise Companies: {bad_companies:,}")
    if bad_companies > 0:
        samples = con.execute(f"""
            SELECT company_id, email FROM rec
            WHERE company_id IS NULL 
               OR TRIM(CAST(company_id AS VARCHAR)) = ''
               OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ({noise_comps_sql})
            LIMIT 5
        """).fetchall()
        print(f"      Samples: {samples}")

    # 5. Phones
    bad_phones = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE phone IS NOT NULL 
          AND TRIM(phone) != ''
          AND (
            REGEXP_MATCHES(REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', ''), '^[01]{7,15}$')
            OR REPLACE(REPLACE(phone, '-', ''), ' ', '') LIKE '12345%'
            OR REPLACE(REPLACE(phone, '-', ''), ' ', '') LIKE '00000%'
            OR REPLACE(REPLACE(phone, '-', ''), ' ', '') LIKE '99999%'
            OR phone LIKE '%555-555%'
          )
    """).fetchone()[0]
    findings["bad_phones"] = bad_phones
    print(f"\n[E] Phone Numbers:")
    print(f"    • Dummy / Repeated Phone Numbers: {bad_phones:,}")
    if bad_phones > 0:
        samples = con.execute("""
            SELECT phone, recruiter_name FROM rec
            WHERE phone IS NOT NULL 
              AND TRIM(phone) != ''
              AND (
                REGEXP_MATCHES(REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', ''), '^[01]{7,15}$')
                OR REPLACE(REPLACE(phone, '-', ''), ' ', '') LIKE '12345%'
                OR phone LIKE '%555-555%'
              )
            LIMIT 5
        """).fetchall()
        print(f"      Samples: {samples}")

    # 6. Geographic States
    valid_states_sql = ", ".join(f"'{s}'" for s in US_STATES)
    bad_states = con.execute(f"""
        SELECT COUNT(*) FROM rec
        WHERE state IS NOT NULL 
          AND TRIM(CAST(state AS VARCHAR)) != ''
          AND UPPER(TRIM(CAST(state AS VARCHAR))) != 'US'
          AND UPPER(TRIM(CAST(state AS VARCHAR))) NOT IN ({valid_states_sql})
    """).fetchone()[0]
    findings["bad_states"] = bad_states
    print(f"\n[F] Geographic States:")
    print(f"    • Invalid State Codes (not in US States): {bad_states:,}")
    if bad_states > 0:
        samples = con.execute(f"""
            SELECT DISTINCT state FROM rec
            WHERE state IS NOT NULL 
              AND UPPER(TRIM(CAST(state AS VARCHAR))) != 'US'
              AND UPPER(TRIM(CAST(state AS VARCHAR))) NOT IN ({valid_states_sql})
            LIMIT 10
        """).fetchall()
        print(f"      Samples: {samples}")

    # 7. LinkedIn URLs
    bad_linkedin = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE linkedin IS NOT NULL 
          AND TRIM(linkedin) != ''
          AND (
            TRIM(linkedin) IN ('https://www.linkedin.com', 'https://www.linkedin.com/', 'https://linkedin.com', 'https://linkedin.com/')
            OR TRIM(linkedin) = 'https://www.linkedin.com/in/'
            OR linkedin NOT LIKE '%linkedin.com/in/%'
          )
    """).fetchone()[0]
    findings["bad_linkedin"] = bad_linkedin
    print(f"\n[G] LinkedIn URLs:")
    print(f"    • Broken / Generic LinkedIn Profile URLs: {bad_linkedin:,}")

    # 8. Duplicate Emails
    dup_emails = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT email, COUNT(*) as cnt 
            FROM rec 
            WHERE email IS NOT NULL AND TRIM(email) != '' 
            GROUP BY email 
            HAVING cnt > 1
        )
    """).fetchone()[0]
    findings["dup_emails"] = dup_emails
    print(f"\n[H] Duplicate Emails:")
    print(f"    • Distinct Duplicate Email Addresses: {dup_emails:,}")

    return findings


def scan_postgresql_bad_data():
    print("\n" + "="*70)
    print("2. SCANNING POSTGRESQL TABLES FOR BAD DATA")
    print("="*70)

    with SessionLocal() as db:
        # Recruiters CRM
        r_total = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
        print(f"Total PostgreSQL Recruiters: {r_total:,}")
        
        # Check bad recruiter names
        r_bad_names = db.execute(text("""
            SELECT COUNT(*) FROM recruiters
            WHERE recruiter_name IS NULL 
               OR LENGTH(TRIM(recruiter_name)) < 2
               OR LOWER(TRIM(recruiter_name)) IN ('linkedin member', 'unknown', 'user', 'admin')
               OR recruiter_name LIKE '%@%'
        """)).scalar()

        # Check bad emails
        r_bad_emails = db.execute(text("""
            SELECT COUNT(*) FROM recruiters
            WHERE email IS NULL 
               OR email NOT LIKE '%@%.%'
               OR email LIKE '%..%'
               OR LOWER(email) LIKE '%@unknown.com%'
               OR LOWER(email) LIKE '%@noemail%'
        """)).scalar()

        # Check duplicate emails
        r_dup_emails = db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT email, COUNT(*) as cnt FROM recruiters WHERE email IS NOT NULL GROUP BY email HAVING count(*) > 1
            ) s
        """)).scalar()

        # Check unlinked recruiters
        r_unlinked = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NULL")).scalar()

        print(f"  • Bad/Noise Names: {r_bad_names:,}")
        print(f"  • Bad/Malformed Emails: {r_bad_emails:,}")
        print(f"  • Duplicate Emails: {r_dup_emails:,}")
        print(f"  • Unlinked to Company: {r_unlinked:,}")

        # Companies CRM
        c_total = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        print(f"\nTotal PostgreSQL Companies: {c_total:,}")

        c_bad_names = db.execute(text("""
            SELECT COUNT(*) FROM companies
            WHERE company_name IS NULL 
               OR LENGTH(TRIM(company_name)) < 2
               OR LOWER(TRIM(company_name)) IN ('linkedin', 'google', 'facebook', 'unknown', 'n/a', 'na')
        """)).scalar()

        c_bad_websites = db.execute(text("""
            SELECT COUNT(*) FROM companies
            WHERE website IS NOT NULL 
              AND website != ''
              AND (website NOT LIKE 'http%' OR website NOT LIKE '%.%')
        """)).scalar()

        print(f"  • Noise/Garbage Company Names: {c_bad_names:,}")
        print(f"  • Malformed Websites: {c_bad_websites:,}")

        # Discovery Staging Table
        ds_total = db.execute(text("SELECT COUNT(*) FROM discovery_staging")).scalar()
        print(f"\nTotal Discovery Staging Records: {ds_total:,}")

        ds_noise_company = db.execute(text("""
            SELECT COUNT(*) FROM discovery_staging
            WHERE raw_company IS NOT NULL 
              AND LOWER(TRIM(raw_company)) IN ('linkedin', 'google', 'facebook', 'twitter', 'unknown', 'n/a', 'na')
        """)).scalar()

        ds_missing_name = db.execute(text("""
            SELECT COUNT(*) FROM discovery_staging
            WHERE raw_name IS NULL OR TRIM(raw_name) = '' OR LOWER(TRIM(raw_name)) IN ('linkedin member', 'unknown')
        """)).scalar()

        print(f"  • Staging with Platform Noise Company ('LinkedIn', 'Google', etc.): {ds_noise_company:,}")
        print(f"  • Staging with Missing / Placeholder Name: {ds_missing_name:,}")


if __name__ == "__main__":
    scan_parquet_bad_data()
    scan_postgresql_bad_data()
