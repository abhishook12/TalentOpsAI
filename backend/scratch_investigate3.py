import pandas as pd
from app.database import engine
from sqlalchemy import text
import json

query = """
SELECT recruiter_id, recruiter_name, email, raw_data 
FROM recruiters 
WHERE recruiter_name = 'Tek Systems' 
LIMIT 5;
"""
print("Checking raw_data for corrupted records:")
with engine.connect() as conn:
    df = pd.read_sql_query(text(query), conn)
    for idx, row in df.iterrows():
        print(f"ID: {row['recruiter_id']}, Name: {row['recruiter_name']}, Email: {row['email']}")
        print(f"Raw Data: {row['raw_data']}")
        print("-" * 40)
