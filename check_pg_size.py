import psycopg2

DATABASE_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
SELECT relname as "Table",
       pg_size_pretty(pg_total_relation_size(relid)) As "Size",
       pg_total_relation_size(relid) as "Size_Bytes"
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
""")

print("Database Tables by Size:")
for row in cur.fetchall():
    print(f"{row[0]:<30} {row[1]:<15} {row[2]}")

cur.close()
conn.close()
