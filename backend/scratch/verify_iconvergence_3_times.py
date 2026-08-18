import sys
import os
import duckdb

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.services.recruiter_store import recruiter_store, PARQUET_FILE

EXPECTED_EMAILS = [
    "matthewg@iconvergence.com", "michael@iconvergence.com", "ramsha@iconvergence.com",
    "brandon@iconvergence.com", "indira@iconvergence.com", "scott@iconvergence.com",
    "scotty@iconvergence.com", "pankaj@iconvergence.com", "chris@iconvergence.com",
    "courtney@iconvergence.com", "kathy@iconvergence.com", "connor@iconvergence.com",
    "jonathon@iconvergence.com", "sc@iconvergence.com", "rachel@iconvergence.com",
    "wesley@iconvergence.com", "ashley@iconvergence.com", "brock@iconvergence.com",
    "adam@iconvergence.com", "douglas@iconvergence.com", "richard@iconvergence.com",
    "amanda@iconvergence.com", "john@iconvergence.com", "chama@iconvergence.com",
    "jason@iconvergence.com", "toby@iconvergence.com", "matt@iconvergence.com",
    "mike@iconvergence.com", "brannon@iconvergence.com", "beau@iconvergence.com",
    "chad@iconvergence.com", "houda@iconvergence.com"
]

def run_3_pass_iconvergence_audit():
    print("=" * 80)
    print("CHECK 3 TIMES RULE: FORENSIC VERIFICATION OF iConvergence ROSTER")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # CHECK 1: POSTGRESQL DATABASE VERIFICATION
    # --------------------------------------------------------------------------
    print("\n[CHECK 1/3] POSTGRESQL DATABASE AUDIT...")
    db = SessionLocal()
    comp = db.query(Company).filter(Company.company_name.ilike("%iconvergence%")).first()
    assert comp is not None, "Company iConvergence not found in PostgreSQL"
    print(f"      Company Found: ID={comp.company_id}, Name='{comp.company_name}', Domain='{comp.primary_domain}', Website='{comp.website}'")

    pg_recs = db.query(Recruiter).filter(Recruiter.email.in_(EXPECTED_EMAILS)).all()
    print(f"      Matched Contacts in PostgreSQL: {len(pg_recs)} / {len(EXPECTED_EMAILS)}")
    for r in pg_recs[:5]:
        print(f"        - ID: {r.recruiter_id} | {r.recruiter_name} | {r.email} | {r.title}")
    
    assert len(pg_recs) == len(EXPECTED_EMAILS), f"Expected 32 records in Postgres, found {len(pg_recs)}"
    db.close()
    print("      -> CHECK 1 PASSED (32/32 records verified in PostgreSQL database)")

    # --------------------------------------------------------------------------
    # CHECK 2: PARQUET COLUMNAR DATASET VERIFICATION
    # --------------------------------------------------------------------------
    print("\n[CHECK 2/3] DUCKDB PARQUET DATASET FORENSIC AUDIT...")
    con = duckdb.connect()
    pq_clean = PARQUET_FILE.replace(os.sep, '/')
    
    query = f"""
    SELECT recruiter_id, recruiter_name, email, specialization, company_id, location, state, completeness_score
    FROM read_parquet('{pq_clean}')
    WHERE LOWER(email) IN ({', '.join([repr(e) for e in EXPECTED_EMAILS])})
    ORDER BY recruiter_id ASC
    """
    df = con.execute(query).fetchdf()
    con.close()
    
    print(f"      Matched Requested Roster Contacts in Parquet: {len(df)} / {len(EXPECTED_EMAILS)}")
    print(df[['recruiter_id', 'recruiter_name', 'email', 'specialization', 'state']].head(8).to_string())
    
    assert len(df) == len(EXPECTED_EMAILS), f"Expected {len(EXPECTED_EMAILS)} records in Parquet, found {len(df)}"
    print("      -> CHECK 2 PASSED (32/32 requested roster records verified in Parquet columnar storage)")

    # --------------------------------------------------------------------------
    # CHECK 3: LIVE RECRUITER STORE SEARCH & DISCOVERY VERIFICATION
    # --------------------------------------------------------------------------
    print("\n[CHECK 3/3] UNIFIED RECRUITER STORE SEARCH ENGINE AUDIT...")
    recruiter_store._ensure_loaded()
    
    # Query recruiter store
    res_list = recruiter_store.search(q="iconvergence.com", limit=100)
    print(f"      Search Query 'iconvergence.com' Results Count: {len(res_list)}")
    
    found_emails = {r.get('email') for r in res_list if r.get('email')}
    matched_target = set(EXPECTED_EMAILS).intersection(found_emails)
    missing_in_search = set(EXPECTED_EMAILS) - found_emails
    print(f"      Found Target Emails in RecruiterStore Search: {len(matched_target)} / {len(EXPECTED_EMAILS)}")
    if missing_in_search:
        print(f"      Missing from search: {missing_in_search}")
        
    assert len(matched_target) == len(EXPECTED_EMAILS), f"Search engine missing target records: {missing_in_search}"
    print("      -> CHECK 3 PASSED (100% of iConvergence roster indexed and discoverable in live search)")

    print("\n" + "=" * 80)
    print("ALL 3 CHECKS COMPLETED WITH 100% SUCCESSFUL EMPIRICAL PROOF!")
    print("=" * 80)

if __name__ == "__main__":
    run_3_pass_iconvergence_audit()
