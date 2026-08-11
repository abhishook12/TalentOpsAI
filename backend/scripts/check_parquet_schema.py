import duckdb
duck = duckdb.connect()
schema = duck.execute("DESCRIBE SELECT * FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full.parquet')").fetchall()
for col in schema:
    print(col[0], col[1])
