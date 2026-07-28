import os
import sqlalchemy

DATABASE_URL = 'postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres'

engine = sqlalchemy.create_engine(DATABASE_URL)

missing_columns = [
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS quality_score INTEGER DEFAULT 0;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS missing_fields TEXT;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS sentinel_status VARCHAR(50);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email_status VARCHAR(50) DEFAULT 'unknown';",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email_confidence INTEGER DEFAULT 0;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email_source VARCHAR(100);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email_pattern_id INTEGER;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email_generated BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email_last_checked_at TIMESTAMP;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS canonical_company_id INTEGER;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS historical_company_id INTEGER;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS company_domain_id INTEGER;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS raw_email_value VARCHAR(150);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS repair_reason VARCHAR(255);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email2 VARCHAR(150);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS phone2 VARCHAR(30);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email3 VARCHAR(150);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS phone3 VARCHAR(30);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS email4 VARCHAR(150);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS phone4 VARCHAR(30);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS alternate_emails TEXT;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS alternate_phones TEXT;",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS title VARCHAR(150);",
    "ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS notes TEXT;",
]

with engine.connect() as conn:
    for cmd in missing_columns:
        print(f"Executing: {cmd}")
        try:
            conn.execute(sqlalchemy.text(cmd))
            conn.commit()
        except Exception as e:
            print(f"Error: {e}")

print("Done checking missing columns!")
