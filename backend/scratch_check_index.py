import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def check_index():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'recruiters' AND indexdef LIKE '%company_id%';
    """)
    rows = cur.fetchall()
    print("Indexes on recruiters involving company_id:")
    for r in rows:
        print(r)
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_index()
