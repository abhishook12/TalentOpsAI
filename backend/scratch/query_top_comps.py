import duckdb

con = duckdb.connect()
print(con.execute("""
    SELECT 
        CAST(company_id AS VARCHAR) AS comp,
        MODE(LOWER(SPLIT_PART(email, '@', 2))) as dom,
        COUNT(*) as cnt
    FROM read_parquet('data/recruiters_full.parquet')
    GROUP BY comp
    ORDER BY cnt DESC
    LIMIT 20
""").df())
