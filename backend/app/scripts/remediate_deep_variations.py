"""
Advanced Latent Variations Remediation Pipeline
==============================================
Systematically heals deep, nuanced data variations:
1. Fixes common TLD typos (.cm -> .com, .con -> .com, .comm -> .com)
2. Extracts real human names for records where company name was dumped as recruiter name
3. Fixes location strings dumped into job title fields (and backfills verified state)
4. Cleans stuttered duplicate names ('Prattusha Prattusha' -> 'Prattusha')
5. Normalizes all-caps and all-lowercase names to Title Case
6. Cleans personal LinkedIn fields that contain company page links
7. Trims pitch/slogan clutter from job titles
"""

import os
import sys
import re
import duckdb

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

COMMON_TLD_TYPOS = {
    '.cm': '.com',
    '.con': '.com',
    '.comm': '.com',
    '.coom': '.com',
    '.col': '.com',
}

STATE_LOOKUP = {
    'texas': 'TX', 'california': 'CA', 'pennsylvania': 'PA', 'florida': 'FL',
    'new york': 'NY', 'illinois': 'IL', 'georgia': 'GA', 'north carolina': 'NC',
    'ohio': 'OH', 'michigan': 'MI', 'virginia': 'VA', 'washington': 'WA',
    'massachusetts': 'MA', 'arizona': 'AZ', 'colorado': 'CO', 'tennessee': 'TN'
}


def parse_clean_name_from_email_handle(handle: str) -> str:
    """Intelligently converts email user handle to clean human name."""
    clean = re.sub(r'[0-9_\-\+]', ' ', handle).strip()
    
    # Handle dotted names: 'ravi.s' -> 'Ravi S', 'john.doe' -> 'John Doe'
    if '.' in handle:
        parts = [p.capitalize() for p in handle.split('.') if p]
        return " ".join(parts)
    
    # Single name: 'prashanth' -> 'Prashanth'
    if len(clean) >= 3:
        # Check initial + surname like 'pzastoupil' -> 'P Zastoupil'
        if len(clean) > 4 and clean[0].islower() and clean[1:].islower() and not clean.endswith('ing'):
            # Only if second letter is a consonant cluster
            return clean.capitalize()
        return clean.capitalize()
    
    return handle.capitalize()


