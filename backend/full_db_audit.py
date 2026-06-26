#!/usr/bin/env python
"""Comprehensive Database Health Audit - TalentOpsAI"""
import sys, os, json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 70)
print("  TALENTOPS AI - FULL DATABASE HEALTH AUDIT")
print("=" * 70)

# 1. Overall Stats
print("\n[1] OVERALL DATABASE STATS")
stats = db.execute(text("""
    SELECT 
        (SELECT count(*) FROM recruiters) AS total_recruiters,
        (SELECT count(*) FROM companies) AS total_companies,
        (SELECT count(*) FROM recruiters WHERE is_active = true) AS active_recruiters,
        (SELECT count(*) FROM recruiters WHERE is_active = false) AS inactive_recruiters,
        (SELECT count(*) FROM companies WHERE is_active = true) AS active_companies
""")).mappings().one()
for k, v in stats.items():
    print(f"   {k}: {v}")

# 2. Email Quality
print("\n[2] EMAIL QUALITY BREAKDOWN")
emails = db.execute(text("""
    SELECT
        count(*) AS total,
        count(*) FILTER (WHERE email IS NULL OR email = '') AS no_email,
        count(*) FILTER (WHERE email LIKE '%@missing.local%') AS dummy_email,
        count(*) FILTER (WHERE email_status = 'invalid') AS marked_invalid,
        count(*) FILTER (WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' AND (email_status IS NULL OR email_status != 'invalid')) AS real_valid_email,
        count(*) FILTER (WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' AND email NOT LIKE '%@%.%') AS malformed_email,
        count(*) FILTER (WHERE email IS NOT NULL AND email LIKE '%@gmail.com') AS gmail,
        count(*) FILTER (WHERE email IS NOT NULL AND email LIKE '%@yahoo.com') AS yahoo,
        count(*) FILTER (WHERE email IS NOT NULL AND email LIKE '%@hotmail.com') AS hotmail,
        count(*) FILTER (WHERE email IS NOT NULL AND email LIKE '%@outlook.com') AS outlook
    FROM recruiters
""")).mappings().one()
for k, v in emails.items():
    print(f"   {k}: {v}")

# 3. Phone Quality
print("\n[3] PHONE QUALITY BREAKDOWN")
phones = db.execute(text("""
    SELECT
        count(*) AS total,
        count(*) FILTER (WHERE phone IS NULL OR phone = '') AS no_phone,
        count(*) FILTER (WHERE phone IS NOT NULL AND phone != '') AS has_phone,
        count(*) FILTER (WHERE phone IN ('000-000-0000', '0000000000', '8888888888', '9999999999')) AS fake_phone,
        count(*) FILTER (WHERE phone IS NOT NULL AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) < 10 AND phone != '') AS short_phone,
        count(*) FILTER (WHERE phone IS NOT NULL AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) > 11 AND phone != '') AS long_phone
    FROM recruiters
""")).mappings().one()
for k, v in phones.items():
    print(f"   {k}: {v}")

# 4. Duplicate Detection
print("\n[4] DUPLICATE DETECTION")
dupes = db.execute(text("""
    SELECT
        (SELECT count(*) FROM (SELECT email FROM recruiters WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' GROUP BY email HAVING count(*) > 1) t) AS duplicate_emails,
        (SELECT count(*) FROM (SELECT phone FROM recruiters WHERE phone IS NOT NULL AND phone != '' GROUP BY phone HAVING count(*) > 1) t) AS duplicate_phones,
        (SELECT count(*) FROM (SELECT recruiter_name, company_id FROM recruiters WHERE recruiter_name IS NOT NULL AND company_id IS NOT NULL GROUP BY recruiter_name, company_id HAVING count(*) > 1) t) AS duplicate_name_company
""")).mappings().one()
for k, v in dupes.items():
    print(f"   {k}: {v}")

# 5. Name Quality
print("\n[5] RECRUITER NAME QUALITY")
names = db.execute(text("""
    SELECT
        count(*) FILTER (WHERE recruiter_name IS NULL OR recruiter_name = '') AS no_name,
        count(*) FILTER (WHERE recruiter_name = 'Unknown') AS name_unknown,
        count(*) FILTER (WHERE recruiter_name LIKE '%@%') AS name_is_email,
        count(*) FILTER (WHERE recruiter_name ~ '^[A-Z][a-z]+ [A-Z][a-z]+$') AS proper_full_name,
        count(*) FILTER (WHERE recruiter_name !~ ' ' AND recruiter_name IS NOT NULL AND recruiter_name != '' AND recruiter_name != 'Unknown' AND recruiter_name NOT LIKE '%@%') AS single_word_name,
        count(*) FILTER (WHERE LENGTH(recruiter_name) < 3 AND recruiter_name IS NOT NULL) AS very_short_name
    FROM recruiters
""")).mappings().one()
for k, v in names.items():
    print(f"   {k}: {v}")

