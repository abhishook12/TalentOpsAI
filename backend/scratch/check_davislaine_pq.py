import duckdb
con = duckdb.connect()
res = con.execute("""
    SELECT recruiter_id, recruiter_name, email, phone, location 
    FROM read_parquet('c:/TalentOpsAI/backend/data/recruiters_full.parquet') 
    WHERE email LIKE '%@davislaine.com%'
""").fetchdf()
print(res.to_string())
con.close()
