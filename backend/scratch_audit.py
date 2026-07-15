import os
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DB_URL)

query = """
SELECT 
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(C.oid)) AS total_size,
    pg_total_relation_size(C.oid) as raw_size
FROM pg_class C
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
WHERE nspname NOT IN ('pg_catalog', 'information_schema')
  AND C.relkind <> 'i'
  AND nspname !~ '^pg_toast'
ORDER BY pg_total_relation_size(C.oid) DESC
LIMIT 10;
"""

with engine.connect() as conn:
    print("Top Tables by Size:")
    res = conn.execute(text(query)).fetchall()
    for row in res:
        print(row)
        
    print("\nTotal DB Size:")
    res = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
    print(res)
