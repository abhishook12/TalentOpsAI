import sqlite3
from sqlalchemy import create_engine, text
import os

GENERIC_NAMES = [
    'Unknown',
    'Partner',
    'Unknown Recruiter',
    'Unknown Vaco Recruiter',
    'Recruiter',
    'Talent Acquisition',
    'HR',
    'Human Resources'
]

def clean_sqlite():
    print("--- Cleaning SQLite (dev.db) ---")
    conn = sqlite3.connect('C:\\TalentOpsAI\\backend\\dev.db')
    c = conn.cursor()
    
    # 1. Delete missing email AND phone
    c.execute("DELETE FROM recruiters WHERE (email IS NULL OR email = '') AND (phone IS NULL OR phone = '')")
    deleted_missing = c.rowcount
    
    # 2. Delete generic names
    placeholders = ','.join('?' for _ in GENERIC_NAMES)
    c.execute(f"DELETE FROM recruiters WHERE recruiter_name IN ({placeholders})", GENERIC_NAMES)
    deleted_generic = c.rowcount
    
    # 3. Delete names that start with "Unknown" just to be safe
    c.execute("DELETE FROM recruiters WHERE recruiter_name LIKE 'Unknown %'")
    deleted_unknown_like = c.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Deleted {deleted_missing} recruiters missing both email and phone.")
    print(f"Deleted {deleted_generic + deleted_unknown_like} recruiters with generic names.")

def clean_postgres():
    print("\n--- Cleaning Postgres (Supabase) ---")
    DATABASE_URL = 'postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres'
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        # 1. Delete missing email AND phone
        res_missing = conn.execute(text("DELETE FROM recruiters WHERE (email IS NULL OR email = '') AND (phone IS NULL OR phone = '')"))
        
        # 2. Delete generic names
        placeholders = ','.join(f"'{name}'" for name in GENERIC_NAMES)
        res_generic = conn.execute(text(f"DELETE FROM recruiters WHERE recruiter_name IN ({placeholders})"))
        
        # 3. Delete "Unknown %" names
        res_unknown = conn.execute(text("DELETE FROM recruiters WHERE recruiter_name ILIKE 'Unknown %'"))
        
        print(f"Deleted {res_missing.rowcount} recruiters missing both email and phone.")
        print(f"Deleted {res_generic.rowcount + res_unknown.rowcount} recruiters with generic names.")

if __name__ == "__main__":
    clean_sqlite()
    clean_postgres()
    print("\nCleanup completed.")
