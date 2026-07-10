import os
import psycopg
from dotenv import load_dotenv

def run_fast_dedup():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    conn.autocommit = False
    cursor = conn.cursor()

    print("=======================================================================")
    print("=== ULTRA-FAST PURE SQL DEDUPLICATION ENGINE ===")
    print("=======================================================================")

    print("\n[Phase 1] Building temporary mapping for exact duplicate recruiters...")
    cursor.execute("""
        CREATE TEMPORARY TABLE recruiter_dup_map AS
        WITH ranked_recruiters AS (
            SELECT 
                recruiter_id,
                company_id,
                normalized_recruiter_name,
                FIRST_VALUE(recruiter_id) OVER (
                    PARTITION BY company_id, normalized_recruiter_name 
                    ORDER BY completeness_score DESC, recruiter_id ASC
                ) AS golden_id
            FROM recruiters
            WHERE is_active = true 
              AND company_id IS NOT NULL 
              AND normalized_recruiter_name IS NOT NULL 
              AND normalized_recruiter_name != ''
        )
        SELECT recruiter_id AS duplicate_id, golden_id
        FROM ranked_recruiters
        WHERE recruiter_id != golden_id;
    """)
    cursor.execute("SELECT COUNT(*) FROM recruiter_dup_map")
    dup_rec_count = cursor.fetchone()[0]
    print(f" -> Found {dup_rec_count:,} duplicate recruiters mapped to golden records.")

    if dup_rec_count > 0:
        print("\n[Phase 2] Reassigning child records (`candidates`, `submissions`, `emails`, `phones`, `locations`, `audit`)...")
        cursor.execute("""
            UPDATE candidates c SET recruiter_id = m.golden_id
            FROM recruiter_dup_map m WHERE c.recruiter_id = m.duplicate_id;
        """)
        cursor.execute("""
            UPDATE submissions s SET recruiter_id = m.golden_id
            FROM recruiter_dup_map m WHERE s.recruiter_id = m.duplicate_id;
        """)
        cursor.execute("""
            UPDATE recruiter_emails e SET recruiter_id = m.golden_id
            FROM recruiter_dup_map m WHERE e.recruiter_id = m.duplicate_id;
        """)
        cursor.execute("""
            UPDATE recruiter_phones p SET recruiter_id = m.golden_id
            FROM recruiter_dup_map m WHERE p.recruiter_id = m.duplicate_id;
        """)
        cursor.execute("""
            UPDATE recruiter_locations l SET recruiter_id = m.golden_id
            FROM recruiter_dup_map m WHERE l.recruiter_id = m.duplicate_id;
        """)
        cursor.execute("""
            UPDATE enrichment_audit a SET recruiter_id = m.golden_id
            FROM recruiter_dup_map m WHERE a.recruiter_id = m.duplicate_id;
        """)

        print("\n[Phase 3] Deactivating duplicate recruiters (`is_active = false`)...")
        cursor.execute("""
            UPDATE recruiters r
            SET is_active = false,
                notes = COALESCE(r.notes || ' | ', '') || '[NIGHT_SWEEPER_SQL] Merged into golden recruiter_id: ' || m.golden_id
            FROM recruiter_dup_map m
            WHERE r.recruiter_id = m.duplicate_id;
        """)
        print(f" -> Successfully deactivated {cursor.rowcount:,} duplicate recruiters.")

    conn.commit()
    print("\n[OK] Pure SQL Deduplication completed in single pass!")
    conn.close()

if __name__ == '__main__':
    run_fast_dedup()
