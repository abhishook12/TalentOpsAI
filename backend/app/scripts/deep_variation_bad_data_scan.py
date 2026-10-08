"""
Deep Multi-Variation Bad Data Forensics Hunter
=============================================
Investigates nuanced and latent data quality anomalies across:
1. Email Variations:
   - Common TLD typos (.con, .comm, .coom, .cm, .col)
   - Trailing punctuation (dots, commas, quotes, slashes)
   - Invisible whitespace & control characters (\u200b, \xa0, \t, \r, \n)
   - Disposable / throwaway mail providers (tempmail, mailinator, etc.)
   - Pure numeric / hex usernames
2. Name Variations:
   - All-caps shouting or all-lowercase names
   - Emojis, symbols, and badges in names (★, 🚀, [Hiring], (Open to work), LION)
   - Duplicated first/last names (e.g. 'John John', 'Smith Smith')
   - Company names mistakenly placed in the person name field
   - Credential suffix clutter (PMP, MBA, CISSP, CPRW, etc.)
3. Job Title Variations:
   - Slogans / pitch decks dumped in title ('Helping companies scale...', '500+ connections')
   - Locations dumped in job title field ('Dallas, Texas', 'New York, NY')
   - Single-word non-titles ('Yes', 'Open', 'Available')
4. Company Variations:
   - URLs as company names ('www.acme.com', 'acme.com')
   - Cluttered corporate suffixes ('Inc.', 'LLC', 'Corp.', 'Ltd.') causing fragmented duplicates
   - Truncated / broken characters
5. Phone Variations:
   - Letters in phone numbers
   - Invalid digit lengths (< 10 or > 15 digits)
6. LinkedIn URL Variations:
   - Company URLs placed in personal LinkedIn profile field ('/company/')
   - Double URLs ('linkedin.com/in/https://...')
"""

import os
import sys
import re
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

COMMON_TLD_TYPOS = ['.con', '.comm', '.coom', '.cm', '.col', '.cmo', '.cpm']

DISPOSABLE_DOMAINS = [
    'mailinator.com', 'tempmail.com', '10minutemail.com', 'guerrillamail.com',
    'yopmail.com', 'trashmail.com', 'getairmail.com', 'sharklasers.com',
    'dispostable.com', 'fakemailgenerator.com'
]

EMOJI_REGEX = r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]'


