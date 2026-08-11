import os
import sys
from sqlalchemy import text
import pandas as pd

sys.path.append(r'C:\TalentOpsAI\backend')
from app.database import engine

def fix_duplicates():
    with engine.connect() as conn:
        with conn.begin():
            print("Finding case-insensitive duplicates...")
            
            # Find duplicated lowercase emails
            df = pd.read_sql("""
                SELECT LOWER(BTRIM(email)) as norm_email, array_agg(recruiter_id) as ids
                FROM recruiters
                GROUP BY LOWER(BTRIM(email))
                HAVING COUNT(*) > 1
            """, conn)
            
            print(f"Found {len(df)} duplicated emails.")
            
            delete_ids = []
            for _, row in df.iterrows():
                # Keep the first ID, delete the rest
                ids = row['ids']
                delete_ids.extend(ids[1:])
                
            if delete_ids:
                print(f"Deleting {len(delete_ids)} duplicate recruiters...")
                # Delete in chunks
                chunk_size = 1000
                for i in range(0, len(delete_ids), chunk_size):
                    chunk = delete_ids[i:i+chunk_size]
                    conn.execute(text("DELETE FROM recruiters WHERE recruiter_id = ANY(:ids)"), {"ids": chunk})
                print("Deleted.")
            else:
                print("No duplicates to delete.")

if __name__ == "__main__":
    fix_duplicates()
