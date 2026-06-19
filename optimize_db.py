from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres', isolation_level="AUTOCOMMIT")

print("Starting database optimization...")
with engine.connect() as conn:
    print("Nullifying raw_data and metadata_json...")
    conn.execute(text("UPDATE recruiters SET raw_data = NULL, metadata_json = NULL WHERE raw_data IS NOT NULL OR metadata_json IS NOT NULL;"))
    
    print("Converting empty strings to NULL in text columns...")
    columns_to_nullify = ['notes', 'alternate_emails', 'alternate_phones', 'review_reason', 'state_reason']
    for col in columns_to_nullify:
        conn.execute(text(f"UPDATE recruiters SET {col} = NULL WHERE {col} = '';"))
        
    print("Running VACUUM FULL on recruiters table to reclaim disk space...")
    conn.execute(text("VACUUM FULL recruiters;"))
    
    print("Optimization Complete.")
