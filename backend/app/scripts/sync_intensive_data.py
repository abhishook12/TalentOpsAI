"""
Intensive Data Synchronization & Enrichment Engine
==================================================
Performs systemic synchronization across:
1. Parquet Master Catalog (444k+ records)
   - Resolves missing / noise company names using corporate email domains.
   - Resolves generic 'US' and missing states using Location regex + Colleague Consensus Dominant State.
2. PostgreSQL Master CRM (recruiters, companies)
   - Populates missing company domains (website / primary_domain) from verified dominant domains.
   - Populates missing company states from colleague aggregation.
   - Synchronizes recruiter states from company headquarters / colleague consensus.
"""

import os
import sys
import re
import duckdb
from typing import Dict, Tuple, Optional

# Add backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from app.database import SessionLocal
from sqlalchemy import text

US_STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}

STATE_NAME_TO_CODE = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'district of columbia': 'DC'
}

FREE_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'mail.com', 'zoho.com', 'protonmail.com', 'live.com'
}

NOISE_COMPANIES = {
    'linkedin', 'google', 'facebook', 'twitter', 'instagram', 'unknown',
    'n/a', 'na', 'none', 'null', 'missing', 'missing.local', 'independent staffing',
    'self employed', 'freelance', 'contractor', 'stealth', 'confidential'
}


def extract_state_from_text(text_val: Optional[str]) -> Optional[str]:
    """Extracts a valid US state code from location or raw text."""
    if not text_val:
        return None
    s = str(text_val).strip()
    if not s or s.upper() == 'US':
        return None

    # Check 2-letter code directly
    s_upper = s.upper()
    if s_upper in US_STATE_CODES:
        return s_upper

    # Check full state name
    s_lower = s.lower()
    for name, code in STATE_NAME_TO_CODE.items():
        if re.search(r'\b' + re.escape(name) + r'\b', s_lower):
            return code

    # Pattern like "City, ST" or "City, ST 12345"
    m = re.search(r',\s*([A-Za-z]{2})\b', s)
    if m:
        st = m.group(1).upper()
        if st in US_STATE_CODES:
            return st

    return None


def derive_company_from_email(email: Optional[str]) -> Optional[str]:
    """Infers clean company name from corporate email domain."""
    if not email or '@' not in email:
        return None
    domain = email.split('@')[1].lower().strip()
    if domain in FREE_DOMAINS or '.' not in domain:
        return None
    # Strip TLD and format nicely (e.g., 'teksystems.com' -> 'Teksystems')
    base = domain.split('.')[0]
    if len(base) <= 1:
        return None
    # Capitalize acronyms or normal words
    return base.capitalize()


