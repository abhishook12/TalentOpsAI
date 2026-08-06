import psycopg, os
from dotenv import load_dotenv
load_dotenv('C:/TalentOpsAI/backend/.env')

conn = psycopg.connect(os.getenv('DATABASE_URL').replace('postgresql+psycopg://','postgresql://'), autocommit=True)
cur = conn.cursor()

# 1. Recruiters table schema
cur.execute("SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'recruiters' ORDER BY ordinal_position")
cols = cur.fetchall()
print("RECRUITERS TABLE COLUMNS:")
for c in cols:
    print(f"  {c[0]}: {c[1]} (max_len: {c[2]})")
print(f"\nTotal columns: {len(cols)}")

# 2. What FK references exist to recruiters
print("\n--- FOREIGN KEY REFERENCES TO recruiters ---")
cur.execute("""
    SELECT tc.table_name, kcu.column_name, ccu.column_name AS foreign_column
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'recruiters'
""")
fks = cur.fetchall()
for fk in fks:
    print(f"  {fk[0]}.{fk[1]} -> recruiters.{fk[2]}")

# 3. Average row size estimation
cur.execute("SELECT pg_total_relation_size('recruiters') / GREATEST(COUNT(*),1) FROM recruiters")
avg_row = cur.fetchone()[0]
print(f"\nAverage row size (with indexes): {avg_row} bytes")

# 4. Column-level size estimation for big text columns
print("\n--- ESTIMATED SIZE PER COLUMN ---")
for col in [c[0] for c in cols]:
    try:
        cur.execute(f"SELECT AVG(LENGTH(CAST({col} AS TEXT))) FROM recruiters WHERE {col} IS NOT NULL LIMIT 10000")
        avg = cur.fetchone()[0]
        if avg:
            print(f"  {col}: avg {avg:.0f} chars")
    except:
        pass

# 5. Bucket storage status
print("\n--- BUCKET STORAGE STATUS ---")
cur.execute("SELECT name, metadata FROM storage.objects WHERE bucket_id = 'recruiter-data' ORDER BY created_at DESC LIMIT 10")
for row in cur.fetchall():
    print(f"  {row[0]} | metadata: {row[1]}")

# 6. Parquet archive on disk
import pandas as pd
parquet_path = 'C:/TalentOpsAI/backend/archived_recruiters_unified.parquet'
if os.path.exists(parquet_path):
    df = pd.read_parquet(parquet_path)
    print(f"\nLocal Parquet archive: {len(df):,} rows, {os.path.getsize(parquet_path)/1024/1024:.2f} MB")
    print(f"Columns: {list(df.columns)}")

conn.close()
