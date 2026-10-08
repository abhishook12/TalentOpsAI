"""
Detailed Inversion & Generic Inbox Auditor & Purger
"""

import os
import sys
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def run():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")

    print("=" * 80)
    print("CHECKING CRAWLER INVERSIONS, ROLE INBOXES & TEST CONTACTS")
    print("=" * 80)

    # 1. Inverted records where company is in name and email domain is a person's name
    inversions = con.execute("""
        SELECT recruiter_name, email, company_id FROM rec
        WHERE (
            LOWER(recruiter_name) IN ('insight global', 'espo corporation', 'fasttek global', 'global technica', 'make corporation', 'sutherland global')
            OR LOWER(recruiter_name) LIKE '% corporation'
            OR LOWER(recruiter_name) LIKE '% global'
        ) AND (
            email LIKE '%.%@%'
            OR email LIKE '%optomi.com%'
            OR company_id LIKE '% %'
        )
    """).fetchall()
    print(f"Inverted records found: {len(inversions)}")
    for inv in inversions[:15]:
        print("  ", inv)

    # 2. Generic inboxes
    role_inboxes = con.execute("""
        SELECT recruiter_name, email, company_id FROM rec
        WHERE LOWER(SPLIT_PART(email, '@', 1)) IN (
            'helpdesk', 'inquiries', 'marketing', 'career', 'careers',
            'info', 'sales', 'support', 'contact', 'billing', 'press',
            'media', 'general', 'mail', 'office', 'team'
        )
    """).fetchall()
    print(f"\nGeneric departmental inboxes found: {len(role_inboxes)}")
    for ri in role_inboxes[:15]:
        print("  ", ri)

    # 3. Test contacts
    test_rows = con.execute("""
        SELECT recruiter_name, email, phone, company_id FROM rec
        WHERE LOWER(recruiter_name) LIKE 'test_%'
           OR LOWER(recruiter_name) = 'test'
           OR LOWER(recruiter_name) LIKE '%test contact%'
           OR LOWER(email) LIKE 'test_%'
           OR LOWER(email) LIKE 'test@%'
    """).fetchall()
    print(f"\nExplicit Test contacts found: {len(test_rows)}")
    for tr in test_rows:
        print("  ", tr)

    # 4. Short / Broken phones
    short_phones = con.execute("""
        SELECT phone, recruiter_name, email FROM rec
        WHERE phone IS NOT NULL 
          AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) > 0
          AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) < 10
    """).fetchall()
    print(f"\nBroken / Short phones found: {len(short_phones)}")
    for sp in short_phones:
        print("  ", sp)

if __name__ == "__main__":
    run()
