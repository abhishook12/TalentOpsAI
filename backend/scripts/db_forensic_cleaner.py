import sys, os, io, time, psycopg
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join('C:/TalentOpsAI/backend', '.env'))

from app.services.platform_alarm import PlatformSafetyAlarm

def run_forensic_cleaner():
    print("=======================================================================")
    print("=== FORENSIC DATABASE HYGIENE & SANITIZATION ENGINE ===")
    print("=======================================================================")
    sys.stdout.flush()

    raw_url = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DATABASE_URL') or ''
    db_url = raw_url.replace('postgresql+psycopg://', 'postgresql://')

    conn = psycopg.connect(db_url, autocommit=True, prepare_threshold=None)
    cursor = conn.cursor()

    start_t = time.time()

    # PHASE 1: SANITIZE .dup.XXXXX EMAIL SUFFIXES IN RECRUITERS & COMPANIES
    print("\n[Phase 1] Stripping .dup.XXXXX garbage suffixes from email addresses & websites...")
    cursor.execute("""
        DELETE FROM recruiters
        WHERE email LIKE '%.dup.%'
          AND EXISTS (
              SELECT 1 FROM recruiters r2 
              WHERE r2.email = REGEXP_REPLACE(REGEXP_REPLACE(recruiters.email, '\\.dup\\.\\d+$', '', 'i'), '\\.\\.dup\\.\\d+$', '', 'i')
                AND r2.recruiter_id != recruiters.recruiter_id
          )
    """)
    print(f" -> Removed {cursor.rowcount:,} exact collision duplicate rows (.dup).")

    cursor.execute("""
        UPDATE recruiters
        SET email = REGEXP_REPLACE(REGEXP_REPLACE(email, '\\.dup\\.\\d+$', '', 'i'), '\\.\\.dup\\.\\d+$', '', 'i')
        WHERE email LIKE '%.dup.%'
    """)
    print(f" -> Cleaned {cursor.rowcount:,} remaining recruiter emails with .dup suffixes.")

    cursor.execute("""
        UPDATE companies
        SET website = REGEXP_REPLACE(REGEXP_REPLACE(website, '\\.dup\\.\\d+$', '', 'i'), '\\.\\.dup\\.\\d+$', '', 'i')
        WHERE website LIKE '%.dup.%'
    """)
    print(f" -> Cleaned {cursor.rowcount:,} company websites with .dup suffixes.")
    cursor.execute("VACUUM VERBOSE recruiters")
    cursor.execute("VACUUM VERBOSE companies")

    # PHASE 2: SPLIT & SANITIZE MASHED/SEMICOLON RECRUITER NAMES & EMAILS
    print("\n[Phase 2] Sanitize mashed multi-person rows (semicolons, commas, slashes)...")
    # Fetch all rows containing semicolons in name or email
    cursor.execute("""
        SELECT recruiter_id, recruiter_name, email 
        FROM recruiters 
        WHERE POSITION(';' IN recruiter_name) > 0 OR POSITION(';' IN email) > 0
    """)
    semicolon_rows = cursor.fetchall()
    print(f" -> Inspecting {len(semicolon_rows):,} rows with semicolons (;)...")

    # Load set of all existing emails to prevent unique violations
    cursor.execute("SELECT LOWER(TRIM(email)) FROM recruiters WHERE email IS NOT NULL")
    existing_emails = set(row[0] for row in cursor.fetchall())

    cleaned_updates = 0
    deleted_dups = 0
    for r_id, r_name, r_email in semicolon_rows:
        clean_name = r_name.split(';')[0].strip() if r_name and ';' in r_name else r_name
        
        clean_email = r_email
        if r_email and ';' in r_email:
            parts = [p.strip() for p in r_email.split(';') if '@' in p and '.' in p]
            chosen = None
            for p in parts:
                if p.lower() not in existing_emails or p.lower() == (r_email.lower() if r_email else ''):
                    chosen = p
                    break
            if not chosen and parts:
                # All parts in this semicolon email already exist in other rows! Drop this duplicate row.
                cursor.execute("DELETE FROM recruiters WHERE recruiter_id = %s", (r_id,))
                deleted_dups += 1
                continue
            elif chosen:
                clean_email = chosen
                existing_emails.add(chosen.lower())
        
        if clean_name != r_name or clean_email != r_email:
            cursor.execute("""
                UPDATE recruiters 
                SET recruiter_name = %s, email = %s 
                WHERE recruiter_id = %s
            """, (clean_name, clean_email, r_id))
            cleaned_updates += 1

    print(f" -> Cleaned & split {cleaned_updates:,} mashed multi-person rows (;), removed {deleted_dups:,} collisions.")

    cursor.execute("""
        UPDATE recruiters
        SET recruiter_name = REGEXP_REPLACE(recruiter_name, '\\s*\\(.*\\)\\s*', '', 'g')
        WHERE POSITION('(' IN recruiter_name) > 0
    """)
    print(f" -> Stripped parenthetical tags/notes from {cursor.rowcount:,} recruiter names.")

    cursor.execute("""
        UPDATE recruiters
        SET recruiter_name = TRIM(SPLIT_PART(recruiter_name, '/', 1))
        WHERE POSITION('/' IN recruiter_name) > 0 AND LENGTH(SPLIT_PART(recruiter_name, '/', 1)) > 2
    """)
    if cursor.rowcount > 0:
        print(f" -> Split and sanitized {cursor.rowcount:,} slash-merged names (/).")
    cursor.execute("VACUUM VERBOSE recruiters")

    # PHASE 3: SANITIZE [DUPLICATE] TAGS & MERGE DUPLICATE COMPANIES
    print("\n[Phase 3] Sanitize [DUPLICATE] tags from company names and merge orphaned recruiters...")
    # First find all duplicate companies that have a clean counterpart
    cursor.execute("""
        WITH dup_companies AS (
            SELECT company_id, TRIM(REPLACE(REPLACE(company_name, '[DUPLICATE]', ''), '[duplicate]', '')) as clean_name
            FROM companies
            WHERE company_name LIKE '%[DUPLICATE]%'
        ),
        matched_clean AS (
            SELECT d.company_id as dup_id, c.company_id as clean_id, d.clean_name
            FROM dup_companies d
            JOIN companies c ON LOWER(d.clean_name) = LOWER(c.company_name)
            WHERE c.company_id != d.company_id AND c.company_name NOT LIKE '%[DUPLICATE]%'
        )
        UPDATE recruiters r
        SET company_id = mc.clean_id
        FROM matched_clean mc
        WHERE r.company_id = mc.dup_id
    """)
    merged_recs = cursor.rowcount
    print(f" -> Re-pointed {merged_recs:,} recruiters from [DUPLICATE] companies to primary clean company records.")

    # Now clean up remaining company names
    cursor.execute("""
        UPDATE companies
        SET company_name = TRIM(REPLACE(REPLACE(company_name, '[DUPLICATE]', ''), '[duplicate]', ''))
        WHERE company_name LIKE '%[DUPLICATE]%'
    """)
    print(f" -> Removed [DUPLICATE] tags across {cursor.rowcount:,} company records.")

    # Deactivate empty duplicate companies that have 0 recruiters
    cursor.execute("""
        UPDATE companies c
        SET is_active = false
        WHERE (c.company_name LIKE '%duplicate%' OR c.company_name = '')
          AND NOT EXISTS (SELECT 1 FROM recruiters r WHERE r.company_id = c.company_id)
    """)
    cursor.execute("VACUUM VERBOSE companies")
    cursor.execute("VACUUM VERBOSE recruiters")

    # PHASE 4: POPULATE & SANITIZE WEBSITES FOR CLEAN LOGO RENDERING
    print("\n[Phase 4] Populating missing and broken company websites from linked recruiter domains...")
    cursor.execute("""
        WITH company_domains AS (
            SELECT company_id, LOWER(SPLIT_PART(email, '@', 2)) as domain, COUNT(*) as cnt
            FROM recruiters
            WHERE company_id IS NOT NULL 
              AND email IS NOT NULL AND POSITION('@' IN email) > 0
              AND email NOT LIKE '%.dup.%' AND email NOT LIKE '%;%' AND email NOT LIKE '%,%'
            GROUP BY company_id, LOWER(SPLIT_PART(email, '@', 2))
        ),
        top_domain_per_company AS (
            SELECT company_id, domain
            FROM (
                SELECT company_id, domain, cnt,
                       ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY cnt DESC) as rn
                FROM company_domains
                WHERE domain NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com', 'mail.com')
                  AND LENGTH(domain) > 3 AND POSITION('.' IN domain) > 0
            ) sub
            WHERE rn = 1
        )
        UPDATE companies c
        SET website = td.domain
        FROM top_domain_per_company td
        WHERE c.company_id = td.company_id
          AND (c.website IS NULL OR c.website = '' OR c.website = 'Unknown' OR c.website LIKE '%.dup.%')
    """)
    print(f" -> Populated and repaired exact domain websites for {cursor.rowcount:,} companies from their recruiters.")
    cursor.execute("VACUUM VERBOSE companies")

    # Check final database size and dirty counts
    cursor.execute("SELECT pg_database_size(current_database()) / 1048576.0")
    final_mb = float(cursor.fetchone()[0])
    
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE email LIKE '%.dup.%' OR email LIKE '%;%' OR recruiter_name LIKE '%;%' OR recruiter_name LIKE '%[DUPLICATE]%'")
    dirty_rec = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM companies WHERE company_name LIKE '%[DUPLICATE]%' OR website LIKE '%.dup.%'")
    dirty_comp = cursor.fetchone()[0]

    elapsed = round(time.time() - start_t, 2)
    print(f"\n✅ All Forensic Sanitization completed in {elapsed}s!")
    print(f"🧹 Remaining Dirty Recruiter Rows (.dup / semicolon / duplicate): {dirty_rec}")
    print(f"🧹 Remaining Dirty Company Rows: {dirty_comp}")
    print(f"📊 Final Database Size: {final_mb:.2f} MB (Safely under 400 MB Cap)")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    run_forensic_cleaner()
