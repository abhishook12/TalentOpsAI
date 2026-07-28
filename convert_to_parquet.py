import sqlite3
import pandas as pd
import os

DB_PATH = r"C:\TalentOpsAI\local_storage_import.db"
PARQUET_PATH = r"C:\TalentOpsAI\local_storage_import.parquet"

print(f"Reading from {DB_PATH}...")
conn = sqlite3.connect(DB_PATH)

try:
    df = pd.read_sql_query("SELECT * FROM imported_recruiters", conn)
    print(f"Loaded {len(df)} records from SQLite.")

    # Convert object columns to category for extreme compression
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype('category')

    print(f"Squeezing data into highly compressed Parquet format...")
    # Use PyArrow engine with snappy compression and dictionary encoding
    df.to_parquet(PARQUET_PATH, engine='pyarrow', compression='snappy', index=False)
    
    orig_size = os.path.getsize(DB_PATH) / (1024*1024)
    new_size = os.path.getsize(PARQUET_PATH) / (1024*1024)
    
    print(f"==================================================")
    print(f"SQLite Size:  {orig_size:.2f} MB")
    print(f"Parquet Size: {new_size:.2f} MB")
    print(f"Compression Ratio: {orig_size / new_size:.2f}x smaller!")
    print(f"==================================================")
    print("Squeezing complete. Maximum data in least storage achieved.")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
