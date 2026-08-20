import duckdb

con = duckdb.connect()
con.execute("""
    CREATE TABLE company_overall AS
    SELECT 
        CAST(company_id AS VARCHAR) AS company_key,
        COUNT(*) AS total_recs,
        MODE(LOWER(SPLIT_PART(email, '@', 2))) FILTER (
            WHERE email IS NOT NULL 
              AND email LIKE '%@%'
              AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com')
              AND LENGTH(SPLIT_PART(email, '@', 2)) > 2
        ) AS true_dominant_domain
    FROM read_parquet('data/recruiters_full.parquet')
    WHERE company_id IS NOT NULL 
      AND TRIM(CAST(company_id AS VARCHAR)) != ''
      AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('need to fill data', 'unknown', 'n/a', 'none', 'null')
      AND INSTR(CAST(company_id AS VARCHAR), '|') = 0
    GROUP BY company_key
    ORDER BY total_recs DESC
""")

print("Top 10 rolled-up companies with TRUE dominant domain:")
print(con.execute("SELECT * FROM company_overall LIMIT 10").df())
