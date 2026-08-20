import duckdb

con = duckdb.connect()
PARQUET = 'backend/data/recruiters_full.parquet'

cnt = con.execute(f"""
    SELECT COUNT(*) FROM '{PARQUET}' 
    WHERE email IS NOT NULL AND email LIKE '%@%'
      AND LOWER(recruiter_name) = LOWER(SPLIT_PART(SPLIT_PART(email, '@', 2), '.', 1))
""").fetchone()[0]

print(f"Recruiters where name was set to company/domain name: {cnt:,}")

samples = con.execute(f"""
    SELECT recruiter_id, recruiter_name, email FROM '{PARQUET}' 
    WHERE email IS NOT NULL AND email LIKE '%@%'
      AND LOWER(recruiter_name) = LOWER(SPLIT_PART(SPLIT_PART(email, '@', 2), '.', 1))
    LIMIT 5
""").fetchall()

for s in samples:
    print("  -> Sample:", s)
