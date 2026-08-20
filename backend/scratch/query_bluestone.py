import duckdb

con = duckdb.connect()
print(con.execute("""
    SELECT 
        CAST(company_id AS VARCHAR) as comp,
        COUNT(*) as cnt,
        MODE(LOWER(SPLIT_PART(email, '@', 2))) as dom
    FROM read_parquet('data/recruiters_full.parquet')
    WHERE CAST(company_id AS VARCHAR) ILIKE '%bluestone%' 
       OR email ILIKE '%bluestone%'
    GROUP BY 1
    ORDER BY 2 DESC
""").df())