def run_parquet_sync():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print(f"\n=======================================================")
    print(f"STEP 1: PARQUET MASTER CATALOG INTENSIVE SYNCHRONIZATION")
    print(f"=======================================================")
    
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    total_records = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Loaded {total_records:,} records into DuckDB memory.")

    # 1. Company Enrichment: Fix missing / noise company names from corporate email domains
    print("\n[A] Resolving missing & noise company names via corporate email domains...")
    free_domains_sql = ", ".join(f"'{d}'" for d in FREE_DOMAINS)
    noise_comps_sql = ", ".join(f"'{c}'" for c in NOISE_COMPANIES)

    before_noise = con.execute(f"""
        SELECT COUNT(*) FROM rec
        WHERE (company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ({noise_comps_sql}))
          AND email IS NOT NULL AND email LIKE '%@%'
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_domains_sql})
    """).fetchone()[0]

    con.execute(f"""
        UPDATE rec
        SET company_id = CONCAT(
            UPPER(SUBSTR(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1), 1, 1)),
            SUBSTR(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1), 2)
        )
        WHERE (company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ({noise_comps_sql}))
          AND email IS NOT NULL AND email LIKE '%@%'
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_domains_sql})
          AND LENGTH(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1)) > 1
    """)

    after_noise = con.execute(f"""
        SELECT COUNT(*) FROM rec
        WHERE (company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ({noise_comps_sql}))
          AND email IS NOT NULL AND email LIKE '%@%'
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_domains_sql})
    """).fetchone()[0]
    print(f"  -> Enriched {before_noise - after_noise:,} company names from corporate emails.")

    # 2. State Extraction from Location text
    print("\n[B] Extracting specific US states from Location text...")
    valid_states_sql = ", ".join(f"'{s}'" for s in US_STATE_CODES)
    
    before_loc_sync = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE state IS NULL OR TRIM(CAST(state AS VARCHAR)) = '' OR UPPER(TRIM(CAST(state AS VARCHAR))) = 'US'
    """).fetchone()[0]

    con.execute(f"""
        UPDATE rec
        SET state = UPPER(REGEXP_EXTRACT(location, ',\\s*([A-Za-z]{{2}})\\b', 1))
        WHERE (state IS NULL OR TRIM(CAST(state AS VARCHAR)) = '' OR UPPER(TRIM(CAST(state AS VARCHAR))) = 'US')
          AND location IS NOT NULL
          AND UPPER(REGEXP_EXTRACT(location, ',\\s*([A-Za-z]{{2}})\\b', 1)) IN ({valid_states_sql})
    """)

    after_loc_sync = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE state IS NULL OR TRIM(CAST(state AS VARCHAR)) = '' OR UPPER(TRIM(CAST(state AS VARCHAR))) = 'US'
    """).fetchone()[0]
    print(f"  -> Resolved {before_loc_sync - after_loc_sync:,} states directly from location strings.")

    # 3. Synchronize States using Colleague Consensus Dominant State per Company
    print("\n[C] Synchronizing remaining person states from Colleague Consensus Dominant State...")
    before_colleague_sync = after_loc_sync

    con.execute(f"""
        CREATE TABLE company_dom_state AS
        SELECT 
            company_id,
            MODE(UPPER(TRIM(CAST(state AS VARCHAR)))) as dom_state
        FROM rec
        WHERE state IS NOT NULL 
          AND LENGTH(TRIM(CAST(state AS VARCHAR))) = 2 
          AND UPPER(TRIM(CAST(state AS VARCHAR))) != 'US'
          AND UPPER(TRIM(CAST(state AS VARCHAR))) IN ({valid_states_sql})
          AND company_id IS NOT NULL 
          AND TRIM(CAST(company_id AS VARCHAR)) != ''
        GROUP BY company_id
    """)

    con.execute("""
        UPDATE rec
        SET state = cds.dom_state
        FROM company_dom_state cds
        WHERE rec.company_id = cds.company_id
          AND (rec.state IS NULL OR TRIM(CAST(rec.state AS VARCHAR)) = '' OR UPPER(TRIM(CAST(rec.state AS VARCHAR))) = 'US')
    """)

    after_colleague_sync = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE state IS NULL OR TRIM(CAST(state AS VARCHAR)) = '' OR UPPER(TRIM(CAST(state AS VARCHAR))) = 'US'
    """).fetchone()[0]

    print(f"  -> Resolved {before_colleague_sync - after_colleague_sync:,} person states from colleague consensus!")
    print(f"  -> Total person states synchronized: {before_loc_sync - after_colleague_sync:,}")

    # Write back to parquet atomically
    temp_parquet = parquet_path + ".tmp"
    con.execute(f"COPY rec TO '{temp_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    os.replace(temp_parquet, parquet_path)
    print(f"\n[D] Successfully serialized updated catalog to {parquet_path}")

    # Return company state and dominant domain maps for PostgreSQL sync
    company_dominant_state = {}
    cds_rows = con.execute("SELECT company_id, dom_state FROM company_dom_state").fetchall()
    for comp, dom_st in cds_rows:
        if comp and dom_st:
            company_dominant_state[str(comp).strip()] = dom_st

    company_dominant_domains = {}
    domain_rows = con.execute("""
        SELECT 
            company_id,
            MODE(LOWER(SPLIT_PART(email, '@', 2))) as dom
        FROM rec
        WHERE email IS NOT NULL 
          AND email LIKE '%@%'
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com')
          AND company_id IS NOT NULL
        GROUP BY company_id
    """).fetchall()

    for comp, dom in domain_rows:
        if comp and dom:
            company_dominant_domains[str(comp).strip()] = dom

    return company_dominant_state, company_dominant_domains


def run_postgresql_sync(company_dominant_state: Dict[str, str], company_dominant_domains: Dict[str, str]):
    print(f"\n=======================================================")
    print(f"STEP 2: POSTGRESQL CRM & RECRUITER STATE SYNCHRONIZATION")
    print(f"=======================================================")

    with SessionLocal() as db:
        # 1. Synchronize PostgreSQL Companies (website / domain & state)
        print("\n[A] Synchronizing PostgreSQL Companies with Dominant Domains & States...")
        comp_records = db.execute(text("SELECT company_id, company_name, state, website FROM companies")).mappings().fetchall()
        print(f"  -> Auditing {len(comp_records):,} PostgreSQL companies...")

        updated_comp_domain = 0
        updated_comp_state = 0
        comp_batch = []

        for comp in comp_records:
            cid = comp['company_id']
            cname = (comp['company_name'] or '').strip()
            curr_state = (comp['state'] or '').strip().upper()
            curr_site = (comp['website'] or '').strip()

            new_state = curr_state if (curr_state and curr_state != 'US') else None
            new_site = curr_site if curr_site else None

            changed = False
            if (not curr_state or curr_state == 'US') and cname in company_dominant_state:
                new_state = company_dominant_state[cname]
                updated_comp_state += 1
                changed = True

            if not curr_site and cname in company_dominant_domains:
                new_site = f"https://www.{company_dominant_domains[cname]}"
                updated_comp_domain += 1
                changed = True

            if changed:
                comp_batch.append({"cid": cid, "st": new_state, "site": new_site})

        if comp_batch:
            # Batch execute updates in chunks of 500
            for i in range(0, len(comp_batch), 500):
                chunk = comp_batch[i:i+500]
                db.execute(text("""
                    UPDATE companies 
                    SET state = COALESCE(:st, state), 
                        website = COALESCE(:site, website), 
                        updated_at = NOW() 
                    WHERE company_id = :cid
                """), chunk)
            db.commit()

        print(f"  -> Synchronized Company Domains: {updated_comp_domain:,}")
        print(f"  -> Synchronized Company States: {updated_comp_state:,}")

        # 2. Synchronize PostgreSQL Recruiters (state from linked company or consensus)
        print("\n[B] Synchronizing PostgreSQL Recruiters with Company States...")
        rec_records = db.execute(text("""
            SELECT r.recruiter_id, r.state, r.company_id, c.company_name, c.state as comp_state
            FROM recruiters r
            LEFT JOIN companies c ON r.company_id = c.company_id
            WHERE r.state IS NULL 
               OR r.state = '' 
               OR UPPER(r.state) = 'US'
        """)).mappings().fetchall()

        print(f"  -> Found {len(rec_records):,} PostgreSQL recruiters with missing or generic state.")
        rec_batch = []
        for r in rec_records:
            rid = r['recruiter_id']
            c_state = (r['comp_state'] or '').strip().upper()
            cname = (r['company_name'] or '').strip()

            target_state = None
            if c_state and c_state in US_STATE_CODES:
                target_state = c_state
            elif cname and cname in company_dominant_state:
                target_state = company_dominant_state[cname]

            if target_state:
                rec_batch.append({"st": target_state, "rid": rid})

        if rec_batch:
            for i in range(0, len(rec_batch), 500):
                chunk = rec_batch[i:i+500]
                db.execute(text("""
                    UPDATE recruiters 
                    SET state = :st, state_source = 'company_colleague_sync', state_confidence = 'high', updated_at = NOW()
                    WHERE recruiter_id = :rid
                """), chunk)
            db.commit()
            updated_rec_state = len(rec_batch)
        else:
            updated_rec_state = 0

        print(f"  -> Synchronized Recruiter States from Company: {updated_rec_state:,}")

        # 3. Link recruiters with missing company_id via email domain
        missing_comp_rows = db.execute(text("""
            SELECT recruiter_id, email FROM recruiters WHERE company_id IS NULL AND email LIKE '%@%'
        """)).mappings().fetchall()

        linked_count = 0
        for r in missing_comp_rows:
            rid = r['recruiter_id']
            email = r['email']
            domain = email.split('@')[1].lower().strip()
            if domain in FREE_DOMAINS:
                continue
            
            comp_match = db.execute(text("""
                SELECT company_id, state 
                FROM companies 
                WHERE website ILIKE :dom_pattern 
                   OR normalized_company_name ILIKE :base_pattern
                LIMIT 1
            """), {
                "dom_pattern": f"%{domain}%",
                "base_pattern": f"%{domain.split('.')[0]}%"
            }).mappings().first()

            if comp_match:
                cid = comp_match['company_id']
                c_st = comp_match['state']
                db.execute(text("""
                    UPDATE recruiters 
                    SET company_id = :cid, 
                        state = COALESCE(state, :st),
                        updated_at = NOW()
                    WHERE recruiter_id = :rid
                """), {"cid": cid, "st": c_st, "rid": rid})
                linked_count += 1

        db.commit()
        print(f"  -> Linked Recruiters to Companies via Corporate Email Domain: {linked_count}")


if __name__ == "__main__":
    comp_states, comp_domains = run_parquet_sync()
    run_postgresql_sync(comp_states, comp_domains)
    print("\n=======================================================")
    print("DATA SYNCHRONIZATION AND ENRICHMENT COMPLETE!")
    print("=======================================================")
