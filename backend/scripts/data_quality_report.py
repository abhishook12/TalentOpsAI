import os
import psycopg
from dotenv import load_dotenv

def generate_quality_report():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()

    print("=======================================================================")
    print("=== FULL DATABASE DATA QUALITY REPORT ===")
    print("=======================================================================")

    # Total Recruiters
    cursor.execute("SELECT COUNT(*) FROM recruiters")
    total_recruiters = cursor.fetchone()[0]
    
    # Recruiters with Emails
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE email IS NOT NULL AND email != ''")
    has_email = cursor.fetchone()[0]
    
    # Recruiters with Title
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE title IS NOT NULL AND title != ''")
    has_title = cursor.fetchone()[0]
    
    # Recruiters mapped to a valid Company
    cursor.execute("SELECT COUNT(*) FROM recruiters r JOIN companies c ON r.company_id = c.company_id WHERE c.company_id IS NOT NULL")
    has_company = cursor.fetchone()[0]
    
    # Structural Anomalies (Clean Data)
    # Check for .dup
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE email LIKE '%.dup.%'")
    dup_emails = cursor.fetchone()[0]
    
    # Check for Semicolons
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE POSITION(';' IN email) > 0 OR POSITION(';' IN recruiter_name) > 0")
    semi_mashes = cursor.fetchone()[0]
    
    # Check for [DUPLICATE] tags in companies
    cursor.execute("SELECT COUNT(*) FROM companies WHERE company_name LIKE '%[DUPLICATE]%'")
    dup_companies = cursor.fetchone()[0]

    # Check for Invalid Names (Job Titles left in Name field)
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE LOWER(recruiter_name) SIMILAR TO '%(specialist|administrator|manager|director|vp|recruiter|talent|acquisition|sourcer|consultant|president|officer|software|technologies|llc|inc|corp|solutions|group)%' AND recruiter_name != 'Unknown'")
    invalid_names = cursor.fetchone()[0]

    print(f"Total Active Recruiters: {total_recruiters:,}")
    print(f"Recruiters with Clean Emails: {has_email:,} ({(has_email/total_recruiters)*100:.1f}%)")
    print(f"Recruiters with Mapped Companies: {has_company:,} ({(has_company/total_recruiters)*100:.1f}%)")
    print(f"Recruiters with Extracted Titles: {has_title:,} ({(has_title/total_recruiters)*100:.1f}%)")
    
    print("\\n--- FORENSIC CLEANLINESS METRICS ---")
    print(f"Emails infected with '.dup' suffix: {dup_emails:,} (Target: 0)")
    print(f"Mashed semicolon contacts: {semi_mashes:,} (Target: 0)")
    print(f"Companies with [DUPLICATE] tags: {dup_companies:,} (Target: 0)")
    print(f"Titles masquerading as Names: {invalid_names:,} (Target: 0)")
    
    # Check Database Size
    cursor.execute("SELECT pg_database_size('postgres') / 1048576.0")
    db_size = cursor.fetchone()[0]
    print(f"\\nDatabase Size: {db_size:.2f} MB (Target: < 400 MB)")
    print("=======================================================================")

if __name__ == '__main__':
    generate_quality_report()
