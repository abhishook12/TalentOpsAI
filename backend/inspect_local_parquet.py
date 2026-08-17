import duckdb

con = duckdb.connect(':memory:')
path = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"
res = con.execute(f"SELECT COUNT(*) FROM read_parquet('{path}')").fetchone()[0]
print(f"Local Parquet Total Rows: {res:,}")

sample = con.execute(f"""
    SELECT recruiter_id, recruiter_name, email, company_id, state, normalized_city, phone, title 
    FROM read_parquet('{path}') 
    WHERE email IS NOT NULL 
    LIMIT 10
""").fetchdf()
print("\nSample 10 Records:")
print(sample.to_string())

# Distribution of company_id types
comp_dist = con.execute(f"""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' THEN 1 END) as null_empty_comp,
        COUNT(CASE WHEN LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0') THEN 1 END) as placeholder_comp,
        COUNT(CASE WHEN company_id IS NOT NULL 
                        AND TRIM(CAST(company_id AS VARCHAR)) != '' 
                        AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0') THEN 1 END) as valid_comp_keys,
        COUNT(DISTINCT CASE WHEN company_id IS NOT NULL THEN CAST(company_id AS VARCHAR) END) as distinct_comp_keys
    FROM read_parquet('{path}')
""").fetchdf()
print("\nCompany ID Distribution on 2.3M records:")
print(comp_dist.to_string())
