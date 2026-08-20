import duckdb

con = duckdb.connect()
rows = con.execute("""
    SELECT 
        company_id, 
        COUNT(*) as cnt, 
        COUNT(DISTINCT email) as distinct_emails,
        MIN(email) as sample_email
    FROM 'backend/data/recruiters_full.parquet'
    WHERE LOWER(SPLIT_PART(email, '@', 2)) = 'rht.com'
    GROUP BY company_id
    ORDER BY cnt DESC
""").fetchall()

print("--- RHT.COM ROWS IN PARQUET ---")
for r in rows:
    print(r)

# Check other high volume domains that have fragmented company_ids
frag = con.execute("""
    SELECT 
        LOWER(SPLIT_PART(email, '@', 2)) as domain,
        COUNT(DISTINCT company_id) as distinct_company_ids,
        COUNT(*) as total_recruiters
    FROM 'backend/data/recruiters_full.parquet'
    WHERE email IS NOT NULL 
      AND email LIKE '%@%'
      AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN (
          'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
          'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
          'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
          'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
      )
    GROUP BY domain
    HAVING COUNT(DISTINCT company_id) > 1
    ORDER BY total_recruiters DESC
    LIMIT 20
""").fetchall()

print("\n--- TOP FRAGMENTED DOMAINS ---")
for f in frag:
    print(f)
