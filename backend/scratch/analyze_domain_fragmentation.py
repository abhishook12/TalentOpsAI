import duckdb
import os
import sys

con = duckdb.connect()

FREE_DOMAINS = (
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
)
free_sql = ", ".join(f"'{d}'" for d in FREE_DOMAINS)

# Check total recruiters with valid corporate domain
stats = con.execute(f"""
    SELECT 
        COUNT(*) as total_recruiters,
        COUNT(CASE WHEN email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql}) THEN 1 END) as with_corp_domain,
        COUNT(DISTINCT CASE WHEN email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql}) THEN LOWER(SPLIT_PART(email, '@', 2)) END) as distinct_corp_domains,
        COUNT(DISTINCT company_id) as distinct_company_ids
    FROM 'backend/data/recruiters_full.parquet'
""").fetchone()

print(f"Total recruiters: {stats[0]:,}")
print(f"With corporate domain: {stats[1]:,}")
print(f"Distinct corporate domains: {stats[2]:,}")
print(f"Distinct company_ids currently: {stats[3]:,}")

# Check how many distinct company_ids have a corporate domain
frag_stats = con.execute(f"""
    WITH domain_counts AS (
        SELECT 
            LOWER(SPLIT_PART(email, '@', 2)) as domain,
            COUNT(DISTINCT company_id) as cid_count,
            COUNT(*) as total_rows
        FROM 'backend/data/recruiters_full.parquet'
        WHERE email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql})
        GROUP BY domain
    )
    SELECT 
        COUNT(*) as total_corp_domains,
        COUNT(CASE WHEN cid_count > 1 THEN 1 END) as fragmented_domains,
        SUM(CASE WHEN cid_count > 1 THEN total_rows ELSE 0 END) as rows_in_fragmented_domains
    FROM domain_counts
""").fetchone()

print(f"\nTotal corporate domains: {frag_stats[0]:,}")
print(f"Fragmented domains (>1 company_id): {frag_stats[1]:,}")
print(f"Recruiters affected by fragmentation: {frag_stats[2]:,}")
