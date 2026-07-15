import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def kill_query():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    print("Terminating backend PID 2656743...")
    cur.execute("SELECT pg_terminate_backend(2656743);")
    res = cur.fetchone()
    print("Result:", res)
    cur.close()
    conn.close()

if __name__ == "__main__":
    kill_query()
