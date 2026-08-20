import os
import duckdb
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv("c:/TalentOpsAI/backend/.env")

parquet_files = [
    "c:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet",
    "c:/TalentOpsAI/backend/data/recruiters_full.parquet",
    "c:/TalentOpsAI/backend/archived_recruiters_unified.parquet",
    "c:/TalentOpsAI/local_storage_import.parquet"
]

con = duckdb.connect()
for f in parquet_files:
    if os.path.exists(f):
        print(f"\n=== PARQUET: {f} ===")
        desc = con.execute(f"DESCRIBE SELECT * FROM '{f}'").df()
        print(desc[['column_name', 'column_type']].to_string())
        sample = con.execute(f"SELECT * FROM '{f}' LIMIT 2").df()
        print("Sample row:", sample.columns.tolist())

db_url = os.environ.get("DATABASE_URL")
if db_url:
    try:
        print("\n=== POSTGRES DATABASE ===")
        engine = create_engine(db_url)
        insp = inspect(engine)
        tables = insp.get_table_names()
        print(f"Tables in DB: {tables}")
        for t in ['companies', 'recruiters']:
            if t in tables:
                cols = insp.get_columns(t)
                print(f"Columns in '{t}': {[c['name'] for c in cols]}")
    except Exception as e:
        print("PG Error:", e)
