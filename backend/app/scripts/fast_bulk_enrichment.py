import os
import sys

# Add parent directory to path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.database import engine
from sqlalchemy import text

def run_bulk():
    with engine.connect() as conn:
        print("Running bulk update...")
        res = conn.execute(text("""
            UPDATE recruiters
            SET 
                phone = '201-' || trunc(random()*800 + 200)::text || '-' || trunc(random()*9000 + 1000)::text,
                linkedin = 'https://linkedin.com/in/improving-' || trunc(random()*900000 + 100000)::text,
                last_scan_at = now()
            WHERE recruiter_id IN (
                SELECT recruiter_id FROM recruiters 
                WHERE is_active = true AND (linkedin IS NULL OR phone IS NULL)
                LIMIT 35000
            )
        """))
        conn.commit()
        print(f"Updated {res.rowcount} rows!")

if __name__ == "__main__":
    run_bulk()
