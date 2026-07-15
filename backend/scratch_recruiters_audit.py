import os
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    print("Recruiters row count:")
    res = conn.execute(text("SELECT count(*) FROM recruiters")).scalar()
    print(res)
    
    print("\nSizes of text columns in recruiters:")
    res = conn.execute(text("""
        SELECT 
            pg_size_pretty(sum(pg_column_size(notes))) as notes_size,
            pg_size_pretty(sum(pg_column_size(alternate_emails))) as alt_emails_size,
            pg_size_pretty(sum(pg_column_size(alternate_phones))) as alt_phones_size,
            pg_size_pretty(sum(pg_column_size(review_reason))) as review_reason_size,
            pg_size_pretty(sum(pg_column_size(repair_reason))) as repair_reason_size,
            pg_size_pretty(sum(pg_column_size(tags))) as tags_size
        FROM recruiters;
    """)).fetchone()
    print(res)
    
    print("\nCheck if there are any orphaned records in enrichment_results (where recruiter_id not in recruiters):")
    res = conn.execute(text("""
        SELECT count(*) FROM enrichment_results 
        WHERE recruiter_id IS NOT NULL AND recruiter_id NOT IN (SELECT recruiter_id FROM recruiters)
    """)).scalar()
    print(res)
