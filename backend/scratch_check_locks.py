import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def check_locks():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT pid, state, query, wait_event_type, wait_event
        FROM pg_stat_activity
        WHERE state = 'active' AND pid != pg_backend_pid();
    """)
    rows = cur.fetchall()
    if rows:
        print("Active queries:")
        for r in rows:
            print(r)
    else:
        print("No other active queries.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_locks()
