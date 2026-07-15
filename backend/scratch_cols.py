import os
from sqlalchemy import create_engine, text
import json

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    print("Columns in 'recruiters':")
    res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'recruiters';")).fetchall()
    for r in res: print(r)
    
    print("\nColumns in 'companies':")
    res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'companies';")).fetchall()
    for r in res: print(r)
