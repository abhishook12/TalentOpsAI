from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
with engine.connect() as conn:
    print("Database Size:", conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()));")).scalar())
    
    rows = conn.execute(text("SELECT relname as table, pg_size_pretty(pg_total_relation_size(relid)) as size FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;")).fetchall()
    print("\nTable Sizes:")
    for row in rows:
        print(f"{row[0]}: {row[1]}")
