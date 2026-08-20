import duckdb

con = duckdb.connect()
PARQUET = 'backend/data/recruiters_full.parquet'

print("--- SYSTEMONE ROWS IN PARQUET ---")
rows = con.execute(f"""
    SELECT recruiter_id, recruiter_name, email, phone, title, company_id
    FROM '{PARQUET}'
    WHERE email LIKE '%systemone.com%' OR recruiter_name LIKE '%systemone.com%'
    ORDER BY recruiter_name
    LIMIT 30
""").fetchall()

for r in rows:
    print(r)
