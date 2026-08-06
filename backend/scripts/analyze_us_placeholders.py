"""
Deep analysis of the 1.2M 'US' placeholder records to find extractable value.
"""
import duckdb
import pandas as pd

conn = duckdb.connect()
pq = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'

print("=" * 70)
print("DEEP ANALYSIS: 1.2M 'US' Placeholder Records")
print("=" * 70)

# 1. Total count of US placeholders
total_us = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{pq}') WHERE state = 'US'").fetchone()[0]
print(f"\nTotal 'US' placeholder records: {total_us:,}")

# 2. How many have corporate vs generic email domains?
print("\n── Email Domain Analysis ──")
domain_breakdown = conn.execute(f"""
    SELECT 
        CASE 
            WHEN email LIKE '%@gmail.com' THEN 'gmail.com'
            WHEN email LIKE '%@yahoo.com' THEN 'yahoo.com'
            WHEN email LIKE '%@hotmail.com' THEN 'hotmail.com'
            WHEN email LIKE '%@outlook.com' THEN 'outlook.com'
            WHEN email LIKE '%@aol.com' THEN 'aol.com'
            WHEN email LIKE '%@icloud.com' THEN 'icloud.com'
            WHEN email LIKE '%@live.com' THEN 'live.com'
            WHEN email LIKE '%@msn.com' THEN 'msn.com'
            WHEN email LIKE '%@ymail.com' THEN 'ymail.com'
            WHEN email LIKE '%@comcast.net' THEN 'comcast.net'
            WHEN email LIKE '%@missing.local' THEN 'missing.local (placeholder)'
            WHEN email LIKE '%@invalid.local' THEN 'invalid.local (placeholder)'
            WHEN email IS NULL OR email = '' THEN 'NO EMAIL'
            ELSE 'CORPORATE DOMAIN'
        END AS domain_type,
        COUNT(*) as cnt
    FROM read_parquet('{pq}')
    WHERE state = 'US'
    GROUP BY domain_type
    ORDER BY cnt DESC
""").fetchall()

for dtype, cnt in domain_breakdown:
    pct = cnt / total_us * 100
    print(f"  {dtype:40s} {cnt:>10,}  ({pct:5.1f}%)")

# 3. Top 30 corporate domains
print("\n── Top 30 Corporate Domains (non-generic) ──")
top_domains = conn.execute(f"""
    SELECT 
        SPLIT_PART(email, '@', 2) AS domain,
        COUNT(*) AS cnt
    FROM read_parquet('{pq}')
    WHERE state = 'US'
      AND email IS NOT NULL
      AND SPLIT_PART(email, '@', 2) NOT IN (
          'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com',
          'icloud.com','live.com','msn.com','ymail.com','comcast.net',
          'missing.local','invalid.local','example.com'
      )
    GROUP BY domain
    ORDER BY cnt DESC
    LIMIT 30
""").fetchall()

for domain, cnt in top_domains:
    print(f"  {domain:40s} {cnt:>8,}")

# 4. How many have a recruiter_name that looks like a real person (has a space)?
print("\n── Name Quality Analysis ──")
name_quality = conn.execute(f"""
    SELECT
        COUNT(*) FILTER (WHERE recruiter_name IS NOT NULL AND recruiter_name != '' AND recruiter_name LIKE '% %') AS multi_word_names,
        COUNT(*) FILTER (WHERE recruiter_name IS NOT NULL AND recruiter_name != '' AND recruiter_name NOT LIKE '% %') AS single_word_names,
        COUNT(*) FILTER (WHERE recruiter_name IS NULL OR recruiter_name = '') AS no_name,
        COUNT(*) FILTER (WHERE recruiter_name LIKE '%@%') AS email_in_name,
        COUNT(*) FILTER (WHERE LENGTH(recruiter_name) < 3) AS very_short_names
    FROM read_parquet('{pq}')
    WHERE state = 'US'
""").fetchone()

print(f"  Multi-word names (likely real):  {name_quality[0]:>10,}")
print(f"  Single-word names:               {name_quality[1]:>10,}")
print(f"  No name at all:                  {name_quality[2]:>10,}")
print(f"  Email in name field:             {name_quality[3]:>10,}")
print(f"  Very short names (<3 chars):     {name_quality[4]:>10,}")

