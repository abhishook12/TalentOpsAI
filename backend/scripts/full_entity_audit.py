import os
import psycopg
from dotenv import load_dotenv

def run_full_audit():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()

    print("=" * 90)
    print("FULL ENTITY DATA COMPLETENESS AUDIT")
    print("=" * 90)

    # --- RECRUITERS TABLE ---
    cursor.execute("SELECT COUNT(*) FROM recruiters")
    total_recruiters = cursor.fetchone()[0]
    print(f"\n{'='*90}")
    print(f"RECRUITERS TABLE ({total_recruiters:,} total rows)")
    print(f"{'='*90}")

    recruiter_fields = [
        ("recruiter_name", "Name"),
        ("normalized_recruiter_name", "Normalized Name"),
        ("email", "Primary Email"),
        ("title", "Job Title"),
        ("phone", "Phone Number"),
        ("linkedin", "LinkedIn URL"),
        ("location", "City / Location"),
        ("normalized_city", "Normalized City"),
        ("state", "State"),
        ("specialization", "Specialization"),
        ("company_id", "Company Link"),
        ("canonical_company_id", "Canonical Company ID"),
        ("is_active", "Is Active Status"),
        ("email2", "Email 2"),
        ("phone2", "Phone 2"),
        ("email3", "Email 3"),
        ("phone3", "Phone 3"),
        ("email4", "Email 4"),
        ("phone4", "Phone 4"),
        ("alternate_emails", "Alternate Emails"),
        ("alternate_phones", "Alternate Phones"),
        ("notes", "Notes"),
        ("data_source", "Data Source"),
        ("tags", "Tags"),
        ("taxonomy_category", "Taxonomy Category"),
        ("email_status", "Email Verification Status"),
        ("email_confidence", "Email Confidence"),
        ("email_source", "Email Source"),
        ("last_scan_at", "Last Scan Timestamp"),
        ("needs_review", "Needs Review Status"),
        ("completeness_score", "Completeness Score"),
        ("trust_score", "Trust Score"),
    ]

    for col, label in recruiter_fields:
        try:
            cursor.execute(f"""
                SELECT COUNT(*) FROM recruiters 
                WHERE {col} IS NOT NULL AND CAST({col} AS TEXT) != '' 
                  AND LOWER(CAST({col} AS TEXT)) NOT IN ('null', 'n/a', 'none', 'unknown', '0')
                  AND CAST({col} AS TEXT) NOT LIKE 'scrubbed-%%@placeholder.invalid'
            """)
            filled = cursor.fetchone()[0]
            pct = (filled / total_recruiters * 100) if total_recruiters > 0 else 0
            empty = total_recruiters - filled
            if pct >= 99: status = "FULL"
            elif pct >= 70: status = "GOOD"
            elif pct >= 30: status = "PARTIAL"
            elif pct >= 5: status = "LOW"
            else: status = "EMPTY"
            print(f"  {label:30s} | {filled:>10,} filled | {empty:>10,} empty | {pct:5.1f}% | [{status}]")
        except Exception as e:
            conn.rollback()
            print(f"  {label:30s} | ERROR: {e}")

    # --- COMPANIES TABLE ---
    cursor.execute("SELECT COUNT(*) FROM companies")
    total_companies = cursor.fetchone()[0]
    print(f"\n{'='*90}")
    print(f"COMPANIES TABLE ({total_companies:,} total rows)")
    print(f"{'='*90}")

    company_fields = [
        ("company_name", "Company Name"),
        ("normalized_company_name", "Normalized Name"),
        ("website", "Website / Domain"),
        ("industry", "Industry"),
        ("location", "Headquarters Location"),
        ("state", "State"),
        ("email_pattern", "Email Pattern"),
        ("linkedin_url", "LinkedIn URL"),
        ("notes", "Notes"),
        ("data_source", "Data Source"),
        ("tags", "Tags"),
        ("trust_score", "Trust Score"),
        ("is_tracked", "Is Tracked Status"),
    ]

    for col, label in company_fields:
        try:
            cursor.execute(f"""
                SELECT COUNT(*) FROM companies 
                WHERE {col} IS NOT NULL AND CAST({col} AS TEXT) != '' 
                  AND LOWER(CAST({col} AS TEXT)) NOT IN ('null', 'n/a', 'none')
            """)
            filled = cursor.fetchone()[0]
            pct = (filled / total_companies * 100) if total_companies > 0 else 0
            empty = total_companies - filled
            if pct >= 99: status = "FULL"
            elif pct >= 70: status = "GOOD"
            elif pct >= 30: status = "PARTIAL"
            elif pct >= 5: status = "LOW"
            else: status = "EMPTY"
            print(f"  {label:30s} | {filled:>10,} filled | {empty:>10,} empty | {pct:5.1f}% | [{status}]")
        except Exception as e:
            conn.rollback()
            print(f"  {label:30s} | ERROR: {e}")

    # --- DB SIZE ---
    cursor.execute("SELECT pg_database_size('postgres') / 1048576.0")
    db_size = cursor.fetchone()[0]
    print(f"\n{'='*90}")
    print(f"DATABASE SIZE: {db_size:.2f} MB / 400 MB limit ({db_size/400*100:.1f}% used)")
    print(f"{'='*90}")

if __name__ == '__main__':
    run_full_audit()
