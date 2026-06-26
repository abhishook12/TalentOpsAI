import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL)
with engine.begin() as conn:
    result = conn.execute(text("UPDATE recruiters SET needs_review = true, updated_at = created_at WHERE recruiter_name ~ '[0-9]'"))
    print(f"Updated {result.rowcount} corrupted records.")