# 5. How many have ANY other useful field populated?
print("\n── Field Completeness (among US placeholders) ──")
fields = conn.execute(f"""
    SELECT
        COUNT(*) FILTER (WHERE phone IS NOT NULL AND phone != '') AS has_phone,
        COUNT(*) FILTER (WHERE location IS NOT NULL AND location != '') AS has_location,
        COUNT(*) FILTER (WHERE company_id IS NOT NULL) AS has_company,
        COUNT(*) FILTER (WHERE linkedin IS NOT NULL AND linkedin != '') AS has_linkedin,
        COUNT(*) FILTER (WHERE title IS NOT NULL AND title != '') AS has_title,
        COUNT(*) FILTER (WHERE notes IS NOT NULL AND notes != '') AS has_notes,
        COUNT(*) FILTER (WHERE specialization IS NOT NULL AND specialization != '') AS has_specialization
    FROM read_parquet('{pq}')
    WHERE state = 'US'
""").fetchone()

labels = ['phone', 'location', 'company_id', 'linkedin', 'title', 'notes', 'specialization']
for label, val in zip(labels, fields):
    pct = val / total_us * 100
    print(f"  Has {label:20s} {val:>10,}  ({pct:5.1f}%)")

# 6. Cross-reference: how many corporate domains match domains in the NON-US records?
print("\n── Corporate Domain Cross-Reference ──")
crossref = conn.execute(f"""
    WITH us_domains AS (
        SELECT DISTINCT SPLIT_PART(email, '@', 2) AS domain
        FROM read_parquet('{pq}')
        WHERE state = 'US'
          AND email IS NOT NULL
          AND SPLIT_PART(email, '@', 2) NOT IN (
              'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com',
              'icloud.com','live.com','msn.com','ymail.com','comcast.net',
              'missing.local','invalid.local','example.com'
          )
    ),
    known_domains AS (
        SELECT DISTINCT SPLIT_PART(email, '@', 2) AS domain, state
        FROM read_parquet('{pq}')
        WHERE state != 'US' AND state IS NOT NULL AND state != ''
          AND email IS NOT NULL
          AND SPLIT_PART(email, '@', 2) NOT IN (
              'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com',
              'icloud.com','live.com','msn.com','ymail.com','comcast.net',
              'missing.local','invalid.local','example.com'
          )
    )
    SELECT COUNT(DISTINCT ud.domain)
    FROM us_domains ud
    JOIN known_domains kd ON ud.domain = kd.domain
""").fetchone()[0]

total_corp_domains_us = conn.execute(f"""
    SELECT COUNT(DISTINCT SPLIT_PART(email, '@', 2))
    FROM read_parquet('{pq}')
    WHERE state = 'US'
      AND email IS NOT NULL
      AND SPLIT_PART(email, '@', 2) NOT IN (
          'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com',
          'icloud.com','live.com','msn.com','ymail.com','comcast.net',
          'missing.local','invalid.local','example.com'
      )
""").fetchone()[0]

print(f"  Corporate domains in US placeholders: {total_corp_domains_us:,}")
print(f"  Of those, matchable to known states:  {crossref:,}")

# 7. How many US records could be resolved via domain matching?
print("\n── Recoverable Records via Domain Matching ──")
recoverable = conn.execute(f"""
    WITH known_domain_states AS (
        SELECT 
            SPLIT_PART(email, '@', 2) AS domain,
            MODE(state) AS consensus_state
        FROM read_parquet('{pq}')
        WHERE state != 'US' AND state IS NOT NULL AND state != ''
          AND email IS NOT NULL
          AND SPLIT_PART(email, '@', 2) NOT IN (
              'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com',
              'icloud.com','live.com','msn.com','ymail.com','comcast.net',
              'missing.local','invalid.local','example.com'
          )
        GROUP BY SPLIT_PART(email, '@', 2)
    )
    SELECT COUNT(*)
    FROM read_parquet('{pq}') r
    JOIN known_domain_states kds ON SPLIT_PART(r.email, '@', 2) = kds.domain
    WHERE r.state = 'US'
""").fetchone()[0]

print(f"  Records recoverable via domain matching: {recoverable:,}")
print(f"  Remaining truly unresolvable:             {total_us - recoverable:,}")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