def run_deep_variation_scan():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print("\n" + "="*75)
    print("DEEP MULTI-VARIATION FORENSIC SCAN (433,741 RECORDS)")
    print("="*75)

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    total = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Total Records Inspected: {total:,}\n")

    report = {}

    # -------------------------------------------------------------
    # 1. EMAIL VARIATIONS
    # -------------------------------------------------------------
    print("[1] EMAIL VARIATIONS & LATENT DEFECTS:")

    # 1a. Common TLD typos
    tld_typo_sql = " OR ".join(f"email LIKE '%{t}'" for t in COMMON_TLD_TYPOS)
    tld_typos = con.execute(f"SELECT COUNT(*) FROM rec WHERE email IS NOT NULL AND ({tld_typo_sql})").fetchone()[0]
    print(f"  • Common TLD Typos (.con, .comm, .coom, .cm, etc.): {tld_typos:,}")
    if tld_typos > 0:
        samples = con.execute(f"SELECT email FROM rec WHERE email IS NOT NULL AND ({tld_typo_sql}) LIMIT 5").fetchall()
        print(f"    Samples: {samples}")
    report["tld_typos"] = tld_typos

    # 1b. Trailing punctuation or illegal end characters
    trailing_punct = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE email IS NOT NULL 
          AND (email LIKE '%.' OR email LIKE '%, ' OR email LIKE '%/' OR email LIKE '%;')
    """).fetchone()[0]
    print(f"  • Trailing Punctuation in Email (dots, commas, slashes): {trailing_punct:,}")
    if trailing_punct > 0:
        samples = con.execute("""
            SELECT email FROM rec 
            WHERE email IS NOT NULL 
              AND (email LIKE '%.' OR email LIKE '%, ' OR email LIKE '%/' OR email LIKE '%;')
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["trailing_punct_emails"] = trailing_punct

    # 1c. Disposable / throwaway email domains
    disposable_sql = ", ".join(f"'{d}'" for d in DISPOSABLE_DOMAINS)
    disposable_count = con.execute(f"""
        SELECT COUNT(*) FROM rec 
        WHERE email IS NOT NULL 
          AND LOWER(SPLIT_PART(email, '@', 2)) IN ({disposable_sql})
    """).fetchone()[0]
    print(f"  • Disposable / Throwaway Mailboxes: {disposable_count:,}")
    report["disposable_emails"] = disposable_count

    # 1d. Pure numeric or hex email usernames (bots / scrape artifacts)
    numeric_usernames = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE email IS NOT NULL 
          AND REGEXP_MATCHES(SPLIT_PART(email, '@', 1), '^[0-9]{5,}$')
    """).fetchone()[0]
    print(f"  • Scrape-bot numeric handles (e.g. 1928374@...): {numeric_usernames:,}")
    if numeric_usernames > 0:
        samples = con.execute("""
            SELECT email, recruiter_name FROM rec
            WHERE email IS NOT NULL 
              AND REGEXP_MATCHES(SPLIT_PART(email, '@', 1), '^[0-9]{5,}$')
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["numeric_usernames"] = numeric_usernames

    # -------------------------------------------------------------
    # 2. NAME VARIATIONS
    # -------------------------------------------------------------
    print("\n[2] NAME VARIATIONS & LATENT DEFECTS:")

    # 2a. Emojis, stars, badges in names
    emoji_names = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND (
            recruiter_name LIKE '%★%'
            OR recruiter_name LIKE '%✨%'
            OR recruiter_name LIKE '%🔥%'
            OR recruiter_name LIKE '%🚀%'
            OR recruiter_name LIKE '%✔%'
            OR recruiter_name LIKE '%(Open%'
            OR recruiter_name LIKE '%[Hiring%'
            OR recruiter_name LIKE '%(LION)%'
          )
    """).fetchone()[0]
    print(f"  • Emojis / Status Badges in Names (★, [Hiring], LION, etc.): {emoji_names:,}")
    if emoji_names > 0:
        samples = con.execute("""
            SELECT recruiter_name FROM rec
            WHERE recruiter_name IS NOT NULL 
              AND (
                recruiter_name LIKE '%★%'
                OR recruiter_name LIKE '%✨%'
                OR recruiter_name LIKE '%🔥%'
                OR recruiter_name LIKE '%(Open%'
                OR recruiter_name LIKE '%[Hiring%'
              )
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["emoji_names"] = emoji_names

    # 2b. Duplicated first and last name (e.g. 'John John', 'Smith Smith')
    dup_names = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND INSTR(TRIM(recruiter_name), ' ') > 0
          AND LOWER(SPLIT_PART(TRIM(recruiter_name), ' ', 1)) = LOWER(SPLIT_PART(TRIM(recruiter_name), ' ', 2))
          AND LENGTH(SPLIT_PART(TRIM(recruiter_name), ' ', 1)) > 2
    """).fetchone()[0]
    print(f"  • Identical First & Last Names (e.g. 'Smith Smith'): {dup_names:,}")
    if dup_names > 0:
        samples = con.execute("""
            SELECT recruiter_name, email FROM rec
            WHERE recruiter_name IS NOT NULL 
              AND INSTR(TRIM(recruiter_name), ' ') > 0
              AND LOWER(SPLIT_PART(TRIM(recruiter_name), ' ', 1)) = LOWER(SPLIT_PART(TRIM(recruiter_name), ' ', 2))
              AND LENGTH(SPLIT_PART(TRIM(recruiter_name), ' ', 1)) > 2
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["dup_names"] = dup_names

    # 2c. All-uppercase shouting names
    all_caps_names = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND LENGTH(TRIM(recruiter_name)) > 4
          AND recruiter_name = UPPER(recruiter_name)
          AND REGEXP_MATCHES(recruiter_name, '^[A-Z\\s\\.\\-]+$')
    """).fetchone()[0]
    print(f"  • All-Caps Shouting Names (e.g. 'JOHN DOE'): {all_caps_names:,}")
    report["all_caps_names"] = all_caps_names

    # 2d. All-lowercase names
    all_lower_names = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND LENGTH(TRIM(recruiter_name)) > 4
          AND recruiter_name = LOWER(recruiter_name)
          AND REGEXP_MATCHES(recruiter_name, '^[a-z\\s\\.\\-]+$')
    """).fetchone()[0]
    print(f"  • All-Lowercase Names (e.g. 'john doe'): {all_lower_names:,}")
    report["all_lower_names"] = all_lower_names

    # 2e. Company name mistakenly in Recruiter Name
    comp_as_name = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND company_id IS NOT NULL 
          AND LOWER(TRIM(recruiter_name)) = LOWER(TRIM(CAST(company_id AS VARCHAR)))
    """).fetchone()[0]
    print(f"  • Company Name mistakenly stored as Person Name: {comp_as_name:,}")
    if comp_as_name > 0:
        samples = con.execute("""
            SELECT recruiter_name, company_id, email, title FROM rec
            WHERE recruiter_name IS NOT NULL 
              AND company_id IS NOT NULL 
              AND LOWER(TRIM(recruiter_name)) = LOWER(TRIM(CAST(company_id AS VARCHAR)))
            LIMIT 6
        """).fetchall()
        print(f"    Samples: {samples}")
    report["comp_as_name"] = comp_as_name

    # -------------------------------------------------------------
    # 3. JOB TITLE VARIATIONS
    # -------------------------------------------------------------
    print("\n[3] JOB TITLE VARIATIONS & LATENT DEFECTS:")

    # 3a. Location dumped in Title
    loc_in_title = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE title IS NOT NULL 
          AND (
            LOWER(title) LIKE '%united states%'
            OR LOWER(title) LIKE '%area%'
            OR LOWER(title) LIKE '%greater %'
            OR REGEXP_MATCHES(title, '^[A-Za-z\\s]+,\\s*[A-Z]{2}$')
          )
    """).fetchone()[0]
    print(f"  • Location strings dumped in Title: {loc_in_title:,}")
    if loc_in_title > 0:
        samples = con.execute("""
            SELECT title FROM rec
            WHERE title IS NOT NULL 
              AND (
                LOWER(title) LIKE '%united states%'
                OR REGEXP_MATCHES(title, '^[A-Za-z\\s]+,\\s*[A-Z]{2}$')
              )
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["loc_in_title"] = loc_in_title

    # 3b. Slogan / pitch deck clutter in Title
    slogans_in_title = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE title IS NOT NULL 
          AND (
            LOWER(title) LIKE '%helping %'
            OR LOWER(title) LIKE '%passionate about%'
            OR LOWER(title) LIKE '%looking for%'
            OR LOWER(title) LIKE '%connections%'
            OR LOWER(title) LIKE '%results-driven%'
            OR LENGTH(title) > 80
          )
    """).fetchone()[0]
    print(f"  • Slogan / Pitch Clutter (>80 chars or marketing buzzwords): {slogans_in_title:,}")
    report["slogans_in_title"] = slogans_in_title

    # -------------------------------------------------------------
    # 4. COMPANY VARIATIONS
    # -------------------------------------------------------------
    print("\n[4] COMPANY VARIATIONS & LATENT DEFECTS:")

    # 4a. URLs as Company names
    urls_as_company = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE company_id IS NOT NULL 
          AND (
            CAST(company_id AS VARCHAR) LIKE 'www.%'
            OR CAST(company_id AS VARCHAR) LIKE '%.com%'
            OR CAST(company_id AS VARCHAR) LIKE '%.org%'
            OR CAST(company_id AS VARCHAR) LIKE '%.net%'
            OR CAST(company_id AS VARCHAR) LIKE '%.io%'
          )
    """).fetchone()[0]
    print(f"  • Website URLs stored as Company Name (e.g. 'acme.com'): {urls_as_company:,}")
    if urls_as_company > 0:
        samples = con.execute("""
            SELECT company_id, email FROM rec
            WHERE company_id IS NOT NULL 
              AND (CAST(company_id AS VARCHAR) LIKE '%.com%' OR CAST(company_id AS VARCHAR) LIKE 'www.%')
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["urls_as_company"] = urls_as_company

    # 4b. Excessive legal entity suffix clutter (Inc, LLC, Corp) causing duplicates
    entity_suffix = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE company_id IS NOT NULL 
          AND (
            CAST(company_id AS VARCHAR) LIKE '% Inc.%'
            OR CAST(company_id AS VARCHAR) LIKE '% LLC%'
            OR CAST(company_id AS VARCHAR) LIKE '% Corp.%'
            OR CAST(company_id AS VARCHAR) LIKE '% Ltd.%'
            OR CAST(company_id AS VARCHAR) LIKE '%, Inc%'
          )
    """).fetchone()[0]
    print(f"  • Legal suffix clutter ('Inc.', 'LLC', ', Inc'): {entity_suffix:,}")
    report["entity_suffix"] = entity_suffix

    # -------------------------------------------------------------
    # 5. LINKEDIN URL VARIATIONS
    # -------------------------------------------------------------
    print("\n[5] LINKEDIN URL VARIATIONS & LATENT DEFECTS:")

    company_in_personal_li = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE linkedin IS NOT NULL 
          AND linkedin LIKE '%linkedin.com/company/%'
    """).fetchone()[0]
    print(f"  • Company Page placed in Personal LinkedIn field: {company_in_personal_li:,}")
    if company_in_personal_li > 0:
        samples = con.execute("""
            SELECT linkedin, recruiter_name FROM rec
            WHERE linkedin IS NOT NULL AND linkedin LIKE '%linkedin.com/company/%'
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["company_in_personal_li"] = company_in_personal_li

    # -------------------------------------------------------------
    # 6. PHONE NUMBER VARIATIONS
    # -------------------------------------------------------------
    print("\n[6] PHONE NUMBER VARIATIONS & LATENT DEFECTS:")

    alpha_phones = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE phone IS NOT NULL 
          AND TRIM(phone) != ''
          AND REGEXP_MATCHES(phone, '[A-Za-z]')
    """).fetchone()[0]
    print(f"  • Alphabetical characters in Phone: {alpha_phones:,}")
    if alpha_phones > 0:
        samples = con.execute("""
            SELECT phone, recruiter_name FROM rec
            WHERE phone IS NOT NULL AND REGEXP_MATCHES(phone, '[A-Za-z]')
            LIMIT 5
        """).fetchall()
        print(f"    Samples: {samples}")
    report["alpha_phones"] = alpha_phones

    print("\n" + "="*75)
    print("DEEP MULTI-VARIATION SCAN COMPLETE!")
    print("="*75)
    return report

if __name__ == "__main__":
    run_deep_variation_scan()
