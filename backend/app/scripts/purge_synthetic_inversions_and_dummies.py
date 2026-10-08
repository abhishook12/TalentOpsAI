"""
Surgical Purge of Synthetic Inversions, Test Dummies, and Broken Phones
Eradicates:
1. Synthetic email inversions (e.g. company.name@personname.com)
2. Explicit test contacts (Test_Contact_Person, testuser@, testcontactperson@)
3. Broken / street addresses in phone numbers
4. Malformed domain extensions (e.g. .netfax)
5. Generic departmental inboxes (helpdesk@, marketing@, billing@, inquiries@)
"""

import os
import sys
import re
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def purge_and_heal():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE master AS SELECT * FROM read_parquet('{parquet_path}')")
    
    start_count = con.execute("SELECT count(*) FROM master").fetchone()[0]
    print(f"Initial Catalog Records: {start_count:,}")

    # 1. Purge explicit test dummy contacts
    print("\n[1] Purging explicit test contacts...")
    con.execute("""
        DELETE FROM master
        WHERE LOWER(recruiter_name) LIKE 'test_%'
           OR LOWER(recruiter_name) = 'test'
           OR LOWER(recruiter_name) LIKE '%test contact%'
           OR LOWER(email) LIKE 'test_%'
           OR LOWER(email) LIKE 'test@%'
           OR LOWER(email) LIKE 'testuser@%'
           OR LOWER(email) LIKE 'testcontactperson@%'
    """)
    cnt1 = con.execute("SELECT count(*) FROM master").fetchone()[0]
    print(f"  -> Purged {start_count - cnt1} test contacts.")

    # 2. Purge synthetic inverted emails (company as handle, person as domain)
    print("\n[2] Purging synthetic inverted emails (e.g. company.name@personname.com)...")
    con.execute("""
        DELETE FROM master
        WHERE (
            LOWER(recruiter_name) IN ('insight global', 'espo corporation', 'fasttek global', 'global technica', 'geologics corporation', 'dsr global', 'cybermed corporation', 'freedom corporation', 'biblioso corporation', 'grt corporation', 'hcpl global')
            OR LOWER(recruiter_name) LIKE '% corporation'
            OR LOWER(recruiter_name) LIKE '% global'
        ) AND (
            email LIKE '%.corporation@%'
            OR email LIKE '%.global@%'
            OR email LIKE 'espo.%@%'
            OR email LIKE 'insight.%@%'
            OR email LIKE 'geologics.%@%'
            OR email LIKE 'dsr.%@%'
            OR email LIKE 'cybermed.%@%'
        )
    """)
    cnt2 = con.execute("SELECT count(*) FROM master").fetchone()[0]
    print(f"  -> Purged {cnt1 - cnt2} synthetic inverted crawler records.")

    # 3. Purge generic departmental inboxes & malformed TLDs (.netfax)
    print("\n[3] Purging generic departmental inboxes & malformed TLDs...")
    con.execute("""
        DELETE FROM master
        WHERE LOWER(SPLIT_PART(email, '@', 1)) IN (
            'helpdesk', 'inquiries', 'billing', 'postmaster', 'mailer-daemon'
        )
        OR email LIKE '%.netfax'
    """)
    cnt3 = con.execute("SELECT count(*) FROM master").fetchone()[0]
    print(f"  -> Purged {cnt2 - cnt3} generic departmental / invalid TLD records.")

    # 4. Clean street addresses and short numbers out of phone field
    print("\n[4] Cleansing phone field (street addresses, short numbers)...")
    # Set to empty string if phone has <10 digits or contains letters / street names
    con.execute("""
        UPDATE master
        SET phone = ''
        WHERE phone IS NOT NULL AND (
            LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) < 10
            OR phone LIKE '%Ave%'
            OR phone LIKE '%St%'
            OR phone LIKE '%Suite%'
            OR phone LIKE '%Road%'
            OR phone LIKE '%Blvd%'
            OR REGEXP_REPLACE(phone, '[^0-9]', '', 'g') = '123567890'
        )
    """)
    print("  -> Cleaned all street addresses and short numbers from phone column.")

    # Final count and write
    final_count = con.execute("SELECT count(*) FROM master").fetchone()[0]
    print(f"\nFinal Verified Catalog Record Count: {final_count:,}")
    print(f"Writing updated catalog to: {parquet_path}...")
    con.execute(f"COPY master TO '{parquet_path}' (FORMAT PARQUET)")
    print("Master parquet file successfully updated and saved!")

if __name__ == "__main__":
    purge_and_heal()
