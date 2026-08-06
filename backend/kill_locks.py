import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r'C:\TalentOpsAI\backend\.env')
DATABASE_URL = os.environ.get('DATABASE_URL', '').replace('+psycopg', '')
DATABASE_URL = DATABASE_URL.replace(':6543', ':5432')

def kill_locks():
    print("Connecting to:", DATABASE_URL)
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE state = 'active' AND query ILIKE '%recruiter_emails%' AND pid <> pg_backend_pid();
    """)
    print(f"Terminated {cur.rowcount} queries blocking recruiter_emails.")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    kill_locks()
