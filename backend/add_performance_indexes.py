import sys
import os

# Ensure backend directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.database import engine
from sqlalchemy import text

def run_migration():
    print("Adding performance indexes...")
    commands = [
        "CREATE INDEX IF NOT EXISTS ix_recruiters_email2 ON recruiters (email2);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_email3 ON recruiters (email3);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_email4 ON recruiters (email4);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_phone ON recruiters (phone);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_phone2 ON recruiters (phone2);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_phone3 ON recruiters (phone3);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_phone4 ON recruiters (phone4);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_company_id ON recruiters (company_id);",
        "CREATE INDEX IF NOT EXISTS ix_recruiters_location ON recruiters (location);"
    ]
    
    with engine.connect() as conn:
        for cmd in commands:
            print(f"Executing: {cmd}")
            conn.execute(text(cmd))
        conn.commit()
    print("Done adding indexes!")

if __name__ == "__main__":
    run_migration()
