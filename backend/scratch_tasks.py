import os
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    print("Size of raw_data and metadata_json in recruiters:")
    res = conn.execute(text("""
        SELECT 
            pg_size_pretty(sum(pg_column_size(raw_data))) as raw_data_size,
            pg_size_pretty(sum(pg_column_size(metadata_json))) as metadata_size
        FROM recruiters;
    """)).fetchone()
    print(res)
    
    print("Size of raw_data and metadata_json in companies:")
    res = conn.execute(text("""
        SELECT 
            pg_size_pretty(sum(pg_column_size(raw_data))) as raw_data_size,
            pg_size_pretty(sum(pg_column_size(metadata_json))) as metadata_size
        FROM companies;
    """)).fetchone()
    print(res)
    
    print("\nData quality check:")
    print("1. Orphaned companies (count):")
    res = conn.execute(text("""
        SELECT count(*) FROM companies c
        WHERE NOT EXISTS (SELECT 1 FROM recruiters r WHERE r.company_id = c.company_id)
    """)).scalar()
    print(res)
    
    print("2. Recruiters missing both email and phone (count):")
    res = conn.execute(text("""
        SELECT count(*) FROM recruiters 
        WHERE (email IS NULL OR email = '') AND (phone IS NULL OR phone = '')
    """)).scalar()
    print(res)
    
    print("3. Duplicate email records (count of dupes):")
    res = conn.execute(text("""
        SELECT email, count(*) FROM recruiters 
        WHERE email IS NOT NULL AND email != ''
        GROUP BY email
        HAVING count(*) > 1
    """)).fetchall()
    print(f"Number of emails with duplicates: {len(res)}")
