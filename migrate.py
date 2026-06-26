import os
from sqlalchemy import create_engine, text

# Get DB URL from env or hardcode for now
db_url = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(db_url)
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE companies ADD COLUMN is_tracked BOOLEAN DEFAULT FALSE;"))
        conn.commit()
        print("Successfully added is_tracked column.")
    except Exception as e:
        print("Error (column might already exist):", e)
