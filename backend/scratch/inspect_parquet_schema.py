import duckdb

con = duckdb.connect()
print("Parquet Schema:")
print(con.execute("DESCRIBE SELECT * FROM read_parquet('data/recruiters_full.parquet') LIMIT 1").df())
print("\nTotal row count in Parquet:")
print(con.execute("SELECT COUNT(*) FROM read_parquet('data/recruiters_full.parquet')").fetchall())
print("\nMax recruiter_id in Parquet:")
print(con.execute("SELECT MAX(TRY_CAST(recruiter_id AS BIGINT)) FROM read_parquet('data/recruiters_full.parquet')").fetchall())
