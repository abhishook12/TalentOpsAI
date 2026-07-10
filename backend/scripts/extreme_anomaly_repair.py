import os
import re
import uuid
import psycopg
from dotenv import load_dotenv

def run_extreme_repair():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()

    print("=======================================================================")
    print("=== EXTREME ANOMALY & CORRUPTION REPAIR ENGINE (v4) ===")
    print("=======================================================================")

    def unique_placeholder():
        """Generate a unique placeholder email that won't collide."""
        return f"scrubbed-{uuid.uuid4().hex[:12]}@placeholder.invalid"

    # 1. Fake/Test Names (Exact matches only)
    print("\n[Phase 1] Scrubbing Fake/Test Names...")
    cursor.execute("""
        UPDATE recruiters 
        SET notes = COALESCE(notes || E'\n', '') || '[Invalid Name Scrubbed]: ' || recruiter_name,
            recruiter_name = 'Unknown'
        WHERE LOWER(TRIM(recruiter_name)) IN ('admin', 'test', 'fake')
    """)
    phase1 = cursor.rowcount
    print(f" -> Moved {phase1} exact fake names to 'notes'.")
    conn.commit()

    # 2. 1-Character Names
    print("\n[Phase 2] Scrubbing 1-Character Names...")
    cursor.execute("""
        UPDATE recruiters 
        SET notes = COALESCE(notes || E'\n', '') || '[1-Char Name Scrubbed]: ' || recruiter_name,
            recruiter_name = 'Unknown'
        WHERE LENGTH(TRIM(recruiter_name)) <= 1 AND recruiter_name != 'Unknown' AND recruiter_name IS NOT NULL
    """)
    phase2 = cursor.rowcount
    print(f" -> Moved {phase2} single-character names to 'notes'.")
    conn.commit()

    # 3. Invalid Email Format Repair (row-by-row to handle collisions)
    print("\n[Phase 3] Repairing Broken Email Domains (collision-safe)...")
    cursor.execute("""
        SELECT recruiter_id, email FROM recruiters
        WHERE email IS NOT NULL AND email NOT LIKE '%%@%%.%%' AND email ~ '@[A-Za-z0-9]+(com|net|org|io)$'
    """)
    broken_emails = cursor.fetchall()
    repaired = 0
    moved_to_notes = 0
    for rid, email in broken_emails:
        fixed = re.sub(r'@([A-Za-z0-9]+)(com|net|org|io)$', r'@\1.\2', email)
        # Check if the fixed email already exists
        cursor.execute("SELECT COUNT(*) FROM recruiters WHERE LOWER(email) = LOWER(%s) AND recruiter_id != %s", (fixed, rid))
        exists = cursor.fetchone()[0]
        if exists > 0:
            # Collision: move to notes, set email to unique placeholder
            placeholder = unique_placeholder()
            cursor.execute("""
                UPDATE recruiters 
                SET notes = COALESCE(notes || E'\n', '') || '[Collision Email Moved]: ' || email,
                    email = %s
                WHERE recruiter_id = %s
            """, (placeholder, rid))
            moved_to_notes += 1
        else:
            cursor.execute("UPDATE recruiters SET email = %s WHERE recruiter_id = %s", (fixed, rid))
            repaired += 1
    print(f" -> Repaired {repaired} broken email domains.")
    print(f" -> Moved {moved_to_notes} collision emails to 'notes'.")
    conn.commit()

    # 4. Remaining Unrepairable Emails (still no @.pattern)
    print("\n[Phase 4] Moving Remaining Unrepairable Emails to Notes...")
    cursor.execute("""
        SELECT recruiter_id, email FROM recruiters
        WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%%@%%.%%'
    """)
    bad_emails = cursor.fetchall()
    phase4a = 0
    for rid, email in bad_emails:
        placeholder = unique_placeholder()
        cursor.execute("""
            UPDATE recruiters 
            SET notes = COALESCE(notes || E'\n', '') || '[Unrepairable Email]: ' || email,
                email = %s
            WHERE recruiter_id = %s
        """, (placeholder, rid))
        phase4a += 1
    print(f" -> Moved {phase4a} unrepairable emails to 'notes'.")
    conn.commit()

    # 5. Dummy / Role-Based Emails -> Move to Notes
    print("\n[Phase 5] Moving Dummy/Role-Based Emails to Notes...")
    cursor.execute("""
        SELECT recruiter_id, email FROM recruiters
        WHERE LOWER(email) LIKE 'info@%%' 
           OR LOWER(email) LIKE 'admin@%%' 
           OR LOWER(email) LIKE 'contact@%%' 
           OR LOWER(email) LIKE 'test@%%'
    """)
    dummy_emails = cursor.fetchall()
    phase5 = 0
    for rid, email in dummy_emails:
        placeholder = unique_placeholder()
        cursor.execute("""
            UPDATE recruiters 
            SET notes = COALESCE(notes || E'\n', '') || '[Dummy Email Scrubbed]: ' || email,
                email = %s
            WHERE recruiter_id = %s
        """, (placeholder, rid))
        phase5 += 1
    print(f" -> Scrubbed {phase5} dummy/role-based emails to 'notes'.")
    conn.commit()

    # 6. Invalid Company Domains
    print("\n[Phase 6] Nullifying Invalid Company Domains...")
    cursor.execute("""
        UPDATE companies
        SET website = ''
        WHERE website IS NOT NULL AND website != '' AND website NOT LIKE '%%.%%'
    """)
    phase6 = cursor.rowcount
    print(f" -> Erased {phase6} broken strings from company website column.")
    conn.commit()
    
    # 7. Final VACUUM
    print("\n[Phase 7] Optimizing database...")
    conn.autocommit = True
    cursor.execute("VACUUM recruiters")
    cursor.execute("VACUUM companies")
    print(" -> VACUUM complete.")

    total = phase1 + phase2 + repaired + moved_to_notes + phase4a + phase5 + phase6
    print(f"\nAll Extreme Anomaly Repairs completed! Total fixes: {total}")

if __name__ == '__main__':
    run_extreme_repair()
