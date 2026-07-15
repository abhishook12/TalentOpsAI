import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql+psycopg://"):
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

def run_vacuum():
    print("Connecting to DB...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    print("Disabling statement timeout...")
    cur.execute("SET statement_timeout = 0;")
    
    print("Running VACUUM...")
    cur.execute("VACUUM;")
    
    print("Database vacuumed successfully!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    run_vacuum()
