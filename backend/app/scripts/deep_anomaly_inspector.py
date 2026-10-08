"""
Deep Anomaly Inspector
Dives into:
1. Synthetic / Concatenated domains (e.g. *linkedincom*, multiple .com in domain)
2. Postmaster / Admin / Mailer-daemon addresses
3. Names that are exact company names vs their emails
4. Names that are job titles vs their emails
5. Email aliases (+number) in person names
6. Stripping tracking query params from LinkedIn URLs
7. Resolving 131,531 'US' states from company state consensus!
"""

import os
import sys
import duckdb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

def inspect():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    
    print("="*80)
    print("DEEP ANOMALY INVESTIGATION")
    print("="*80)

    # 1. Concatenated or Bogus Domains
    print("\n[1] BOGUS / CONCATENATED DOMAINS IN EMAILS:")
    bogus_domains = con.execute("""
        SELECT recruiter_name, email, company_id, linkedin FROM rec
        WHERE email LIKE '%linkedincom%'
           OR email LIKE '%https%'
           OR email LIKE '%http%'
           OR email LIKE '%www%'
           OR email LIKE '%@%.%.%.%.%'
    """).fetchall()
    print(f"  Found {len(bogus_domains)} records with bogus/URL domains in email:")
    for b in bogus_domains[:10]:
        print(f"    Name: {b[0]} | Email: {b[1]} | Company: {b[2]} | LI: {b[3]}")

    # 2. Postmaster / System addresses
    print("\n[2] POSTMASTER & SYSTEM INBOXES:")
    postmasters = con.execute("""
        SELECT recruiter_name, email, company_id FROM rec
        WHERE LOWER(email) LIKE 'postmaster@%'
           OR LOWER(email) LIKE 'mailer-daemon@%'
           OR LOWER(email) LIKE 'admin@%'
           OR LOWER(email) LIKE 'administrator@%'
           OR LOWER(email) LIKE 'root@%'
           OR LOWER(email) LIKE 'webmaster@%'
           OR LOWER(recruiter_name) LIKE '%postmaster%'
           OR LOWER(recruiter_name) LIKE '%mimecast%'
    """).fetchall()
    print(f"  Found {len(postmasters)} postmaster / system inboxes:")
    for p in postmasters[:10]:
        print(f"    Name: {p[0]} | Email: {p[1]} | Company: {p[2]}")

    # 3. Company names in recruiter_name
    print("\n[3] COMPANY NAMES AS RECRUITER NAME:")
    comp_as_names = con.execute("""
        SELECT recruiter_name, email, company_id FROM rec
        WHERE LOWER(recruiter_name) LIKE '% corporation'
           OR LOWER(recruiter_name) LIKE '% corp'
           OR LOWER(recruiter_name) LIKE '% inc'
           OR LOWER(recruiter_name) LIKE '% llc'
           OR LOWER(recruiter_name) LIKE '% limited'
           OR LOWER(recruiter_name) LIKE '% ltd'
           OR LOWER(recruiter_name) LIKE '% global'
           OR LOWER(recruiter_name) LIKE '% technologies'
           OR LOWER(recruiter_name) LIKE '% consulting'
           OR LOWER(recruiter_name) LIKE '% solutions'
    """).fetchall()
    print(f"  Found {len(comp_as_names)} records where person name has company suffixes:")
    for c in comp_as_names[:10]:
        print(f"    Name: {c[0]} | Email: {c[1]} | Company: {c[2]}")

    # 4. Job titles in recruiter_name
    print("\n[4] JOB TITLES AS RECRUITER NAME:")
    titles_as_names = con.execute("""
        SELECT recruiter_name, title, email FROM rec
        WHERE LOWER(recruiter_name) IN (
            'recruiter', 'technical recruiter', 'recruitment consultant',
            'senior vice president', 'vice president', 'talent acquisition',
            'recruitment specialist', 'lead recruiter', 'program coordinator',
            'sourcing specialist', 'recruiting coordinator', 'executive recruiter'
        )
    """).fetchall()
    print(f"  Found {len(titles_as_names)} records where person name is an exact job title:")
    for t in titles_as_names[:10]:
        print(f"    Name: {t[0]} | Title: {t[1]} | Email: {t[2]}")

    # 5. Turnberry / Alias +Number names
    print("\n[5] ALIAS WITH PLUS-SIGN IN RECRUITER NAME:")
    alias_names = con.execute("""
        SELECT recruiter_name, email, company_id FROM rec
        WHERE recruiter_name LIKE '%+%'
    """).fetchall()
    print(f"  Found {len(alias_names)} records with '+' in person name:")
    for a in alias_names[:10]:
        print(f"    Name: {a[0]} | Email: {a[1]} | Company: {a[2]}")

    # 6. Test records / dummy contacts
    print("\n[6] TEST / DUMMY CONTACTS:")
    test_contacts = con.execute("""
        SELECT recruiter_name, email, phone, company_id FROM rec
        WHERE LOWER(recruiter_name) LIKE '%test%'
           OR LOWER(email) LIKE '%test%'
           OR LOWER(company_id) LIKE '%test%'
    """).fetchall()
    print(f"  Found {len(test_contacts)} test/dummy contacts:")
    for tc in test_contacts[:10]:
        print(f"    Name: {tc[0]} | Email: {tc[1]} | Phone: {tc[2]} | Company: {tc[3]}")

    # 7. State resolution opportunity:
    print("\n[7] COMPANY STATE CONSENSUS FOR 'US' RECORDS:")
    # Check how many of the 131,531 'US' records belong to a company that has a known specific state from other recruiters or company table
    consensus_res = con.execute("""
        WITH known_states AS (
            SELECT company_id, state, count(*) as cnt
            FROM rec
            WHERE state IS NOT NULL AND state != 'US' AND LENGTH(TRIM(state)) = 2
            GROUP BY company_id, state
        ),
        best_state AS (
            SELECT company_id, state, cnt,
                   ROW_NUMBER() OVER(PARTITION BY company_id ORDER BY cnt DESC) as rk
            FROM known_states
        )
        SELECT count(*)
        FROM rec r
        JOIN best_state b ON r.company_id = b.company_id AND b.rk = 1
        WHERE r.state = 'US'
    """).fetchone()[0]
    print(f"  Out of 131,531 'US' records, {consensus_res:,} can be resolved to specific US States via company colleague consensus!")

if __name__ == "__main__":
    inspect()
