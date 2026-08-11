import duckdb
duck = duckdb.connect()
print('Testing read_parquet...')
try:
    print(duck.execute("SELECT * FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full.parquet') LIMIT 5").fetchall())
except Exception as e:
    print('Error:', e)
