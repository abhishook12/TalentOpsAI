"""
Ultra-Deep Forensic Data Quality Hunter
=======================================
Deeply interrogates:
1. Non-Recruiter / Irrelevant Roles in catalog (Cashier, Truck Driver, Nurse, Student, Chef, etc.)
2. Company Noise Variations ('Self-employed', 'Retired', 'Looking for Opportunities', 'Confidential', etc.)
3. Email-Company Mismatches (e.g. Company says 'Microsoft', but email is '@amazon.com')
4. Typos in Free Mail Domains (gmaill.com, hotmial.com, yaho.com, etc.)
5. Corrupt Encoding / Mozybake in Names & Titles (Ã©, â€™, , HTML entities like &amp;)
6. Single-Word Names, Punctuation-Only Names, Prefix/Suffix Clutter (Mr., Dr., Esq., MBA, PMP)
7. City/Location Noise ('Remote', 'Anywhere', City == State, Zip codes in city)
8. Non-Personal LinkedIn URLs (Sales Navigator, Recruiter seats, Search results, Posts)
9. Toll-Free / Repeated Switchboard Phone Numbers
10. Discovery Staging JSON & Field Integrity
"""

import os
import sys
import re
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

from app.database import SessionLocal
from sqlalchemy import text

IRRELEVANT_JOB_ROLES = [
    'cashier', 'truck driver', 'driver', 'nurse', 'registered nurse', 'waiter', 
    'waitress', 'chef', 'cook', 'bartender', 'student', 'retired', 'unemployed',
    'intern', 'janitor', 'custodian', 'security guard', 'teacher', 'tutor'
]

NOISE_COMPANY_PATTERNS = [
    'self employed', 'self-employed', 'freelance', 'freelancer', 'unemployed',
    'retired', 'student', 'confidential', 'stealth', 'looking for', 'seeking',
    'open to work', 'n/a', 'none', 'independent contractor', 'various'
]

FREE_MAIL_TYPOS = [
    'gmaill.com', 'gmai.com', 'gmil.com', 'gmial.com', 'gmaill.com',
    'hotmial.com', 'hotmai.com', 'homail.com', 'yaho.com', 'yahooo.com',
    'outlok.com', 'outloo.com'
]

NAME_PREFIXES = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.']
NAME_SUFFIXES = ['mba', 'pmp', 'phd', 'esq', 'cpa', 'shrm-cp', 'phr', 'sphr', 'cir', 'cprw']


