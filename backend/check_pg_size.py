import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("Executing pg_stat_user_tables size query...")
    query = text("""
        SELECT relname as "Table",
               pg_size_pretty(pg_total_relation_size(relid)) As "Size",
               pg_total_relation_size(relid) as "SizeBytes"
        FROM pg_catalog.pg_statio_user_tables 
        ORDER BY pg_total_relation_size(relid) DESC;
    """)
    result = conn.execute(query)
    for row in result:
        print(row)
        
    print("---")
    size_query = text("SELECT pg_database_size(current_database()) / 1048576.0")
    print(f"Total DB Size: {conn.execute(size_query).scalar()} MB")
