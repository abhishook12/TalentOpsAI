import os
import time
import psycopg
from dotenv import load_dotenv

def run_phase4_enrichment():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SET statement_timeout = 0;")

    print("=" * 80)
    print("MASS FREE ENRICHMENT ENGINE PHASE 4 (SINGLE-PASS HIGH-SPEED SCORING)")
    print("=" * 80)
    start_total = time.time()

    # =========================================================================
    # ITEM 1: Classify Scrubbed Placeholder Emails (Single-Pass)
    # =========================================================================
    print("\n[Item 1/6] Classifying scrubbed placeholder emails...")
    t0 = time.time()
    cursor.execute("""
        UPDATE recruiters
        SET email_status = 'scrubbed_placeholder',
            email_confidence = 0,
            email_source = 'forensic_scrub',
            email_last_checked_at = NOW()
        WHERE (email_status IS NULL OR email_status = '' OR email_status = 'unknown' OR email_status = 'missing_placeholder')
          AND LEFT(email, 9) = 'scrubbed-'
    """)
    conn.commit()
    print(f" -> Scrubbed placeholders classified: {cursor.rowcount:,} rows in {time.time()-t0:.2f}s.")

    # =========================================================================
    # ITEM 2: Classify Generic Provider Emails (Single-Pass)
    # =========================================================================
    print("\n[Item 2/6] Scoring generic provider email addresses...")
    t0 = time.time()
    cursor.execute("""
        UPDATE recruiters
        SET email_status = 'generic_provider',
            email_confidence = 65,
            email_source = 'public_provider',
            email_verified_at = NOW(),
            email_last_checked_at = NOW()
        WHERE (email_status IS NULL OR email_status = '' OR email_status = 'unknown' OR email_confidence = 0)
          AND email IS NOT NULL AND email != '' AND LEFT(email, 9) != 'scrubbed-'
          AND LOWER(SPLIT_PART(email, '@', 2)) IN ('gmail.com','yahoo.com','outlook.com','hotmail.com','aol.com','icloud.com','msn.com','live.com')
    """)
    conn.commit()
    print(f" -> Generic provider emails classified: {cursor.rowcount:,} rows in {time.time()-t0:.2f}s.")

    # =========================================================================
    # ITEM 3: Classify Structurally Valid Emails (Single-Pass)
    # =========================================================================
    print("\n[Item 3/6] Scoring remaining structurally valid email addresses...")
    t0 = time.time()
    cursor.execute("""
        UPDATE recruiters
        SET email_status = 'syntax_valid',
            email_confidence = 75,
            email_source = 'syntax_check',
            email_verified_at = NOW(),
            email_last_checked_at = NOW()
        WHERE (email_status IS NULL OR email_status = '' OR email_status = 'unknown' OR email_confidence = 0)
          AND email IS NOT NULL AND email != '' AND LEFT(email, 9) != 'scrubbed-'
          AND POSITION('@' in email) > 0 AND POSITION('.' in SPLIT_PART(email, '@', 2)) > 0
    """)
    conn.commit()
    print(f" -> Valid syntax emails classified: {cursor.rowcount:,} rows in {time.time()-t0:.2f}s.")

    # =========================================================================
    # ITEM 4: Promote syntax_valid to verified_pattern for matching company domains
    # =========================================================================
    print("\n[Item 4/6] Promoting emails matching verified company websites to verified_pattern...")
    t0 = time.time()
    cursor.execute("""
        UPDATE recruiters r
        SET email_status = 'verified_pattern',
            email_confidence = 90,
            email_source = 'domain_pattern_match'
        FROM companies c
        WHERE r.company_id = c.company_id
          AND r.email_status = 'syntax_valid'
          AND c.website IS NOT NULL AND c.website != '' AND LOWER(c.website) NOT IN ('null','n/a','none')
          AND LOWER(SPLIT_PART(r.email, '@', 2)) = LOWER(c.website)
    """)
    conn.commit()
    print(f" -> Corporate domain matched emails promoted: {cursor.rowcount:,} rows in {time.time()-t0:.2f}s.")

    # =========================================================================
    # ITEM 5: Operational Metadata Completion across Recruiters (Single-Pass)
    # =========================================================================
    print("\n[Item 5/6] Completing operational metadata across missing recruiter records...")
    t0 = time.time()
    cursor.execute("""
        UPDATE recruiters
        SET last_scan_at = COALESCE(last_scan_at, NOW()),
            needs_review = COALESCE(needs_review, false),
            report_count = COALESCE(report_count, 0),
            email_source = COALESCE(email_source, 'system_scan')
        WHERE last_scan_at IS NULL OR needs_review IS NULL OR email_source IS NULL
    """)
    conn.commit()
    print(f" -> Recruiter operational metadata completed: {cursor.rowcount:,} rows in {time.time()-t0:.2f}s.")

    # =========================================================================
    # ITEM 6: Company Tracking & Metadata Completion across Companies (Single-Pass)
    # =========================================================================
    print("\n[Item 6/6] Completing operational metadata across missing company records...")
    t0 = time.time()
    cursor.execute("""
        UPDATE companies
        SET is_tracked = COALESCE(is_tracked, true),
            trust_score = COALESCE(trust_score, 10)
        WHERE is_tracked IS NULL OR trust_score IS NULL
    """)
    conn.commit()
    print(f" -> Company operational metadata completed: {cursor.rowcount:,} rows in {time.time()-t0:.2f}s.")

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
    print(f"MASS FREE ENRICHMENT PHASE 4 COMPLETE IN {time.time()-start_total:.1f}s!")
    print("=" * 80)

if __name__ == '__main__':
    run_phase4_enrichment()
