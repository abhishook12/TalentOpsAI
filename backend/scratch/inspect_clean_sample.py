import duckdb

con = duckdb.connect()
PARQUET = 'backend/data/recruiters_full.parquet'

rows = con.execute(f"""
    SELECT recruiter_id, recruiter_name, email, phone, title
    FROM '{PARQUET}'
    WHERE email LIKE '%@systemone.com'
    LIMIT 20
""").fetchall()

for r in rows:
    print(r)
