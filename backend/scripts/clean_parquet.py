import duckdb
import os
import time

parquet_path = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
temp_parquet_path = "C:/TalentOpsAI/backend/data/recruiters_full_temp.parquet"

def clean_data():
    con = duckdb.connect()
    
    print("Loading data...")
    con.execute(f"CREATE TABLE recruiters AS SELECT * FROM read_parquet('{parquet_path}')")
    
    # 1. Deduplication
    print("Deduplicating by email...")
    con.execute("""
        CREATE TABLE recruiters_dedup AS 
        SELECT * FROM recruiters WHERE email IS NULL
        UNION ALL
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, ROW_NUMBER() OVER(PARTITION BY email ORDER BY completeness_score DESC, updated_at DESC) as rn
            FROM recruiters
            WHERE email IS NOT NULL
        ) WHERE rn = 1
    """)
    
    # Drop old table and rename
    con.execute("DROP TABLE recruiters")
    con.execute("ALTER TABLE recruiters_dedup RENAME TO recruiters")
    
    # 2. Nullify fake emails
    print("Nullifying fake emails...")
    con.execute("UPDATE recruiters SET email = NULL WHERE email LIKE '%@missing.local'")
    
    # 3. Clean up names
    print("Cleaning up names...")
    # Register Python UDF for title casing
    def title_case(x):
        if not x: return ""
        x = str(x).strip()
        if x.lower() in ['unknown', 'n/a', 'none', 'null', '']: return ""
        return x.title()
        
    con.create_function('clean_name_udf', title_case, ['VARCHAR'], 'VARCHAR')
    
    con.execute("UPDATE recruiters SET recruiter_name = clean_name_udf(recruiter_name)")
    con.execute("UPDATE recruiters SET recruiter_name = NULL WHERE recruiter_name = ''")
    
    print("Writing to parquet...")
    con.execute(f"COPY recruiters TO '{temp_parquet_path}' (FORMAT PARQUET)")
    
    print("Done. Replacing original file.")
    con.close()
    
    os.replace(temp_parquet_path, parquet_path)

if __name__ == '__main__':
    start = time.time()
    clean_data()
    print(f"Finished in {time.time() - start:.2f} seconds.")
