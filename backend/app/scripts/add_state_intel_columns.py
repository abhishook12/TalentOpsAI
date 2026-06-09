import os
import sys
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.database import SessionLocal

def upgrade():
    db = SessionLocal()
    queries = [
        "ALTER TABLE recruiters ADD COLUMN state_source VARCHAR(150);",
        "ALTER TABLE recruiters ADD COLUMN state_confidence VARCHAR(50);",
        "ALTER TABLE recruiters ADD COLUMN state_reason TEXT;",
        "ALTER TABLE recruiters ADD COLUMN last_scan_at TIMESTAMP;"
    ]
    
    for q in queries:
        try:
            print(f"Executing: {q}")
            db.execute(text(q))
            db.commit()
            print("Success.")
        except Exception as e:
            db.rollback()
            print(f"Skipped/Failed: {e}")
            
    db.close()

if __name__ == '__main__':
    upgrade()
