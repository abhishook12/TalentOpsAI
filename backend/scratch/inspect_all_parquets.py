import duckdb
import glob
import os

print("=" * 80)
print("INSPECTING ALL PARQUET DATASETS IN TALENTOPS")
print("=" * 80)

for p in sorted(glob.glob("c:/TalentOpsAI/backend/data/*.parquet*")):
    if os.path.isfile(p):
        try:
            con = duckdb.connect()
            cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{p.replace(os.sep, '/')}')").fetchone()[0]
            con.close()
            size_mb = round(os.path.getsize(p) / (1024 * 1024), 2)
            print(f"{os.path.basename(p):<50} | Count: {cnt:>10,} | Size: {size_mb:>6} MB")
        except Exception as e:
            print(f"{os.path.basename(p):<50} | Error: {str(e)[:60]}")
