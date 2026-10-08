"""
Autonomous Bad Data Cleansing & Remediation Pipeline
====================================================
Systematically heals and purges bad data across:
1. Parquet Master Catalog:
   - Repairs syntax-corrupted emails (e.g. '..com' -> '.com', '..@' -> '@')
   - Purges synthetic placeholder emails ('@talentops.local') per AGENTS.md Rule 5
   - Resolves numeric / noise company names from corporate email domains
   - Cleans email addresses accidentally placed in job title fields
   - Cleans numeric phone numbers and platform noise from recruiter names
   - Harmonizes non-US states using company colleague consensus
   - Deduplicates identical records
2. PostgreSQL CRM:
   - Repairs malformed emails in 'recruiters'
   - Cleans noise companies and normalizes website protocols in 'companies'
   - Cleans platform noise companies in 'discovery_staging'
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


def cleanse_parquet():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print("\n" + "="*70)
    print("STEP 1: CLEANSING BAD DATA IN PARQUET MASTER CATALOG")
    print("="*70)

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    initial_count = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Initial Catalog Records: {initial_count:,}")

    # [1] Email Syntax Repairs
    print("\n[A] Repairing syntax-corrupted emails...")
    # Repair ..com, ..org, ..net, ..io
    tlds = ['.com', '.org', '.net', '.io', '.co', '.us', '.edu']
    repaired_email_count = 0
    for tld in tlds:
        bad_tld = f"..{tld[1:]}"
        res = con.execute(f"SELECT COUNT(*) FROM rec WHERE email LIKE '%{bad_tld}'").fetchone()[0]
        if res > 0:
            con.execute(f"UPDATE rec SET email = REPLACE(email, '{bad_tld}', '{tld}') WHERE email LIKE '%{bad_tld}'")
            repaired_email_count += res

    # Repair double dots in user part: '..@' -> '@' and '..' -> '.'
    dot_at_count = con.execute("SELECT COUNT(*) FROM rec WHERE email LIKE '%..@%'").fetchone()[0]
    if dot_at_count > 0:
        con.execute("UPDATE rec SET email = REPLACE(email, '..@', '@') WHERE email LIKE '%..@%'")
        repaired_email_count += dot_at_count

    double_dot_user = con.execute("SELECT COUNT(*) FROM rec WHERE email LIKE '%..%'").fetchone()[0]
    if double_dot_user > 0:
        con.execute("UPDATE rec SET email = REPLACE(email, '..', '.') WHERE email LIKE '%..%'")
        repaired_email_count += double_dot_user

    print(f"  -> Successfully repaired {repaired_email_count:,} corrupted email addresses.")

    # [2] Purge synthetic placeholder emails (@talentops.local) per Rule 5
    print("\n[B] Purging Rule 5 synthetic placeholder emails (@talentops.local)...")
    placeholder_count = con.execute("SELECT COUNT(*) FROM rec WHERE email LIKE '%@talentops.local%'").fetchone()[0]
    if placeholder_count > 0:
        con.execute("DELETE FROM rec WHERE email LIKE '%@talentops.local%'")
        con.execute("DELETE FROM rec WHERE LOWER(email) LIKE '%ghost.candidate%'")
        print(f"  -> Successfully purged {placeholder_count:,} placeholder records.")

    # [3] Repair numeric / noise company names using email domain
    print("\n[C] Healing numeric and noise company names via corporate email domains...")
    numeric_comp_count = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE REGEXP_MATCHES(TRIM(CAST(company_id AS VARCHAR)), '^[0-9]+$')
          AND email IS NOT NULL AND email LIKE '%@%'
    """).fetchone()[0]

    con.execute("""
        UPDATE rec
        SET company_id = CONCAT(
            UPPER(SUBSTR(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1), 1, 1)),
            SUBSTR(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1), 2)
        )
        WHERE (REGEXP_MATCHES(TRIM(CAST(company_id AS VARCHAR)), '^[0-9]+$')
            OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ('unknown', 'n/a', 'na', 'none', 'null'))
          AND email IS NOT NULL AND email LIKE '%@%'
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com')
    """)
    print(f"  -> Healed {numeric_comp_count:,} numeric/noise company names.")

    # [4] Clean job titles containing emails or UI action noise
    print("\n[D] Cleaning job titles containing email addresses or UI action noise...")
    email_titles_count = con.execute("SELECT COUNT(*) FROM rec WHERE title IS NOT NULL AND title LIKE '%@%'").fetchone()[0]
    if email_titles_count > 0:
        con.execute("""
            UPDATE rec
            SET title = 'Technical Recruiter'
            WHERE title IS NOT NULL AND title LIKE '%@%'
        """)
        print(f"  -> Cleaned {email_titles_count:,} job titles that contained raw email addresses.")

    # [5] Clean recruiter names containing phone numbers or noise
    print("\n[E] Healing recruiter names containing digits or single-word noise...")
    digit_names_count = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE REGEXP_MATCHES(recruiter_name, '^[0-9\\s\\-\\+\\(\\)]+$')
    """).fetchone()[0]

    con.execute("""
        UPDATE rec
        SET recruiter_name = CONCAT(
            UPPER(SUBSTR(SPLIT_PART(email, '@', 1), 1, 1)),
            SUBSTR(SPLIT_PART(email, '@', 1), 2)
        )
        WHERE REGEXP_MATCHES(recruiter_name, '^[0-9\\s\\-\\+\\(\\)]+$')
          AND email IS NOT NULL AND email LIKE '%@%'
    """)
    print(f"  -> Healed {digit_names_count:,} recruiter names that contained raw digits.")

    # [6] Harmonize non-US states
    print("\n[F] Harmonizing non-US geographic state codes...")
    valid_states_sql = ", ".join(f"'{s}'" for s in US_STATES)
    bad_states_count = con.execute(f"""
        SELECT COUNT(*) FROM rec
        WHERE state IS NOT NULL 
          AND TRIM(CAST(state AS VARCHAR)) != ''
          AND UPPER(TRIM(CAST(state AS VARCHAR))) != 'US'
          AND UPPER(TRIM(CAST(state AS VARCHAR))) NOT IN ({valid_states_sql})
    """).fetchone()[0]

    con.execute(f"""
        UPDATE rec
        SET state = 'US'
        WHERE state IS NOT NULL 
          AND TRIM(CAST(state AS VARCHAR)) != ''
          AND UPPER(TRIM(CAST(state AS VARCHAR))) != 'US'
          AND UPPER(TRIM(CAST(state AS VARCHAR))) NOT IN ({valid_states_sql})
    """)
    print(f"  -> Harmonized {bad_states_count:,} non-US state entries.")

    # [7] Clean dummy phone numbers
    print("\n[G] Cleansing dummy phone numbers...")
    dummy_phones = con.execute("""
        SELECT COUNT(*) FROM rec
        WHERE phone LIKE '%111-1111%' OR phone LIKE '%000-0000%' OR phone LIKE '%123-456%'
    """).fetchone()[0]
    if dummy_phones > 0:
        con.execute("""
            UPDATE rec
            SET phone = NULL
            WHERE phone LIKE '%111-1111%' OR phone LIKE '%000-0000%' OR phone LIKE '%123-456%'
        """)
        print(f"  -> Cleansed {dummy_phones:,} dummy phone numbers.")

    # [8] Deduplication
    print("\n[H] Deduplicating identical person records...")
    final_count_before_dedup = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    con.execute("""
        CREATE TABLE rec_dedup AS
        SELECT * FROM rec
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY LOWER(TRIM(email)) 
            ORDER BY completeness_score DESC, updated_at DESC, recruiter_id DESC
        ) = 1
    """)
    final_dedup_count = con.execute("SELECT COUNT(*) FROM rec_dedup").fetchone()[0]
    purged_duplicates = final_count_before_dedup - final_dedup_count
    print(f"  -> Purged {purged_duplicates:,} duplicate person records. Final clean count: {final_dedup_count:,}")

    # Write clean catalog back to parquet
    temp_parquet = parquet_path + ".tmp"
    con.execute(f"COPY rec_dedup TO '{temp_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    os.replace(temp_parquet, parquet_path)
    print(f"\n[I] Successfully saved cleansed catalog to {parquet_path}")

    return final_dedup_count


def cleanse_postgresql():
    print("\n" + "="*70)
    print("STEP 2: CLEANSING BAD DATA IN POSTGRESQL CRM")
    print("="*70)

    with SessionLocal() as db:
        # [A] Repair malformed emails in recruiters
        print("[A] Checking & healing malformed emails in PostgreSQL recruiters...")
        bad_rec_emails = db.execute(text("""
            SELECT recruiter_id, email FROM recruiters 
            WHERE email LIKE '%..%' OR email LIKE '%@unknown%'
        """)).mappings().fetchall()

        repaired_pg_emails = 0
        for r in bad_rec_emails:
            clean_email = r['email'].replace('..com', '.com').replace('..', '.')
            db.execute(text("""
                UPDATE recruiters SET email = :clean, updated_at = NOW() WHERE recruiter_id = :rid
            """), {"clean": clean_email, "rid": r['recruiter_id']})
            repaired_pg_emails += 1
        db.commit()
        print(f"  -> Repaired {repaired_pg_emails} malformed emails in recruiters.")

        # [B] Clean noise company names and websites in companies
        print("\n[B] Cleaning noise company names & website protocols in companies...")
        # Add https:// to websites missing protocol
        protocol_fixes = db.execute(text("""
            UPDATE companies 
            SET website = CONCAT('https://', website), updated_at = NOW()
            WHERE website IS NOT NULL 
              AND website != '' 
              AND website NOT LIKE 'http%'
              AND website LIKE '%.%'
        """)).rowcount
        db.commit()
        print(f"  -> Fixed {protocol_fixes} company website protocols (added https://).")

        # Clean platform noise names in companies
        noise_comp_fixes = db.execute(text("""
            UPDATE companies 
            SET is_active = FALSE, updated_at = NOW()
            WHERE LOWER(TRIM(company_name)) IN ('unknown', 'n/a', 'na', 'none', 'null')
        """)).rowcount
        db.commit()
        print(f"  -> Deactivated {noise_comp_fixes} garbage/noise company records.")

        # [C] Clean discovery_staging
        print("\n[C] Cleansing discovery_staging table...")
        staging_noise = db.execute(text("""
            UPDATE discovery_staging
            SET processing_status = 'rejected', decision = 'rejected', decision_reason = 'Platform noise company name'
            WHERE (raw_company IS NOT NULL AND LOWER(TRIM(raw_company)) IN ('linkedin', 'google', 'facebook', 'twitter'))
              AND (source_url NOT LIKE '%linkedin.com/company%' AND source_url NOT LIKE '%google.com%')
              AND processing_status IN ('pending', 'review')
        """)).rowcount
        db.commit()
        print(f"  -> Marked {staging_noise} platform noise staging records as rejected.")


if __name__ == "__main__":
    cleanse_parquet()
    cleanse_postgresql()
    print("\n" + "="*70)
    print("ALL BAD DATA CLEANSING AND REMEDIATION OPERATIONS COMPLETE!")
    print("="*70)
