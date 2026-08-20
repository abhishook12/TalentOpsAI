import duckdb
import requests

con = duckdb.connect()
print("Top companies in parquet:")
print(con.execute("""
    SELECT company_name, email, COUNT(*) as cnt 
    FROM read_parquet('data/recruiters_full.parquet') 
    WHERE company_name ILIKE '%waypoint%' OR company_name ILIKE '%warrior%'
    GROUP BY company_name, email
    ORDER BY cnt DESC
    LIMIT 10
""").df())

print("\nDistinct top companies:")
print(con.execute("""
    SELECT company_name, COUNT(*) as cnt 
    FROM read_parquet('data/recruiters_full.parquet') 
    GROUP BY company_name
    ORDER BY cnt DESC
    LIMIT 15
""").df())
