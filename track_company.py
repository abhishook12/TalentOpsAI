import os
from sqlalchemy import create_engine, text

db_url = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(db_url)

with engine.connect() as conn:
    # Get a company to track
    res = conn.execute(text("SELECT company_id, company_name FROM companies LIMIT 1")).fetchone()
    if res:
        company_id = res[0]
        company_name = res[1]
        print(f"Tracking company: {company_name} (ID: {company_id})")
        
        # Mark it as tracked
        conn.execute(text("UPDATE companies SET is_tracked = true WHERE company_id = :cid"), {"cid": company_id})
        conn.commit()
        print("Success!")
    else:
        print("No companies found.")
