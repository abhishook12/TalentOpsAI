import duckdb
conn = duckdb.connect()
pq = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'
rows = conn.execute(f"""
    SELECT TRY_CAST(company_id AS INTEGER) as cid, COUNT(*) AS cnt
    FROM read_parquet('{pq}')
    WHERE TRY_CAST(company_id AS INTEGER) IN (28002, 332)
    GROUP BY cid
""").fetchall()
print(rows)
