import os
import psycopg
from dotenv import load_dotenv

def check_missing_logos():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    # psycopg expects standard postgresql:// for connection string instead of postgresql+psycopg://
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    c = conn.cursor()
    c.execute("""
        SELECT c.company_name, COUNT(r.recruiter_id) as cnt 
        FROM companies c 
        LEFT JOIN recruiters r ON c.company_id = r.company_id 
        WHERE (c.website IS NULL OR c.website = '' OR c.website = 'null') 
        GROUP BY c.company_name 
        HAVING COUNT(r.recruiter_id) > 0
        ORDER BY cnt DESC 
        LIMIT 30
    """)
    rows = c.fetchall()
    print("=== Top 30 Companies Missing Websites (Logos) ===")
    for row in rows:
        print(f"{row[0]}: {row[1]} recruiters")
    
    c.execute("""
        SELECT COUNT(*) FROM companies 
        WHERE website IS NULL OR website = '' OR website = 'null'
    """)
    total_missing = c.fetchone()[0]
    print(f"\\nTotal Companies Missing Websites: {total_missing:,}")

if __name__ == "__main__":
    check_missing_logos()
