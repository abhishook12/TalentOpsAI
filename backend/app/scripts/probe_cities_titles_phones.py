"""
Probing Cities, Titles, Phones, and Staging Database
"""

import os
import sys
import duckdb

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

from app.database import SessionLocal
from sqlalchemy import text

def probe_more():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")

    print("="*80)
    print("PROBING CITIES, TITLES, PHONES & POSTGRESQL TABLES")
    print("="*80)

    # 1. Cities
    print("\n[1] CITY ANOMALIES:")
    num_cities = con.execute("SELECT normalized_city, count(*) FROM rec WHERE normalized_city IS NOT NULL AND REGEXP_MATCHES(normalized_city, '[0-9]') GROUP BY normalized_city LIMIT 10").fetchall()
    print(f"  Cities with digits: {len(num_cities)}")
    for nc in num_cities:
        print(f"    {nc}")

    comma_cities = con.execute("SELECT normalized_city, state, count(*) FROM rec WHERE normalized_city IS NOT NULL AND normalized_city LIKE '%,%' GROUP BY normalized_city, state LIMIT 10").fetchall()
    print(f"  Cities with commas: {len(comma_cities)}")
    for cc in comma_cities:
        print(f"    {cc}")

    # 2. Titles
    print("\n[2] TITLE ANOMALIES:")
    weird_titles = con.execute("""
        SELECT title, count(*) FROM rec 
        WHERE title IS NOT NULL AND (
            title LIKE '%http%'
            OR title LIKE '%.com%'
            OR title LIKE '%@%'
            OR title LIKE '%/%/%%'
            OR title LIKE '%--%'
            OR title LIKE '%?%'
        )
        GROUP BY title ORDER BY count(*) DESC LIMIT 15
    """).fetchall()
    print(f"  Titles with URLs, emails, or weird symbols: {len(weird_titles)}")
    for wt in weird_titles:
        print(f"    {wt}")

    # 3. Short Titles
    short_titles = con.execute("SELECT title, count(*) FROM rec WHERE title IS NOT NULL AND LENGTH(TRIM(title)) <= 2 GROUP BY title LIMIT 10").fetchall()
    print(f"  Titles with length <= 2: {short_titles}")

    # 4. PostgreSQL CRM Table Audit
    print("\n[3] POSTGRESQL CRM TABLES AUDIT:")
    db = SessionLocal()
    try:
        # Check discovery_staging
        stg_count = db.execute(text("SELECT count(*) FROM discovery_staging")).scalar()
        print(f"  discovery_staging rows: {stg_count}")
        stg_bad_email = db.execute(text("SELECT count(*) FROM discovery_staging WHERE raw_email IS NULL OR raw_email NOT LIKE '%@%.%'")).scalar()
        stg_noise = db.execute(text("SELECT count(*) FROM discovery_staging WHERE entity_type = 'NOISE' OR raw_name ILIKE '%linkedin%' OR raw_company ILIKE '%linkedin%'")).scalar()
        print(f"  discovery_staging missing/non-standard raw_email: {stg_bad_email}")
        print(f"  discovery_staging noise / platform records: {stg_noise}")

        # Check companies table
        comp_count = db.execute(text("SELECT count(*) FROM companies")).scalar()
        comp_no_domain = db.execute(text("SELECT count(*) FROM companies WHERE domain IS NULL OR domain = ''")).scalar()
        comp_no_state = db.execute(text("SELECT count(*) FROM companies WHERE state IS NULL OR state = ''")).scalar()
        print(f"  companies count: {comp_count} (missing domain: {comp_no_domain}, missing state: {comp_no_state})")

        # Check recruiters table
        rec_count = db.execute(text("SELECT count(*) FROM recruiters")).scalar()
        rec_no_comp = db.execute(text("SELECT count(*) FROM recruiters WHERE company_id IS NULL")).scalar()
        rec_no_state = db.execute(text("SELECT count(*) FROM recruiters WHERE state IS NULL OR state = ''")).scalar()
        print(f"  recruiters count: {rec_count} (unlinked to company: {rec_no_comp}, missing state: {rec_no_state})")
    finally:
        db.close()

if __name__ == "__main__":
    probe_more()
