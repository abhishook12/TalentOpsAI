import duckdb
c1 = duckdb.query("SELECT COUNT(1) FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full.parquet')").fetchone()[0]
c2 = duckdb.query("SELECT COUNT(1) FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full_backup.parquet')").fetchone()[0]
c3 = duckdb.query("SELECT COUNT(1) FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full_pre_cleanup.parquet')").fetchone()[0]
print(f"full: {c1}")
print(f"backup: {c2}")
print(f"pre_cleanup: {c3}")
