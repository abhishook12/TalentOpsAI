import duckdb
import os

PARQUET_FILE = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'
try:
    con = duckdb.connect()
    query = f"""
        SELECT 
            CAST(LOWER(SPLIT_PART(email, '@', 2)) AS VARCHAR) as domain,
            COUNT(*) as recruiter_count
        FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
        WHERE email IS NOT NULL AND email != ''
        GROUP BY 1
        ORDER BY 2 DESC
    """
    res = con.execute(query).fetchall()
    print(f"Success! Got {len(res)} domains.")
except Exception as e:
    print(f"Error: {e}")
