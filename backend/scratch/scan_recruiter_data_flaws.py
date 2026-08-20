import duckdb

con = duckdb.connect()
PARQUET = 'backend/data/recruiters_full.parquet'

cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM '{PARQUET}'").fetchall()]
print("Columns in Parquet:", cols)

print("\n--- RECRUITERS MATCHING SYSTEMONE ---")
rows = con.execute(f"""
    SELECT recruiter_id, recruiter_name, email, company_id, phone, title
    FROM '{PARQUET}'
    WHERE email LIKE '%@systemone.com' OR recruiter_name LIKE '%@systemone.com'
    LIMIT 30
""").fetchall()

for r in rows:
    print(r)

print("\n--- GENERAL DATA QUALITY ANOMALY SCAN ---")
# 1. Names that are emails
name_is_email = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_name LIKE '%@%'").fetchone()[0]
print(f"1. Recruiters where recruiter_name is an email address: {name_is_email:,}")

# 2. Email is NULL or empty but recruiter_name has '@'
email_in_name_missing_email = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE (email IS NULL OR email = '') AND recruiter_name LIKE '%@%'").fetchone()[0]
print(f"2. Missing email where name has email: {email_in_name_missing_email:,}")

# 3. Duplicate recruiter records (same email and name)
dup_records = con.execute(f"""
    SELECT COUNT(*) FROM (
        SELECT LOWER(email), COUNT(*) 
        FROM '{PARQUET}' 
        WHERE email IS NOT NULL AND email LIKE '%@%'
        GROUP BY LOWER(email) 
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]
print(f"3. Distinct emails with duplicate recruiter records: {dup_records:,}")

dup_total_rows = con.execute(f"""
    SELECT SUM(cnt) FROM (
        SELECT COUNT(*) as cnt
        FROM '{PARQUET}' 
        WHERE email IS NOT NULL AND email LIKE '%@%'
        GROUP BY LOWER(email) 
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]
print(f"   -> Total duplicate recruiter rows: {dup_total_rows:,}")

# 4. What does the search endpoint do when searching for 'systemone'?
