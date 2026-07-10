import os
import psycopg
from dotenv import load_dotenv

def run_extreme_hunt():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()

    print("=======================================================================")
    print("=== EXTREME ANOMALY & CORRUPTION HUNT (v2) ===")
    print("=======================================================================")

    anomalies_found = 0

    # 1. Fake/Test Names (exact word match only, not substrings like Padmini)
    cursor.execute("""
        SELECT COUNT(*) FROM recruiters 
        WHERE LOWER(TRIM(recruiter_name)) IN ('test', 'fake', 'admin', 'unknown test', 'test user')
    """)
    fake_names = cursor.fetchone()[0]
    if fake_names > 0:
        cursor.execute("""
            SELECT recruiter_name FROM recruiters 
            WHERE LOWER(TRIM(recruiter_name)) IN ('test', 'fake', 'admin', 'unknown test', 'test user') LIMIT 5
        """)
        examples = [r[0] for r in cursor.fetchall()]
        print(f"[!] Found {fake_names:,} exact fake/test names (e.g., {examples})")
        anomalies_found += fake_names
    else:
        print("[OK] No exact fake/test names found.")

    # 2. 1-Character Names
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE LENGTH(TRIM(recruiter_name)) <= 1 AND recruiter_name != 'Unknown'")
    one_char = cursor.fetchone()[0]
    if one_char > 0:
        print(f"[!] Found {one_char:,} names that are 1 character or less.")
        anomalies_found += one_char
    else:
        print("[OK] No 1-character names found.")

    # 3. Invalid Email Format (No '@' or no '.' after @) - excluding placeholders
    cursor.execute("""
        SELECT COUNT(*) FROM recruiters 
        WHERE email NOT LIKE '%%@%%.%%' 
          AND email NOT LIKE 'scrubbed-%%@placeholder.invalid'
    """)
    bad_emails = cursor.fetchone()[0]
    if bad_emails > 0:
        cursor.execute("""
            SELECT email FROM recruiters 
            WHERE email NOT LIKE '%%@%%.%%' AND email NOT LIKE 'scrubbed-%%@placeholder.invalid' LIMIT 5
        """)
        examples = [r[0] for r in cursor.fetchall()]
        print(f"[!] Found {bad_emails:,} structurally invalid emails (e.g., {examples})")
        anomalies_found += bad_emails
    else:
        print("[OK] No structurally invalid emails found.")

    # 4. Dummy/Placeholder Emails (excluding our scrubbed placeholders)
    cursor.execute("""
        SELECT COUNT(*) FROM recruiters 
        WHERE (LOWER(email) LIKE 'info@%%' OR LOWER(email) LIKE 'admin@%%' 
               OR LOWER(email) LIKE 'contact@%%' OR LOWER(email) LIKE 'test@%%')
          AND email NOT LIKE 'scrubbed-%%@placeholder.invalid'
    """)
    dummy_emails = cursor.fetchone()[0]
    if dummy_emails > 0:
        print(f"[!] Found {dummy_emails:,} non-personal dummy emails.")
        anomalies_found += dummy_emails
    else:
        print("[OK] No dummy/role-based emails found.")

    # 5. .dup suffix emails
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE email LIKE '%%.dup.%%'")
    dup_emails = cursor.fetchone()[0]
    if dup_emails > 0:
        print(f"[!] Found {dup_emails:,} emails with .dup suffix.")
        anomalies_found += dup_emails
    else:
        print("[OK] No .dup suffix emails.")

    # 6. Semicolon mashes
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE POSITION(';' IN email) > 0 OR POSITION(';' IN recruiter_name) > 0")
    semi = cursor.fetchone()[0]
    if semi > 0:
        print(f"[!] Found {semi:,} semicolon-mashed contacts.")
        anomalies_found += semi
    else:
        print("[OK] No semicolon mashes.")

    # 7. [DUPLICATE] company tags
    cursor.execute("SELECT COUNT(*) FROM companies WHERE company_name LIKE '%%[DUPLICATE]%%'")
    dup_co = cursor.fetchone()[0]
    if dup_co > 0:
        print(f"[!] Found {dup_co:,} companies with [DUPLICATE] tags.")
        anomalies_found += dup_co
    else:
        print("[OK] No [DUPLICATE] company tags.")

    # 8. Companies with invalid website (no dot)
    cursor.execute("""
        SELECT COUNT(*) FROM companies 
        WHERE website IS NOT NULL AND website != '' AND website NOT LIKE '%%.%%'
    """)
    bad_urls = cursor.fetchone()[0]
    if bad_urls > 0:
        print(f"[!] Found {bad_urls:,} companies with invalid website URLs.")
        anomalies_found += bad_urls
    else:
        print("[OK] No invalid company website URLs.")

    # 9. Scrubbed placeholder count (informational)
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE email LIKE 'scrubbed-%%@placeholder.invalid'")
    placeholders = cursor.fetchone()[0]
    print(f"\n[INFO] Scrubbed placeholder emails (safely parked): {placeholders:,}")

    # 10. DB Size
    cursor.execute("SELECT pg_database_size('postgres') / 1048576.0")
    db_size = cursor.fetchone()[0]
    print(f"[INFO] Database Size: {db_size:.2f} MB (Limit: 400 MB)")

    print("\n=======================================================================")
    if anomalies_found == 0:
        print("RESULT: ZERO structural anomalies found across all 326k contacts!")
    else:
        print(f"RESULT: {anomalies_found:,} anomalies still remain.")
    print("=======================================================================")

if __name__ == '__main__':
    run_extreme_hunt()
