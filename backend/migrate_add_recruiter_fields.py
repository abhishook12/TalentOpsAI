"""
Run this once to add email2, phone2, notes columns to the live Neon DB.
Usage: python migrate_add_recruiter_fields.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(DATABASE_URL)

migrations = [
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email2 VARCHAR(150)",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS phone2 VARCHAR(30)",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS notes TEXT",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS linkedin VARCHAR(255)",  # in case it was missing
]

with engine.connect() as conn:
    for sql in migrations:
        try:
            conn.execute(text(sql))
            print(f"[OK] {sql}")
        except Exception as e:
            print(f"[SKIP] Already exists or error: {e}")
    conn.commit()

print("\nDone! New columns: email2, phone2, notes, linkedin")
