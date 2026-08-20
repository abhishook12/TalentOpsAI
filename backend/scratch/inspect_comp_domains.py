import duckdb

con = duckdb.connect()
print("Top 10 email domains for company_id 161735:")
print(con.execute("""
    SELECT 
        LOWER(SPLIT_PART(email, '@', 2)) as domain,
        COUNT(*) as cnt
    FROM read_parquet('data/recruiters_full.parquet')
    WHERE CAST(company_id AS VARCHAR) = '161735'
    GROUP BY domain
    ORDER BY cnt DESC
    LIMIT 10
""").df())

print("\nTop 10 email domains for company_id 168275:")
print(con.execute("""
    SELECT 
        LOWER(SPLIT_PART(email, '@', 2)) as domain,
        COUNT(*) as cnt
    FROM read_parquet('data/recruiters_full.parquet')
    WHERE CAST(company_id AS VARCHAR) = '168275'
    GROUP BY domain
    ORDER BY cnt DESC
    LIMIT 10
""").df())
