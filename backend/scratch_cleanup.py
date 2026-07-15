import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def cleanup():
    print("Connecting to DB for cleanup...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Disable statement timeout for these heavy queries
    cur.execute("SET statement_timeout = 0;")
    print("Statement timeout disabled.")
    
    # 1. Truncate metadata_json and raw_data to save space (do this first as it might be faster and free up space)
    print("Nullifying metadata_json and raw_data in recruiters...")
    cur.execute("""
        UPDATE recruiters SET metadata_json = NULL, raw_data = NULL 
        WHERE metadata_json IS NOT NULL OR raw_data IS NOT NULL
    """)
    print(f"Updated {cur.rowcount} recruiters.")
    
    print("Nullifying metadata_json and raw_data in companies...")
    cur.execute("""
        UPDATE companies SET metadata_json = NULL, raw_data = NULL 
        WHERE metadata_json IS NOT NULL OR raw_data IS NOT NULL
    """)
    print(f"Updated {cur.rowcount} companies.")

    # 2. Delete recruiters missing both email and phone
    print("Deleting recruiters with no email and no phone...")
    cur.execute("""
        DELETE FROM recruiters 
        WHERE (email IS NULL OR email = '') AND (phone IS NULL OR phone = '')
    """)
    print(f"Deleted {cur.rowcount} invalid recruiters.")
    
    # 3. Delete orphaned companies
    print("Deleting orphaned companies...")
    cur.execute("""
        DELETE FROM companies 
        WHERE NOT EXISTS (SELECT 1 FROM recruiters r WHERE r.company_id = companies.company_id)
    """)
    print(f"Deleted {cur.rowcount} orphaned companies.")
    
    cur.close()
    conn.close()
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
