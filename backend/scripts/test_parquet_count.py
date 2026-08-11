import duckdb
duck = duckdb.connect()
print('Testing read_parquet count...')
try:
    print(duck.execute("SELECT COUNT(*) FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full.parquet')").fetchall())
except Exception as e:
    print('Error:', e)
