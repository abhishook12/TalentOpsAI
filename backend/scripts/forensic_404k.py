"""Forensic analysis of the final 404K unresolvable records."""
import duckdb

conn = duckdb.connect()
pq = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'

print("=" * 60)
print("FORENSIC ANALYSIS: 404K Remaining 'US' Records")
print("=" * 60)

total = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{pq}') WHERE state = 'US'").fetchone()[0]
print(f"Total remaining: {total:,}")

# Category 1: No email at all
no_email = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{pq}') WHERE state = 'US' AND (email IS NULL OR email = '')").fetchone()[0]
print(f"\n[CAT-1] No email at all: {no_email:,} ({no_email/total*100:.1f}%)")

# Category 2: Placeholder emails (missing.local, invalid.local)
placeholder = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{pq}') WHERE state = 'US' AND (email LIKE '%missing.local' OR email LIKE '%invalid.local' OR email LIKE '%example.com')").fetchone()[0]
print(f"[CAT-2] Placeholder emails: {placeholder:,} ({placeholder/total*100:.1f}%)")

# Category 3: Generic email only (gmail, yahoo, etc)
generic = conn.execute(f"""SELECT COUNT(*) FROM read_parquet('{pq}') WHERE state = 'US' 
    AND email IS NOT NULL AND email != ''
    AND (email LIKE '%@gmail.com' OR email LIKE '%@yahoo.com' OR email LIKE '%@hotmail.com' 
         OR email LIKE '%@outlook.com' OR email LIKE '%@aol.com' OR email LIKE '%@icloud.com'
         OR email LIKE '%@live.com' OR email LIKE '%@msn.com' OR email LIKE '%@ymail.com'
         OR email LIKE '%@comcast.net')""").fetchone()[0]
print(f"[CAT-3] Generic email (gmail/yahoo/etc): {generic:,} ({generic/total*100:.1f}%)")

# Category 4: Corporate email but orphan domain (no peers with known state)
corp_orphan = total - no_email - placeholder - generic
print(f"[CAT-4] Corporate email, orphan domain: {corp_orphan:,} ({corp_orphan/total*100:.1f}%)")

# Name quality within each category
print("\n--- Name Quality Breakdown ---")
for cat, where in [
    ("No email", "(email IS NULL OR email = '')"),
    ("Placeholder email", "(email LIKE '%missing.local' OR email LIKE '%invalid.local')"),
    ("Generic email", "(email LIKE '%@gmail.com' OR email LIKE '%@yahoo.com' OR email LIKE '%@hotmail.com' OR email LIKE '%@outlook.com' OR email LIKE '%@aol.com')"),
]:
    row = conn.execute(f"""
        SELECT 
            COUNT(*) FILTER (WHERE recruiter_name IS NOT NULL AND recruiter_name LIKE '% %' AND recruiter_name NOT LIKE '%@%') AS good_name,
            COUNT(*) FILTER (WHERE recruiter_name IS NULL OR recruiter_name = '' OR LENGTH(recruiter_name) < 3) AS bad_name,
            COUNT(*) FILTER (WHERE recruiter_name LIKE '%@%') AS email_as_name,
            COUNT(*) FILTER (WHERE company_id IS NOT NULL) AS has_company,
            COUNT(*) FILTER (WHERE phone IS NOT NULL AND phone != '') AS has_phone
        FROM read_parquet('{pq}') WHERE state = 'US' AND {where}
    """).fetchone()
    print(f"  {cat:25s} | good_name={row[0]:>7,} bad_name={row[1]:>7,} email_as_name={row[2]:>7,} has_company={row[3]:>7,} has_phone={row[4]:>7,}")

# Sample the truly empty ones
print("\n--- Sample: No Email, No Company ---")
samples = conn.execute(f"""
    SELECT recruiter_name, email, phone, company_id, title
    FROM read_parquet('{pq}')
    WHERE state = 'US' AND (email IS NULL OR email = '') AND company_id IS NULL
    LIMIT 10
""").fetchall()
for s in samples:
    print(f"  name={s[0]} | email={s[1]} | phone={s[2]} | company={s[3]} | title={s[4]}")

# Sample corporate orphans
print("\n--- Sample: Corporate Orphan Domains ---")
samples2 = conn.execute(f"""
    SELECT recruiter_name, email, company_id, title
    FROM read_parquet('{pq}')
    WHERE state = 'US' 
      AND email IS NOT NULL AND email != ''
      AND email NOT LIKE '%@gmail.com' AND email NOT LIKE '%@yahoo.com'
      AND email NOT LIKE '%@hotmail.com' AND email NOT LIKE '%@outlook.com'
      AND email NOT LIKE '%missing.local' AND email NOT LIKE '%invalid.local'
    LIMIT 15
""").fetchall()
for s in samples2:
    print(f"  name={s[0]} | email={s[1]} | company={s[2]} | title={s[3]}")

# Junk score classification
print("\n--- JUNK CLASSIFICATION ---")
pure_junk = conn.execute(f"""
    SELECT COUNT(*) FROM read_parquet('{pq}')
    WHERE state = 'US'
      AND (recruiter_name IS NULL OR recruiter_name = '' OR LENGTH(recruiter_name) < 3 OR recruiter_name LIKE '%@%')
      AND (email IS NULL OR email = '' OR email LIKE '%missing.local' OR email LIKE '%invalid.local')
      AND (phone IS NULL OR phone = '')
      AND company_id IS NULL
""").fetchone()[0]
print(f"  PURE JUNK (no useful data at all): {pure_junk:,}")

low_value = conn.execute(f"""
    SELECT COUNT(*) FROM read_parquet('{pq}')
    WHERE state = 'US'
      AND (email IS NULL OR email = '' OR email LIKE '%missing.local' OR email LIKE '%invalid.local')
      AND (phone IS NULL OR phone = '')
""").fetchone()[0]
print(f"  LOW VALUE (no real email, no phone): {low_value:,}")

has_real_email = conn.execute(f"""
    SELECT COUNT(*) FROM read_parquet('{pq}')
    WHERE state = 'US'
      AND email IS NOT NULL AND email != ''
      AND email NOT LIKE '%missing.local' AND email NOT LIKE '%invalid.local'
      AND email NOT LIKE '%example.com'
""").fetchone()[0]
print(f"  HAS REAL EMAIL (potentially useful): {has_real_email:,}")

print(f"\n  RECOMMENDATION:")
print(f"    ARCHIVE (low value, no contact): {low_value:,}")
print(f"    KEEP (has real email):           {has_real_email:,}")
print(f"    DELETE (pure junk):              {pure_junk:,}")
