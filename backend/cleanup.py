import os
import duckdb
from app.database import engine
from sqlalchemy import text

PARQUET_FILE = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"

def cleanup():
    print("Finding active company IDs in Parquet...")
    con = duckdb.connect()
    res = con.execute(f"SELECT DISTINCT company_id FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}') WHERE company_id IS NOT NULL").fetchall()
    active_ids = {row[0] for row in res}
    con.close()
    
    print(f"Found {len(active_ids)} active company IDs in Parquet.")
    
    with engine.begin() as conn:
        all_comps = conn.execute(text("SELECT company_id FROM companies")).fetchall()
        all_ids = {row[0] for row in all_comps}
        print(f"Total companies in Postgres: {len(all_ids)}")
        
        orphaned = all_ids - active_ids
        print(f"Found {len(orphaned)} orphaned companies to delete.")
        
        if orphaned:
            orphaned_list = tuple(orphaned)
            # SQLite / Postgres max vars is high, but let's just delete them directly
            # Or chunk it
            chunk_size = 5000
            orphaned_list = list(orphaned)
            deleted = 0
            for i in range(0, len(orphaned_list), chunk_size):
                chunk = orphaned_list[i:i+chunk_size]
                chunk_str = ','.join(map(str, chunk))
                conn.execute(text(f"DELETE FROM companies WHERE company_id IN ({chunk_str})"))
                deleted += len(chunk)
            print(f"Successfully deleted {deleted} orphaned companies.")
        
if __name__ == "__main__":
    cleanup()
