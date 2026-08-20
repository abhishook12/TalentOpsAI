import duckdb

con = duckdb.connect()
PARQUET = 'backend/data/recruiters_full.parquet'

print("--- FULL AUDIT OF DATASET CORRUPTIONS & DUPLICATES ---")

total_rows = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}'").fetchone()[0]
print(f"Total Rows: {total_rows:,}")

# 1. Negative recruiter IDs
neg_ids = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_id < 0").fetchone()[0]
print(f"1. Negative recruiter_id rows: {neg_ids:,}")

# 2. Duplicate rows by email (where email is present)
dup_email_rows = con.execute(f"""
    SELECT COUNT(*) FROM (
        SELECT LOWER(email), COUNT(*) 
        FROM '{PARQUET}' 
        WHERE email IS NOT NULL AND email LIKE '%@%'
        GROUP BY LOWER(email) 
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]
print(f"2. Unique emails with multiple duplicate entries: {dup_email_rows:,}")

# 3. Recruiter names that are emails, phone numbers, or junk
email_in_name = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_name LIKE '%@%'").fetchone()[0]
phone_in_name = con.execute(f"SELECT COUNT(*) FROM '{PARQUET}' WHERE recruiter_name SIMILAR TO '[0-9+() -]+' AND LENGTH(recruiter_name) > 6").fetchone()[0]
single_first_name_only = con.execute(f"""
    SELECT COUNT(*) FROM '{PARQUET}' 
    WHERE recruiter_name NOT LIKE '% %' 
      AND email LIKE '%.%@%'
""").fetchone()[0]

print(f"3. Recruiter names that are email addresses: {email_in_name:,}")
print(f"4. Recruiter names that are phone numbers/numeric: {phone_in_name:,}")
print(f"5. Recruiter names with only 1 word when email has first.last format: {single_first_name_only:,}")

# 6. Emails where company_id is NULL or not mapped to company
unmapped_company = con.execute(f"""
    SELECT COUNT(*) FROM '{PARQUET}' 
    WHERE (company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' OR LOWER(CAST(company_id AS VARCHAR)) IN ('unknown', 'n/a', 'none', 'null'))
      AND email LIKE '%@%'
""").fetchone()[0]
print(f"6. Valid emails with unmapped/unknown company: {unmapped_company:,}")
