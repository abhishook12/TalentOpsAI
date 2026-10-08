"""
Comprehensive Deep Multi-Vector Forensic Scanner
Audits 433,742 records across 12 distinct dimensions:
1. Invisible / Non-printable characters & whitespace anomalies (emails, names, companies)
2. Role-based generic emails in personal recruiter catalog (info@, sales@, support@, etc.)
3. Disposable / Temp email domains
4. TLD anomalies & domain syntax flaws
5. Names containing company designations (Inc, LLC, Corp, Technologies)
6. Names containing job titles (Recruiter, Sourcer, Manager, Director)
7. Names with digits, special punctuation, or invalid characters
8. All-caps or all-lowercase names requiring title-casing
9. Companies containing domain extensions (.com, .net) or web prefixes (http, www)
10. Residual US-only states and resolvable state consensus from Company HQs
11. Phone number sanity (repeated digits, dummy numbers, malformed strings)
12. LinkedIn vanity slug integrity (tracking query params, directory URLs)
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

US_VALID_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'PR', 'VI', 'GU', 'AS', 'MP'
}

ROLE_BASED_PREFIXES = [
    'info', 'admin', 'administrator', 'support', 'sales', 'contact', 'contactus',
    'hr', 'careers', 'career', 'recruiting', 'recruitment', 'recruiter', 'jobs',
    'billing', 'help', 'helpdesk', 'office', 'team', 'marketing', 'press',
    'media', 'general', 'inquiries', 'mail', 'webmaster', 'postmaster'
]

DISPOSABLE_DOMAINS = [
    'mailinator.com', '10minutemail.com', 'tempmail.com', 'guerrillamail.com',
    'throwawaymail.com', 'yopmail.com', 'sharklasers.com', 'getairmail.com',
    'dispostable.com', 'fakeinbox.com', 'trashmail.com'
]

CORP_WORDS_IN_NAME = [
    'inc', 'llc', 'corp', 'corporation', 'ltd', 'limited', 'technologies',
    'solutions', 'services', 'staffing', 'consulting', 'group', 'global',
    'associates', 'partners', 'systems', 'enterprises', 'holdings'
]

TITLE_WORDS_IN_NAME = [
    'recruiter', 'sourcer', 'recruiting', 'talent', 'acquisition',
    'lead', 'manager', 'director', 'vp', 'vice president', 'president',
    'head', 'consultant', 'coordinator', 'specialist'
]

DUMMY_PHONES = [
    '1234567890', '0000000000', '1111111111', '2222222222', '3333333333',
    '4444444444', '5555555555', '6666666666', '7777777777', '8888888888',
    '9999999999', '1231231234', '9876543210'
]

def audit():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print("=" * 80)
    print("PROBING ULTRA-DEEP FORENSIC ANOMALIES ACROSS ALL RECORDS")
    print("=" * 80)
    
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    total = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Total Master Records Loaded: {total:,}\n")

    # Vector 1: Invisible / Non-printable characters
    print("[VECTOR 1] INVISIBLE & NON-PRINTABLE CHARACTERS:")
    inv_emails = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE email IS NOT NULL AND (
            email LIKE '%\t%' OR email LIKE '%\n%' OR email LIKE '%\r%' 
            OR email LIKE '%\xa0%' OR email LIKE '% %'
        )
    """).fetchone()[0]
    inv_names = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE recruiter_name IS NOT NULL AND (
            recruiter_name LIKE '%\t%' OR recruiter_name LIKE '%\n%' OR recruiter_name LIKE '%\r%' 
            OR recruiter_name LIKE '%\xa0%'
        )
    """).fetchone()[0]
    print(f"  • Emails with whitespace / tab / newline / non-breaking space: {inv_emails}")
    print(f"  • Names with tab / newline / carriage return / non-breaking space: {inv_names}")

    # Vector 2: Role-based generic emails
    print("\n[VECTOR 2] ROLE-BASED / GENERIC INBOXES (vs Personal Recruiters):")
    role_sql = " OR ".join(f"LOWER(SPLIT_PART(email, '@', 1)) = '{p}'" for p in ROLE_BASED_PREFIXES)
    role_emails = con.execute(f"SELECT COUNT(*) FROM rec WHERE email IS NOT NULL AND ({role_sql})").fetchone()[0]
    print(f"  • Role-based inboxes (info@, sales@, hr@, careers@, etc.): {role_emails}")
    if role_emails > 0:
        samples = con.execute(f"SELECT email, recruiter_name, company_id FROM rec WHERE email IS NOT NULL AND ({role_sql}) LIMIT 5").fetchall()
        print(f"    Samples: {samples}")

    # Vector 3: Disposable email domains
    print("\n[VECTOR 3] DISPOSABLE / TEMPORARY EMAIL SERVICES:")
    disp_sql = " OR ".join(f"LOWER(SPLIT_PART(email, '@', 2)) = '{d}'" for d in DISPOSABLE_DOMAINS)
    disp_emails = con.execute(f"SELECT COUNT(*) FROM rec WHERE email IS NOT NULL AND ({disp_sql})").fetchone()[0]
    print(f"  • Disposable email addresses: {disp_emails}")

    # Vector 4: Email domain structure & TLD sanity
    print("\n[VECTOR 4] EMAIL DOMAIN STRUCTURE & TLD INTEGRITY:")
    invalid_domain_chars = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE email IS NOT NULL 
          AND (
            SPLIT_PART(email, '@', 2) LIKE '% %'
            OR SPLIT_PART(email, '@', 2) NOT LIKE '%.%'
            OR SPLIT_PART(email, '@', 2) LIKE '%.--%'
            OR SPLIT_PART(email, '@', 2) LIKE '%..%'
            OR SPLIT_PART(email, '@', 2) LIKE '%@%'
            OR SPLIT_PART(email, '@', 2) LIKE '%/%'
            OR SPLIT_PART(email, '@', 2) LIKE '%\\\\%'
          )
    """).fetchone()[0]
    print(f"  • Domains with invalid characters / missing dot / double dot: {invalid_domain_chars}")
    if invalid_domain_chars > 0:
        samples = con.execute("""
            SELECT email FROM rec 
            WHERE email IS NOT NULL 
              AND (
                SPLIT_PART(email, '@', 2) LIKE '% %'
                OR SPLIT_PART(email, '@', 2) NOT LIKE '%.%'
                OR SPLIT_PART(email, '@', 2) LIKE '%..%'
              ) LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")

    # Vector 5: Company Designations in Person Names
    print("\n[VECTOR 5] COMPANY LEGAL SUFFIXES IN PERSON NAMES (Crawler flipped fields?):")
    corp_in_name_sql = " OR ".join(
        f"LOWER(recruiter_name) = '{w}' OR LOWER(recruiter_name) LIKE '{w} %' OR LOWER(recruiter_name) LIKE '% {w}' OR LOWER(recruiter_name) LIKE '%, {w}'"
        for w in CORP_WORDS_IN_NAME
    )
    corp_names = con.execute(f"SELECT COUNT(*) FROM rec WHERE recruiter_name IS NOT NULL AND ({corp_in_name_sql})").fetchone()[0]
    print(f"  • Names containing corporate legal suffixes (Inc, LLC, Corp, Technologies, etc.): {corp_names}")
    if corp_names > 0:
        samples = con.execute(f"SELECT recruiter_name, company_id, email FROM rec WHERE recruiter_name IS NOT NULL AND ({corp_in_name_sql}) LIMIT 6").fetchall()
        print(f"    Samples: {samples}")

    # Vector 6: Job Titles in Person Names
    print("\n[VECTOR 6] JOB TITLES EMBEDDED IN PERSON NAMES:")
    title_in_name_sql = " OR ".join(
        f"LOWER(recruiter_name) LIKE '% {w}' OR LOWER(recruiter_name) LIKE '{w} %' OR LOWER(recruiter_name) LIKE '% - {w}%'"
        for w in TITLE_WORDS_IN_NAME
    )
    title_names = con.execute(f"SELECT COUNT(*) FROM rec WHERE recruiter_name IS NOT NULL AND ({title_in_name_sql})").fetchone()[0]
    print(f"  • Names containing job titles (e.g. 'John Doe Recruiter', 'Lead Sourcer'): {title_names}")
    if title_names > 0:
        samples = con.execute(f"SELECT recruiter_name, title, email FROM rec WHERE recruiter_name IS NOT NULL AND ({title_in_name_sql}) LIMIT 6").fetchall()
        print(f"    Samples: {samples}")

    # Vector 7: Names with Digits / Odd Punctuation
    print("\n[VECTOR 7] NAMES WITH DIGITS OR UNUSUAL SYMBOLS:")
    digit_names = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE recruiter_name IS NOT NULL 
          AND REGEXP_MATCHES(recruiter_name, '[0-9]')
    """).fetchone()[0]
    symbol_names = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE recruiter_name IS NOT NULL 
          AND (
            recruiter_name LIKE '%"%'
            OR recruiter_name LIKE '%''%'
            OR recruiter_name LIKE '%[%'
            OR recruiter_name LIKE '%]%'
            OR recruiter_name LIKE '%(%'
            OR recruiter_name LIKE '%)%'
            OR recruiter_name LIKE '%{%'
            OR recruiter_name LIKE '%}%'
            OR recruiter_name LIKE '%|%'
            OR recruiter_name LIKE '%<%'
            OR recruiter_name LIKE '%>%'
            OR recruiter_name LIKE '%+%'
            OR recruiter_name LIKE '%=%'
            OR recruiter_name LIKE '%!%'
            OR recruiter_name LIKE '%@%'
            OR recruiter_name LIKE '%#%'
            OR recruiter_name LIKE '%$%'
            OR recruiter_name LIKE '%^%'
            OR recruiter_name LIKE '%*%'
            OR recruiter_name LIKE '%~%'
            OR recruiter_name LIKE '%?%'
          )
    """).fetchone()[0]
    print(f"  • Names containing numeric digits: {digit_names}")
    if digit_names > 0:
        samples = con.execute("SELECT recruiter_name, email FROM rec WHERE recruiter_name IS NOT NULL AND REGEXP_MATCHES(recruiter_name, '[0-9]') LIMIT 5").fetchall()
        print(f"    Samples: {samples}")
    print(f"  • Names containing symbols / brackets / quotes: {symbol_names}")
    if symbol_names > 0:
        samples = con.execute("""
            SELECT recruiter_name, email FROM rec 
            WHERE recruiter_name IS NOT NULL 
              AND (
                recruiter_name LIKE '%(%' OR recruiter_name LIKE '%)%'
                OR recruiter_name LIKE '%"%' OR recruiter_name LIKE '%@%'
                OR recruiter_name LIKE '%+%' OR recruiter_name LIKE '%?%'
              ) LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")

    # Vector 8: Case Sanitization (ALL CAPS or all lowercase names)
    print("\n[VECTOR 8] CASING ANOMALIES IN PERSON NAMES:")
    all_caps_names = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE recruiter_name IS NOT NULL 
          AND LENGTH(TRIM(recruiter_name)) > 2
          AND recruiter_name = UPPER(recruiter_name)
          AND recruiter_name != LOWER(recruiter_name)
    """).fetchone()[0]
    all_lower_names = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE recruiter_name IS NOT NULL 
          AND LENGTH(TRIM(recruiter_name)) > 2
          AND recruiter_name = LOWER(recruiter_name)
          AND recruiter_name != UPPER(recruiter_name)
    """).fetchone()[0]
    print(f"  • ALL CAPS names (e.g. 'JOHN SMITH'): {all_caps_names:,}")
    print(f"  • all lowercase names (e.g. 'john smith'): {all_lower_names:,}")

    # Vector 9: Company Name Cleanliness (Web Prefixes, Domain Extensions in Company Field)
    print("\n[VECTOR 9] COMPANY NAMES HOLDING DOMAIN STRINGS / URLS:")
    url_comps = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE company_id IS NOT NULL 
          AND (
            LOWER(company_id) LIKE 'http://%' 
            OR LOWER(company_id) LIKE 'https://%' 
            OR LOWER(company_id) LIKE 'www.%'
          )
    """).fetchone()[0]
    ext_comps = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE company_id IS NOT NULL 
          AND (
            LOWER(company_id) LIKE '%.com'
            OR LOWER(company_id) LIKE '%.net'
            OR LOWER(company_id) LIKE '%.org'
            OR LOWER(company_id) LIKE '%.io'
            OR LOWER(company_id) LIKE '%.ai'
            OR LOWER(company_id) LIKE '%.co'
          )
    """).fetchone()[0]
    print(f"  • Companies with http://, https://, or www. prefixes: {url_comps}")
    if url_comps > 0:
        samples = con.execute("SELECT company_id, email FROM rec WHERE company_id IS NOT NULL AND (LOWER(company_id) LIKE 'http://%' OR LOWER(company_id) LIKE 'https://%' OR LOWER(company_id) LIKE 'www.%') LIMIT 5").fetchall()
        print(f"    Samples: {samples}")
    print(f"  • Companies ending in domain extensions (.com, .io, .net, etc.): {ext_comps}")
    if ext_comps > 0:
        samples = con.execute("SELECT company_id, email FROM rec WHERE company_id IS NOT NULL AND (LOWER(company_id) LIKE '%.com' OR LOWER(company_id) LIKE '%.net' OR LOWER(company_id) LIKE '%.org' OR LOWER(company_id) LIKE '%.io' OR LOWER(company_id) LIKE '%.ai') LIMIT 5").fetchall()
        print(f"    Samples: {samples}")

    # Vector 10: State Resolution & Alignment
    print("\n[VECTOR 10] STATE FIELD DEEP AUDIT:")
    all_states = con.execute("SELECT DISTINCT state FROM rec WHERE state IS NOT NULL").fetchall()
    states_list = [str(s[0]).strip().upper() for s in all_states]
    invalid_states = [s for s in states_list if s not in US_VALID_STATES]
    print(f"  • Distinct non-US / non-standard state values found: {len(invalid_states)}")
    if len(invalid_states) > 0:
        inv_counts = con.execute(f"""
            SELECT state, COUNT(*) FROM rec 
            WHERE state IS NOT NULL AND UPPER(TRIM(state)) NOT IN {tuple(US_VALID_STATES)}
            GROUP BY state ORDER BY COUNT(*) DESC LIMIT 15
        """).fetchall()
        print(f"    Top non-standard states: {inv_counts}")

    # Vector 11: Phone Number Forensic Audit
    print("\n[VECTOR 11] PHONE NUMBER FORENSIC AUDIT:")
    dummy_phones_count = con.execute(f"""
        SELECT COUNT(*) FROM rec 
        WHERE phone IS NOT NULL 
          AND REGEXP_REPLACE(phone, '[^0-9]', '', 'g') IN {tuple(DUMMY_PHONES)}
    """).fetchone()[0]
    short_phones = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE phone IS NOT NULL 
          AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) > 0
          AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) < 10
    """).fetchone()[0]
    print(f"  • Dummy / repeating phone numbers (1234567890, 0000000000, etc.): {dummy_phones_count}")
    print(f"  • Incomplete / too-short phone numbers (<10 digits): {short_phones}")
    if short_phones > 0:
        samples = con.execute("SELECT phone, recruiter_name FROM rec WHERE phone IS NOT NULL AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) > 0 AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) < 10 LIMIT 5").fetchall()
        print(f"    Samples: {samples}")

    # Vector 12: LinkedIn URL forensic audit
    print("\n[VECTOR 12] LINKEDIN URL FORENSIC AUDIT:")
    tracking_li = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE linkedin IS NOT NULL 
          AND (
            linkedin LIKE '%?%'
            OR linkedin LIKE '%#%'
            OR linkedin LIKE '%/pub/dir/%'
          )
    """).fetchone()[0]
    print(f"  • LinkedIn URLs with tracking query params (?trk=, etc.) or directory URLs: {tracking_li}")
    if tracking_li > 0:
        samples = con.execute("SELECT linkedin FROM rec WHERE linkedin IS NOT NULL AND (linkedin LIKE '%?%' OR linkedin LIKE '%#%' OR linkedin LIKE '%/pub/dir/%') LIMIT 5").fetchall()
        print(f"    Samples: {samples}")

    print("\n" + "=" * 80)
    print("AUDIT PROBE EXECUTION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    audit()
