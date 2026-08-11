import duckdb

parquet_path = "C:/TalentOpsAI/backend/data/recruiters_full_pre_cleanup.parquet"
con = duckdb.connect()

print('--- PRE CLEANUP Data Validation Report ---')
count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{parquet_path}')").fetchone()[0]
print(f'Total Rows: {count:,}')

dups = con.execute(f"""
    SELECT email, COUNT(*) as c 
    FROM read_parquet('{parquet_path}') 
    WHERE email IS NOT NULL 
    GROUP BY email 
    HAVING c > 1
""").fetchall()
print(f'Duplicated Emails: {len(dups):,}')

fakes = con.execute(f"""
    SELECT COUNT(*) 
    FROM read_parquet('{parquet_path}') 
    WHERE email LIKE '%@missing.local'
""").fetchone()[0]
print(f'Fake @missing.local Emails: {fakes:,}')

unknowns = con.execute(f"""
    SELECT COUNT(*) 
    FROM read_parquet('{parquet_path}') 
    WHERE LOWER(recruiter_name) IN ('unknown', 'n/a', 'none', 'null', '')
""").fetchone()[0]
print(f'Unknown/Blank Names: {unknowns:,}')