# 6. State Distribution
print("\n[6] STATE DISTRIBUTION (Top 15)")
states = db.execute(text("""
    SELECT state, count(*) AS cnt 
    FROM recruiters 
    WHERE state IS NOT NULL AND state != ''
    GROUP BY state 
    ORDER BY cnt DESC 
    LIMIT 15
""")).fetchall()
for s in states:
    print(f"   {s[0]}: {s[1]}")

# 7. Company Linkage
print("\n[7] COMPANY LINKAGE QUALITY")
linkage = db.execute(text("""
    SELECT
        count(*) FILTER (WHERE company_id IS NULL) AS no_company_link,
        count(*) FILTER (WHERE company_id IS NOT NULL) AS has_company_link,
        (SELECT count(*) FROM companies WHERE is_active = true AND company_id NOT IN (SELECT DISTINCT company_id FROM recruiters WHERE company_id IS NOT NULL)) AS orphan_companies
    FROM recruiters
""")).mappings().one()
for k, v in linkage.items():
    print(f"   {k}: {v}")

# 8. Data Freshness
print("\n[8] DATA FRESHNESS")
fresh = db.execute(text("""
    SELECT
        count(*) FILTER (WHERE last_scan_at IS NULL) AS never_scanned,
        count(*) FILTER (WHERE last_scan_at IS NOT NULL AND last_scan_at < NOW() - INTERVAL '30 days') AS stale_30d,
        count(*) FILTER (WHERE last_scan_at IS NOT NULL AND last_scan_at >= NOW() - INTERVAL '7 days') AS fresh_7d,
        count(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') AS added_last_24h,
        count(*) FILTER (WHERE needs_review = true) AS needs_review
    FROM recruiters
""")).mappings().one()
for k, v in fresh.items():
    print(f"   {k}: {v}")

# 9. Source quality
print("\n[9] SOURCE & METADATA QUALITY")
try:
    src = db.execute(text("""
        SELECT
            count(*) FILTER (WHERE source IS NOT NULL AND source != '') AS has_source,
            count(*) FILTER (WHERE source IS NULL OR source = '') AS no_source,
            count(*) FILTER (WHERE metadata_json IS NOT NULL) AS has_metadata,
            count(*) FILTER (WHERE notes IS NOT NULL AND notes != '') AS has_notes
        FROM recruiters
    """)).mappings().one()
    for k, v in src.items():
        print(f"   {k}: {v}")
except Exception as e:
    print(f"   Skipped (column missing): {e}")

# 10. Title / Role Quality
print("\n[10] TITLE / ROLE QUALITY")
try:
    titles = db.execute(text("""
        SELECT
            count(*) FILTER (WHERE title IS NOT NULL AND title != '') AS has_title,
            count(*) FILTER (WHERE title IS NULL OR title = '') AS no_title
        FROM recruiters
    """)).mappings().one()
    for k, v in titles.items():
        print(f"   {k}: {v}")
except Exception as e:
    print(f"   Skipped (column missing): {e}")

# 11. Top duplicate emails
print("\n[11] TOP DUPLICATE EMAILS (Top 10)")
dup_emails = db.execute(text("""
    SELECT email, count(*) AS cnt 
    FROM recruiters 
    WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%'
    GROUP BY email 
    HAVING count(*) > 1 
    ORDER BY cnt DESC 
    LIMIT 10
""")).fetchall()
for d in dup_emails:
    print(f"   {d[0]}: {d[1]} duplicates")

# 12. Top duplicate phones
print("\n[12] TOP DUPLICATE PHONES (Top 10)")
dup_phones = db.execute(text("""
    SELECT phone, count(*) AS cnt 
    FROM recruiters 
    WHERE phone IS NOT NULL AND phone != ''
    GROUP BY phone 
    HAVING count(*) > 1 
    ORDER BY cnt DESC 
    LIMIT 10
""")).fetchall()
for d in dup_phones:
    print(f"   {d[0]}: {d[1]} duplicates")

print("\n" + "=" * 70)
print("  AUDIT COMPLETE")
print("=" * 70)

db.close()
