import os
import time
import psycopg
from dotenv import load_dotenv

def run_phase3_enrichment():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SET statement_timeout = 0;")

    print("=" * 80)
    print("MASS FREE ENRICHMENT ENGINE PHASE 3 (STRUCTURAL & RELATIONAL COMPLETION)")
    print("=" * 80)
    start_total = time.time()

    def update_batched(query, params, batch_size=25000, desc=""):
        total_updated = 0
        while True:
            batched_query = f"""
                WITH batch AS (
                    {query}
                    LIMIT {batch_size}
                )
                UPDATE {params['table']} t
                SET {params['set_clause']}
                FROM batch
                WHERE t.{params['pk']} = batch.{params['pk']}
            """
            cursor.execute(batched_query, params.get('args', ()))
            rows = cursor.rowcount
            conn.commit()
            total_updated += rows
            if rows < batch_size:
                break
        print(f" -> {desc}: {total_updated:,} rows updated.")
        return total_updated

    # =========================================================================
    # ITEM 1: Populate Recruiter canonical_company_id from company_id
    # =========================================================================
    print("\n[Item 1/8] Populating Recruiter canonical_company_id across missing records...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT recruiter_id, company_id as new_cid
            FROM recruiters
            WHERE canonical_company_id IS NULL AND company_id IS NOT NULL
        """,
        params={'table': 'recruiters', 'pk': 'recruiter_id', 'set_clause': 'canonical_company_id = batch.new_cid'},
        batch_size=25000,
        desc="Canonical Company IDs linked"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 2: Populate Recruiter is_active flag
    # =========================================================================
    print("\n[Item 2/8] Setting default is_active = true across unflagged recruiters...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT recruiter_id
            FROM recruiters
            WHERE is_active IS NULL
        """,
        params={'table': 'recruiters', 'pk': 'recruiter_id', 'set_clause': 'is_active = true'},
        batch_size=25000,
        desc="Recruiters marked is_active = true"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 3: Populate Recruiter normalized_city
    # =========================================================================
    print("\n[Item 3/8] Normalizing city strings into normalized_city column...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT recruiter_id, LEFT(LOWER(TRIM(location)), 140) as norm_loc
            FROM recruiters
            WHERE (normalized_city IS NULL OR normalized_city = '')
              AND location IS NOT NULL AND location != '' AND LOWER(location) NOT IN ('null','n/a','none','unknown')
        """,
        params={'table': 'recruiters', 'pk': 'recruiter_id', 'set_clause': 'normalized_city = batch.norm_loc'},
        batch_size=25000,
        desc="Normalized cities populated"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 4: Populate Recruiter normalized_recruiter_name
    # =========================================================================
    print("\n[Item 4/8] Normalizing recruiter names into normalized_recruiter_name...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT recruiter_id, LEFT(LOWER(TRIM(recruiter_name)), 200) as norm_name
            FROM recruiters
            WHERE (normalized_recruiter_name IS NULL OR normalized_recruiter_name = '')
              AND recruiter_name IS NOT NULL AND recruiter_name != ''
        """,
        params={'table': 'recruiters', 'pk': 'recruiter_id', 'set_clause': 'normalized_recruiter_name = batch.norm_name'},
        batch_size=25000,
        desc="Normalized recruiter names populated"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 5: Copy Company location to Recruiter location where missing
    # =========================================================================
    print("\n[Item 5/8] Copying Company HQ location to recruiters missing city...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT r.recruiter_id, LEFT(c.location, 200) as hq_loc
            FROM recruiters r
            JOIN companies c ON r.company_id = c.company_id
            WHERE (r.location IS NULL OR r.location = '' OR LOWER(r.location) IN ('null','n/a','none'))
              AND c.location IS NOT NULL AND c.location != '' AND LOWER(c.location) NOT IN ('null','n/a','none')
        """,
        params={'table': 'recruiters', 'pk': 'recruiter_id', 'set_clause': 'location = batch.hq_loc, normalized_city = LEFT(LOWER(TRIM(batch.hq_loc)), 140)'},
        batch_size=25000,
        desc="Recruiter locations synced with company HQ"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 6: Compute Company trust_score across missing companies
    # =========================================================================
    print("\n[Item 6/8] Computing Company Trust Score where missing or 0...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT company_id,
            LEAST(100, GREATEST(0,
                CASE WHEN website IS NOT NULL AND website != '' AND LOWER(website) NOT IN ('null','n/a','none') THEN 35 ELSE 0 END +
                CASE WHEN state IS NOT NULL AND state != '' AND LOWER(state) NOT IN ('null','n/a','none') THEN 25 ELSE 0 END +
                CASE WHEN location IS NOT NULL AND location != '' AND LOWER(location) NOT IN ('null','n/a','none') THEN 20 ELSE 0 END +
                CASE WHEN email_pattern IS NOT NULL AND email_pattern != '' AND LOWER(email_pattern) NOT IN ('null','n/a','none') THEN 20 ELSE 0 END
            )) as calc_trust
            FROM companies
            WHERE trust_score IS NULL OR trust_score = 0
        """,
        params={'table': 'companies', 'pk': 'company_id', 'set_clause': 'trust_score = batch.calc_trust'},
        batch_size=25000,
        desc="Company Trust Score computed"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 7: Populate Company normalized_company_name
    # =========================================================================
    print("\n[Item 7/8] Normalizing company names into normalized_company_name...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT company_id, LEFT(LOWER(TRIM(company_name)), 200) as norm_cname
            FROM companies
            WHERE (normalized_company_name IS NULL OR normalized_company_name = '')
              AND company_name IS NOT NULL AND company_name != ''
        """,
        params={'table': 'companies', 'pk': 'company_id', 'set_clause': 'normalized_company_name = batch.norm_cname'},
        batch_size=25000,
        desc="Normalized company names populated"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 8: Detect Corporate Email Patterns from single-recruiter companies
    # =========================================================================
    print("\n[Item 8/8] Detecting Email Patterns for single-recruiter corporate domains...")
    t0 = time.time()
    cursor.execute("""
        UPDATE companies c
        SET email_pattern = sub.detected_pattern
        FROM (
            SELECT r.company_id,
                CASE
                    WHEN LOWER(r.email) LIKE LOWER(SPLIT_PART(r.recruiter_name, ' ', 1)) || '.' || LOWER(SPLIT_PART(r.recruiter_name, ' ', 2)) || '@%' THEN '{first}.{last}'
                    WHEN LOWER(r.email) LIKE LOWER(SPLIT_PART(r.recruiter_name, ' ', 1)) || LOWER(SPLIT_PART(r.recruiter_name, ' ', 2)) || '@%' THEN '{first}{last}'
                    WHEN LOWER(r.email) LIKE LOWER(LEFT(SPLIT_PART(r.recruiter_name, ' ', 1), 1)) || LOWER(SPLIT_PART(r.recruiter_name, ' ', 2)) || '@%' THEN '{f}{last}'
                    WHEN LOWER(r.email) LIKE LOWER(SPLIT_PART(r.recruiter_name, ' ', 1)) || '@%' THEN '{first}'
                END as detected_pattern
            FROM recruiters r
            JOIN companies comp ON r.company_id = comp.company_id
            WHERE (comp.email_pattern IS NULL OR comp.email_pattern = '' OR LOWER(comp.email_pattern) IN ('null','n/a','none'))
              AND r.email IS NOT NULL AND r.email != '' AND r.email NOT LIKE 'scrubbed-%' AND r.email LIKE '%@%'
              AND r.recruiter_name IS NOT NULL AND r.recruiter_name LIKE '% %'
              AND LENGTH(SPLIT_PART(r.recruiter_name, ' ', 1)) >= 2 AND LENGTH(SPLIT_PART(r.recruiter_name, ' ', 2)) >= 2
              AND LOWER(SPLIT_PART(r.email, '@', 2)) NOT IN ('gmail.com','yahoo.com','outlook.com','hotmail.com','aol.com','icloud.com','msn.com')
        ) sub
        WHERE c.company_id = sub.company_id
          AND sub.detected_pattern IS NOT NULL
          AND (c.email_pattern IS NULL OR c.email_pattern = '' OR LOWER(c.email_pattern) IN ('null','n/a','none'))
    """)
    print(f" -> Detected and filled corporate email patterns for {cursor.rowcount:,} additional companies in {time.time()-t0:.1f}s.")
    conn.commit()

    # =========================================================================
    # FINAL: STRICT VACUUM FULL & SIZE VERIFICATION
    # =========================================================================
    print("\n[Final] Executing VACUUM FULL to enforce hard <400 MB Rule 7 limit...")
    t0 = time.time()
    conn.autocommit = True
    cursor.execute("VACUUM FULL recruiters")
    cursor.execute("VACUUM FULL companies")
    cursor.execute("SELECT pg_database_size('postgres') / 1048576.0")
    db_size = cursor.fetchone()[0]
    print(f" -> VACUUM FULL complete in {time.time()-t0:.1f}s. Final DB Size: {db_size:.2f} MB / 400 MB")
    print("=" * 80)
    print(f"MASS FREE ENRICHMENT PHASE 3 COMPLETE IN {time.time()-start_total:.1f}s!")
    print("=" * 80)

if __name__ == '__main__':
    run_phase3_enrichment()
