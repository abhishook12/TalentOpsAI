import duckdb
conn = duckdb.connect()
pq = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'

print('=== TOP 10 STATES ===')
rows = conn.execute(f"""
    SELECT state, COUNT(*) AS cnt 
    FROM read_parquet('{pq}') 
    WHERE state IS NOT NULL AND state != '' AND state != 'US' 
    GROUP BY state ORDER BY cnt DESC LIMIT 10
""").fetchall()
for r in rows:
    print(f'  {r[0]}: {r[1]:,}')

print()
print('=== TOP 10 COMPANIES BY RECRUITER COUNT ===')
rows2 = conn.execute(f"""
    SELECT company_id, COUNT(*) AS cnt 
    FROM read_parquet('{pq}') 
    WHERE company_id IS NOT NULL 
    GROUP BY company_id ORDER BY cnt DESC LIMIT 10
""").fetchall()
for r in rows2:
    print(f'  company_id={r[0]}: {r[1]:,} recruiters')
