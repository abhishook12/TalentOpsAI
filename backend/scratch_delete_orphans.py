import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def delete_orphans():
    print("Connecting to DB...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("SET statement_timeout = 0;")
    print("Deleting orphaned companies...")
    cur.execute("""
        DELETE FROM companies 
        WHERE NOT EXISTS (SELECT 1 FROM recruiters r WHERE r.company_id = companies.company_id)
    """)
    print(f"Deleted {cur.rowcount} orphaned companies.")
    
    cur.execute("VACUUM FULL companies;")
    print("Companies table vacuumed.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    delete_orphans()
