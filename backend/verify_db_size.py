import time
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def check_size():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    size = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM companies WHERE NOT EXISTS (SELECT 1 FROM recruiters r WHERE r.company_id = companies.company_id)")
    orphans = cur.fetchone()[0]
    print(f"DB Size: {size}, Orphaned Companies: {orphans}")
    cur.close()
    conn.close()

print("Check 1:")
check_size()
print("Waiting 60 seconds...")
time.sleep(60)
print("Check 2:")
check_size()
print("Waiting 60 seconds...")
time.sleep(60)
print("Check 3:")
check_size()
print("Waiting 60 seconds...")
time.sleep(60)
print("Check 4:")
check_size()