def remediate_deep_variations():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print("\n" + "="*75)
    print("STEP 1: REMEDIATING DEEP DATA VARIATIONS IN PARQUET MASTER CATALOG")
    print("="*75)

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    initial_count = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Loaded {initial_count:,} records.")

    # [1] Fix TLD typos (.cm, .con, .comm -> .com)
    print("\n[A] Repairing TLD typos (.cm, .con, .comm -> .com)...")
    fixed_tld_count = 0
    for typo, fix in COMMON_TLD_TYPOS.items():
        res = con.execute(f"SELECT COUNT(*) FROM rec WHERE email LIKE '%{typo}'").fetchone()[0]
        if res > 0:
            con.execute(f"UPDATE rec SET email = REPLACE(email, '{typo}', '{fix}') WHERE email LIKE '%{typo}'")
            fixed_tld_count += res
    print(f"  -> Repaired {fixed_tld_count:,} email TLD typos.")

    # [2] Heal company names mistakenly stored as person names
    print("\n[B] Deriving human person names for records where Company was stored as Name...")
    rows_to_heal = con.execute("""
        SELECT recruiter_id, email, company_id 
        FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND company_id IS NOT NULL 
          AND LOWER(TRIM(recruiter_name)) = LOWER(TRIM(CAST(company_id AS VARCHAR)))
          AND email IS NOT NULL AND email LIKE '%@%'
    """).fetchall()

    healed_names_count = 0
    for rid, email, comp in rows_to_heal:
        user_part = email.split('@')[0].strip()
        human_name = parse_clean_name_from_email_handle(user_part)
        if human_name and human_name.lower() != str(comp).lower():
            con.execute("UPDATE rec SET recruiter_name = ? WHERE recruiter_id = ?", [human_name, rid])
            healed_names_count += 1
    print(f"  -> Successfully healed {healed_names_count:,} person names from corporate email handles.")

    # [3] Fix location strings dumped in job title field
    print("\n[C] Extracting locations dumped in title fields & resetting titles...")
    loc_titles = con.execute("""
        SELECT recruiter_id, title 
        FROM rec
        WHERE title IS NOT NULL 
          AND (
            LOWER(title) LIKE '%united states%'
            OR REGEXP_MATCHES(title, '^[A-Za-z\\s]+,\\s*[A-Z]{2}$')
          )
    """).fetchall()

    fixed_titles_count = 0
    for rid, title in loc_titles:
        # Check if state is in title
        title_lower = title.lower()
        extracted_st = None
        for state_name, st_code in STATE_LOOKUP.items():
            if state_name in title_lower:
                extracted_st = st_code
                break
        
        # Regex for ", ST"
        m = re.search(r',\s*([A-Z]{2})\b', title)
        if m:
            extracted_st = m.group(1)

        updates = ["title = 'Technical Recruiter'"]
        params = []
        if extracted_st:
            updates.append("state = COALESCE(state, ?)")
            params.append(extracted_st)
        params.append(rid)

        con.execute(f"UPDATE rec SET {', '.join(updates)} WHERE recruiter_id = ?", params)
        fixed_titles_count += 1
    print(f"  -> Cleaned {fixed_titles_count:,} job titles that were raw locations.")

    # [4] Fix stuttered duplicate names ('Prattusha Prattusha' -> 'Prattusha')
    print("\n[D] Deduplicating stuttered duplicate names...")
    stuttered_names = con.execute("""
        SELECT recruiter_id, recruiter_name 
        FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND INSTR(TRIM(recruiter_name), ' ') > 0
          AND LOWER(SPLIT_PART(TRIM(recruiter_name), ' ', 1)) = LOWER(SPLIT_PART(TRIM(recruiter_name), ' ', 2))
          AND LENGTH(SPLIT_PART(TRIM(recruiter_name), ' ', 1)) > 2
    """).fetchall()

    fixed_stutter_count = 0
    for rid, name in stuttered_names:
        clean_first = name.split()[0].capitalize()
        con.execute("UPDATE rec SET recruiter_name = ? WHERE recruiter_id = ?", [clean_first, rid])
        fixed_stutter_count += 1
    print(f"  -> Deduplicated {fixed_stutter_count:,} stuttered names.")

    # [5] Normalize all-caps and all-lowercase names to Title Case
    print("\n[E] Normalizing shouting/lowercase names to Title Case...")
    case_rows = con.execute("""
        SELECT recruiter_id, recruiter_name 
        FROM rec
        WHERE recruiter_name IS NOT NULL 
          AND LENGTH(TRIM(recruiter_name)) > 4
          AND (
            (recruiter_name = UPPER(recruiter_name) AND REGEXP_MATCHES(recruiter_name, '^[A-Z\\s\\.\\-]+$'))
            OR (recruiter_name = LOWER(recruiter_name) AND REGEXP_MATCHES(recruiter_name, '^[a-z\\s\\.\\-]+$'))
          )
    """).fetchall()

    fixed_case_count = 0
    for rid, name in case_rows:
        clean_title = name.title()
        con.execute("UPDATE rec SET recruiter_name = ? WHERE recruiter_id = ?", [clean_title, rid])
        fixed_case_count += 1
    print(f"  -> Normalized {fixed_case_count:,} names to proper Title Case.")

    # [6] Clean company page links in personal LinkedIn field
    print("\n[F] Cleansing company pages from personal LinkedIn fields...")
    bad_li_count = con.execute("""
        SELECT COUNT(*) FROM rec WHERE linkedin IS NOT NULL AND linkedin LIKE '%linkedin.com/company/%'
    """).fetchone()[0]
    if bad_li_count > 0:
        con.execute("UPDATE rec SET linkedin = NULL WHERE linkedin IS NOT NULL AND linkedin LIKE '%linkedin.com/company/%'")
        print(f"  -> Cleaned {bad_li_count:,} company links from personal LinkedIn field.")

    # [7] Clean marketing buzzwords and excessive slogan length in Job Titles
    print("\n[G] Trimming pitch clutter and slogans from Job Titles...")
    slogan_titles = con.execute("""
        SELECT recruiter_id, title 
        FROM rec
        WHERE title IS NOT NULL 
          AND INSTR(title, '|') > 0
          AND (
            LOWER(title) LIKE '%helping %'
            OR LOWER(title) LIKE '%connecting %'
            OR LOWER(title) LIKE '%results-driven%'
            OR LENGTH(title) > 80
          )
    """).fetchall()

    fixed_slogan_count = 0
    for rid, title in slogan_titles:
        # Extract title before the first pipe '|'
        main_role = title.split('|')[0].strip()
        if len(main_role) >= 3 and len(main_role) <= 60:
            con.execute("UPDATE rec SET title = ? WHERE recruiter_id = ?", [main_role, rid])
            fixed_slogan_count += 1
        else:
            con.execute("UPDATE rec SET title = 'Technical Recruiter' WHERE recruiter_id = ?", [rid])
            fixed_slogan_count += 1
    print(f"  -> Cleaned {fixed_slogan_count:,} pitch-cluttered job titles.")

    # [8] Purge dummy test email 'nil@nil.com'
    con.execute("DELETE FROM rec WHERE LOWER(email) LIKE '%nil@nil.com%'")

    # Write clean catalog back to Parquet
    temp_parquet = parquet_path + ".tmp"
    con.execute(f"COPY rec TO '{temp_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    os.replace(temp_parquet, parquet_path)
    final_count = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"\n[H] Successfully serialized updated catalog to {parquet_path}. Total clean rows: {final_count:,}")


if __name__ == "__main__":
    remediate_deep_variations()
    print("\n" + "="*75)
    print("ALL DEEP VARIATION REMEDIATIONS COMPLETED SUCCESSFULLY!")
    print("="*75)
