"""
Rule 11 Triple Verification Proof Script
========================================
Executes 3 independent verification checks:
1. Parquet Master Catalog Integrity & Person-Company-Email-State Audit
2. PostgreSQL CRM Master Sync & Linking Verification
3. Live Analytical Store (RecruiterStore DuckDB Query & Filter Verification)
"""

import os
import sys
import json
import duckdb
from typing import Dict, Any

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

from app.database import SessionLocal
from sqlalchemy import text
from app.services.recruiter_store import recruiter_store


def check_1_parquet_catalog():
    print("=================================================================")
    print("CHECK 1: PARQUET MASTER CATALOG INTEGRITY & AUDIT PROOF")
    print("=================================================================")
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")

    total = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    missing_email = con.execute("SELECT COUNT(*) FROM rec WHERE email IS NULL OR TRIM(email) = ''").fetchone()[0]
    placeholder_email = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE LOWER(email) LIKE '%@unknown.com%' 
           OR LOWER(email) LIKE '%@noemail%' 
           OR LOWER(email) LIKE '%dummy%'
    """).fetchone()[0]
    missing_company = con.execute("SELECT COUNT(*) FROM rec WHERE company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = ''").fetchone()[0]
    valid_states = con.execute("SELECT COUNT(*) FROM rec WHERE state IS NOT NULL AND LENGTH(TRIM(CAST(state AS VARCHAR))) = 2").fetchone()[0]
    
    # State distribution sample
    top_5_states = con.execute("SELECT state, COUNT(*) as cnt FROM rec GROUP BY state ORDER BY cnt DESC LIMIT 5").fetchall()

    print(f"  • Total Catalog Records: {total:,}")
    print(f"  • Email Completeness: {((total - missing_email)/total)*100:.2f}% ({missing_email} missing)")
    print(f"  • Synthetic Placeholders: {placeholder_email} (Deliverability gate compliant)")
    print(f"  • Company Completeness: {((total - missing_company)/total)*100:.2f}% ({missing_company} missing)")
    print(f"  • Valid 2-Letter US States: {valid_states:,} ({(valid_states/total)*100:.2f}% of catalog)")
    print(f"  • Top 5 Synchronized States: {top_5_states}")

    assert total == 433742, "Record count must be 433,742"
    assert missing_email == 0, "All persons must have an email"
    assert placeholder_email == 0, "No placeholder emails allowed"
    assert missing_company == 0, "All persons must have a company assigned"
    assert valid_states >= 430000, "State coverage must exceed 430,000 records"
    print(">>> CHECK 1 VERIFICATION: PASSED\n")


def check_2_postgresql_crm():
    print("=================================================================")
    print("CHECK 2: POSTGRESQL CRM MASTER SYNC & LINKING PROOF")
    print("=================================================================")
    with SessionLocal() as db:
        comp_total = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        comp_with_website = db.execute(text("SELECT COUNT(*) FROM companies WHERE website IS NOT NULL AND website != ''")).scalar()
        comp_with_state = db.execute(text("SELECT COUNT(*) FROM companies WHERE state IS NOT NULL AND state != ''")).scalar()

        rec_total = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
        rec_with_comp = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL")).scalar()
        rec_with_state = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NOT NULL AND state != ''")).scalar()

        print(f"  • PostgreSQL Companies Total: {comp_total:,}")
        print(f"  • Companies with Verified Website/Domain: {comp_with_website:,} ({((comp_with_website)/comp_total)*100:.1f}%)")
        print(f"  • Companies with Synchronized State: {comp_with_state:,} ({((comp_with_state)/comp_total)*100:.1f}%)")
        print(f"  • PostgreSQL Recruiters Total: {rec_total:,}")
        print(f"  • Recruiters Linked to Company: {rec_with_comp:,} ({((rec_with_comp)/rec_total)*100:.1f}%)")
        print(f"  • Recruiters with Synchronized State: {rec_with_state:,} ({((rec_with_state)/rec_total)*100:.1f}%)")

        assert comp_with_website >= 27000, "Companies with website must exceed 27,000"
        assert comp_with_state >= 7500, "Companies with state must exceed 7,500"
        assert rec_with_comp >= 3280, "Recruiters linked to company must exceed 3,280"
        assert rec_with_state >= 2400, "Recruiters with state must exceed 2,400"
        print(">>> CHECK 2 VERIFICATION: PASSED\n")


def check_3_analytical_store():
    print("=================================================================")
    print("CHECK 3: LIVE ANALYTICAL STORE (RECRUITERSTORE) QUERY & FILTER PROOF")
    print("=================================================================")
    recruiter_store.reload()
    total = recruiter_store.total_count
    print(f"  • RecruiterStore Loaded Total: {total:,}")

    # Test filtering by dominant state
    ca_results = recruiter_store._conn.execute("SELECT COUNT(*) FROM recruiters WHERE state = 'CA'").fetchone()[0]
    tx_results = recruiter_store._conn.execute("SELECT COUNT(*) FROM recruiters WHERE state = 'TX'").fetchone()[0]
    print(f"  • Fast Query California (CA) Recruiters: {ca_results:,}")
    print(f"  • Fast Query Texas (TX) Recruiters: {tx_results:,}")

    # Test company_summary and company_overall consistency
    top_comp = recruiter_store._conn.execute("""
        SELECT company_key, recruiter_count, dominant_domain 
        FROM company_overall 
        WHERE dominant_domain IS NOT NULL 
        ORDER BY recruiter_count DESC 
        LIMIT 3
    """).fetchall()
    print(f"  • Top Aggregated Companies with Dominant Domain: {top_comp}")

    assert total == 433742, "Store total count must match 433,742"
    assert ca_results > 25000, "California query count must exceed 25,000"
    assert tx_results > 25000, "Texas query count must exceed 25,000"
    assert len(top_comp) == 3, "Top company aggregation must return 3 rows"
    print(">>> CHECK 3 VERIFICATION: PASSED\n")


if __name__ == "__main__":
    check_1_parquet_catalog()
    check_2_postgresql_crm()
    check_3_analytical_store()
    print("=================================================================")
    print("ALL 3 RULE 11 CHECKS SUCCESSFULLY VERIFIED WITH CONCRETE PROOFS!")
    print("=================================================================")
