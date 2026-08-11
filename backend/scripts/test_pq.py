import duckdb
try:
    print(duckdb.execute("SELECT COUNT(*) FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full.parquet')").fetchone()[0])
except Exception as e:
    print("Error:", e)