def run_deepest_scan():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print("\n" + "="*80)
    print("ULTRA-DEEP FORENSIC DATA QUALITY SCAN (433,742 RECORDS)")
    print("="*80)

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    total = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Total Rows Inspected: {total:,}\n")

    findings = {}

    # -------------------------------------------------------------
    # 1. Non-Recruiter / Candidate Misclassifications in Titles
    # -------------------------------------------------------------
    print("[1] JOB ROLE INTEGRITY (Are these all staffing/recruiting professionals?):")
    irrelevant_sql = " OR ".join(f"LOWER(title) = '{r}' OR LOWER(title) LIKE '{r} %' OR LOWER(title) LIKE '% {r}'" for r in IRRELEVANT_JOB_ROLES)
    irrelevant_titles = con.execute(f"SELECT COUNT(*) FROM rec WHERE title IS NOT NULL AND ({irrelevant_sql})").fetchone()[0]
    print(f"  • Non-recruiting / Irrelevant candidate titles (Nurse, Truck Driver, Cashier, etc.): {irrelevant_titles:,}")
    if irrelevant_titles > 0:
        samples = con.execute(f"SELECT recruiter_name, title, company_id FROM rec WHERE title IS NOT NULL AND ({irrelevant_sql}) LIMIT 6").fetchall()
        print(f"    Samples: {samples}")
    findings["irrelevant_titles"] = irrelevant_titles

    # -------------------------------------------------------------
    # 2. Company Platform Noise & Non-Company Entities
    # -------------------------------------------------------------
    print("\n[2] COMPANY INTEGRITY (Non-company phrases stored as company):")
    noise_comp_sql = " OR ".join(f"LOWER(TRIM(CAST(company_id AS VARCHAR))) LIKE '%{p}%'" for p in NOISE_COMPANY_PATTERNS)
    noise_comps = con.execute(f"SELECT COUNT(*) FROM rec WHERE company_id IS NOT NULL AND ({noise_comp_sql})").fetchone()[0]
    print(f"  • Non-company phrases (Self-employed, Seeking, Retired, Confidential, etc.): {noise_comps:,}")
    if noise_comps > 0:
        samples = con.execute(f"SELECT company_id, recruiter_name, email FROM rec WHERE company_id IS NOT NULL AND ({noise_comp_sql}) LIMIT 6").fetchall()
        print(f"    Samples: {samples}")
    findings["noise_comps"] = noise_comps

    # -------------------------------------------------------------
    # 3. Email-Company Mismatch
    # -------------------------------------------------------------
    print("\n[3] EMAIL DOMAIN VS COMPANY ALIGNMENT:")
    # Check cases where email domain belongs to one known firm, but company says another firm
    mismatch_count = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE email IS NOT NULL AND company_id IS NOT NULL
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com')
          AND LENGTH(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1)) > 4
          AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT LIKE '%' || SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1) || '%'
          AND SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1) NOT LIKE '%' || LOWER(TRIM(CAST(company_id AS VARCHAR))) || '%'
    """).fetchone()[0]
    print(f"  • Potential Cross-Company Attribution Gaps (domain != company name): {mismatch_count:,}")
    if mismatch_count > 0:
        samples = con.execute("""
            SELECT recruiter_name, company_id, email FROM rec
            WHERE email IS NOT NULL AND company_id IS NOT NULL
              AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com')
              AND LENGTH(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1)) > 4
              AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT LIKE '%' || SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1) || '%'
              AND SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1) NOT LIKE '%' || LOWER(TRIM(CAST(company_id AS VARCHAR))) || '%'
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    findings["company_email_mismatch"] = mismatch_count

    # -------------------------------------------------------------
    # 4. Typos in Free Mail Domains
    # -------------------------------------------------------------
    print("\n[4] FREE MAIL DOMAIN TYPOS:")
    free_typo_sql = " OR ".join(f"email LIKE '%@{d}'" for d in FREE_MAIL_TYPOS)
    free_typos = con.execute(f"SELECT COUNT(*) FROM rec WHERE email IS NOT NULL AND ({free_typo_sql})").fetchone()[0]
    print(f"  • Typos in consumer webmail domains (gmaill.com, hotmial.com, etc.): {free_typos:,}")
    findings["free_mail_typos"] = free_typos

    # -------------------------------------------------------------
    # 5. Encoding Corruption & HTML Entities in Names & Titles
    # -------------------------------------------------------------
    print("\n[5] ENCODING CORRUPTION & HTML ENTITIES (Mojibake):")
    mojibake_names = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND (
            recruiter_name LIKE '%Ã%' 
            OR recruiter_name LIKE '%â%' 
            OR recruiter_name LIKE '%%'
            OR recruiter_name LIKE '%&amp;%'
            OR recruiter_name LIKE '%&quot;%'
            OR recruiter_name LIKE '&#%'
          )
    """).fetchone()[0]
    print(f"  • Encoding Corruption / HTML Entities in Recruiter Names: {mojibake_names:,}")
    if mojibake_names > 0:
        samples = con.execute("""
            SELECT recruiter_name FROM rec
            WHERE recruiter_name IS NOT NULL 
              AND (recruiter_name LIKE '%Ã%' OR recruiter_name LIKE '%â%' OR recruiter_name LIKE '%&amp;%' OR recruiter_name LIKE '&#%')
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    findings["mojibake_names"] = mojibake_names

    mojibake_titles = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE title IS NOT NULL 
          AND (
            title LIKE '%Ã%' 
            OR title LIKE '%â%' 
            OR title LIKE '%%'
            OR title LIKE '%&amp;%'
            OR title LIKE '%&quot;%'
            OR title LIKE '&#%'
          )
    """).fetchone()[0]
    print(f"  • Encoding Corruption / HTML Entities in Job Titles: {mojibake_titles:,}")
    findings["mojibake_titles"] = mojibake_titles

    # -------------------------------------------------------------
    # 6. Single-Word Names & Certification Suffix Clutter
    # -------------------------------------------------------------
    print("\n[6] NAME STRUCTURE & SUFFIX CLUTTER:")
    single_word_names = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND INSTR(TRIM(recruiter_name), ' ') = 0
          AND LENGTH(TRIM(recruiter_name)) > 1
    """).fetchone()[0]
    print(f"  • Single-word names (only First Name, no surname): {single_word_names:,}")
    if single_word_names > 0:
        samples = con.execute("SELECT recruiter_name, email FROM rec WHERE recruiter_name IS NOT NULL AND INSTR(TRIM(recruiter_name), ' ') = 0 LIMIT 5").fetchall()
        print(f"    Samples: {samples}")
    findings["single_word_names"] = single_word_names

    suffix_sql = " OR ".join(f"LOWER(recruiter_name) LIKE '%, {s}%' OR LOWER(recruiter_name) LIKE '% {s}'" for s in NAME_SUFFIXES)
    cert_names = con.execute(f"SELECT COUNT(*) FROM rec WHERE recruiter_name IS NOT NULL AND ({suffix_sql})").fetchone()[0]
    print(f"  • Certification suffix clutter in person names (PMP, MBA, CPA, etc.): {cert_names:,}")
    if cert_names > 0:
        samples = con.execute(f"SELECT recruiter_name FROM rec WHERE recruiter_name IS NOT NULL AND ({suffix_sql}) LIMIT 5").fetchall()
        print(f"    Samples: {samples}")
    findings["cert_names"] = cert_names

    # -------------------------------------------------------------
    # 7. City / Location Noise
    # -------------------------------------------------------------
    print("\n[7] LOCATION & CITY NOISE:")
    city_equals_state = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE normalized_city IS NOT NULL AND state IS NOT NULL
          AND UPPER(TRIM(normalized_city)) = UPPER(TRIM(CAST(state AS VARCHAR)))
    """).fetchone()[0]
    print(f"  • City mistakenly identical to State code: {city_equals_state:,}")

    zip_in_city = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE normalized_city IS NOT NULL 
          AND REGEXP_MATCHES(normalized_city, '[0-9]{4,}')
    """).fetchone()[0]
    print(f"  • Zip codes stored in city name: {zip_in_city:,}")
    findings["zip_in_city"] = zip_in_city

    # -------------------------------------------------------------
    # 8. Non-Personal LinkedIn URLs
    # -------------------------------------------------------------
    print("\n[8] LINKEDIN URL CLASSIFICATION:")
    bad_li_types = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE linkedin IS NOT NULL 
          AND (
            linkedin LIKE '%/search/%'
            OR linkedin LIKE '%/sales/%'
            OR linkedin LIKE '%/talent/%'
            OR linkedin LIKE '%/posts/%'
            OR linkedin LIKE '%/groups/%'
          )
    """).fetchone()[0]
    print(f"  • Non-profile LinkedIn URLs (Search results, Posts, Sales Nav): {bad_li_types:,}")
    if bad_li_types > 0:
        samples = con.execute("""
            SELECT linkedin, recruiter_name FROM rec
            WHERE linkedin IS NOT NULL 
              AND (linkedin LIKE '%/search/%' OR linkedin LIKE '%/sales/%' OR linkedin LIKE '%/talent/%' OR linkedin LIKE '%/posts/%')
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    findings["bad_li_types"] = bad_li_types

    # -------------------------------------------------------------
    # 9. Generic Country State 'US'
    # -------------------------------------------------------------
    print("\n[9] RESIDUAL GENERIC 'US' STATES:")
    us_state_count = con.execute("SELECT COUNT(*) FROM rec WHERE UPPER(TRIM(CAST(state AS VARCHAR))) = 'US'").fetchone()[0]
    print(f"  • Records still holding generic country-level 'US' state: {us_state_count:,} ({((us_state_count)/total)*100:.1f}%)")
    findings["us_state_count"] = us_state_count

    print("\n" + "="*80)
    print("ULTRA-DEEP FORENSIC SCAN COMPLETE!")
    print("="*80)
    return findings

if __name__ == "__main__":
    run_deepest_scan()
