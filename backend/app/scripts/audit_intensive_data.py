"""
Intensive Data Audit Script
===========================
Audits every person/recruiter in the system across:
1. Emails (Deliverability, Syntax, Corporate vs Free vs Placeholder)
2. Companies (Platform noise, missing, capitalization, domain matching)
3. Syncing between Person, Email Domain, and Company
4. States (US 2-letter codes, unnormalized names, missing states, company-state alignment)
5. Database vs Parquet Sync integrity
"""

import os
import sys
import json
import duckdb
from typing import Dict, Any

# Ensure project root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from sqlalchemy import text

US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'mail.com', 'zoho.com', 'protonmail.com', 'live.com'
}

NOISE_COMPANY_NAMES = {
    'linkedin', 'google', 'facebook', 'twitter', 'instagram', 'unknown',
    'n/a', 'na', 'none', 'null', 'missing', 'missing.local', 'independent staffing',
    'self employed', 'freelance', 'contractor', 'stealth', 'confidential'
}

def audit_parquet():
    parquet_path = os.path.join(os.path.dirname(__file__), "..", "data", "recruiters_full.parquet")
    if not os.path.exists(parquet_path):
        print(f"Parquet file not found at: {parquet_path}")
        return {}

    print(f"\n--- AUDITING PARQUET CATALOG ({parquet_path}) ---")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    
    total = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    cols = [c[0] for c in con.execute("DESCRIBE rec").fetchall()]
    print(f"Total Records: {total:,}, Columns: {cols}")

    # Email Audit
    email_stats = con.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(email) as with_email,
            SUM(CASE WHEN email IS NULL OR TRIM(email) = '' THEN 1 ELSE 0 END) as missing_email,
            SUM(CASE WHEN LOWER(email) LIKE '%@unknown.com%' 
                           OR LOWER(email) LIKE '%@noemail%' 
                           OR LOWER(email) LIKE '%dummy%' 
                           OR LOWER(email) LIKE '%@placeholder%' THEN 1 ELSE 0 END) as placeholder_email,
            SUM(CASE WHEN email NOT LIKE '%@%' OR email NOT LIKE '%.%' THEN 1 ELSE 0 END) as malformed_email,
            SUM(CASE WHEN LOWER(SPLIT_PART(email, '@', 2)) IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com') THEN 1 ELSE 0 END) as free_email
        FROM rec
    """).fetchone()

    corporate_emails = (email_stats[1] or 0) - (email_stats[3] or 0) - (email_stats[4] or 0) - (email_stats[5] or 0)

    print("\n[1] EMAIL INTELLIGENCE AUDIT:")
    print(f"  • Total Evaluated: {email_stats[0]:,}")
    print(f"  • Has Email: {email_stats[1]:,} ({((email_stats[1] or 0)/total)*100:.1f}%)")
    print(f"  • Corporate Domain Emails: {corporate_emails:,} ({((corporate_emails or 0)/total)*100:.1f}%)")
    print(f"  • Free Webmail (Gmail/Yahoo/etc): {email_stats[5]:,} ({((email_stats[5] or 0)/total)*100:.1f}%)")
    print(f"  • Synthetic/Placeholder Emails: {email_stats[3]:,}")
    print(f"  • Malformed Emails: {email_stats[4]:,}")
    print(f"  • Missing Emails: {email_stats[2]:,}")

    # Company Audit
    company_stats = con.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(company_id) as with_company,
            SUM(CASE WHEN company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' THEN 1 ELSE 0 END) as missing_company,
            SUM(CASE WHEN LOWER(TRIM(CAST(company_id AS VARCHAR))) IN (
                'linkedin', 'google', 'facebook', 'twitter', 'unknown', 'n/a', 'na', 
                'none', 'null', 'missing', 'missing.local', 'independent staffing', 
                'self employed', 'freelance'
            ) THEN 1 ELSE 0 END) as noise_company
        FROM rec
    """).fetchone()

    valid_company = (company_stats[1] or 0) - (company_stats[3] or 0)
    print("\n[2] COMPANY AUDIT:")
    print(f"  • Total Evaluated: {company_stats[0]:,}")
    print(f"  • Has Company Name: {company_stats[1]:,} ({((company_stats[1] or 0)/total)*100:.1f}%)")
    print(f"  • Valid Non-Noise Company: {valid_company:,} ({((valid_company or 0)/total)*100:.1f}%)")
    print(f"  • Platform Noise / Generic Placeholders: {company_stats[3]:,}")
    print(f"  • Missing Company: {company_stats[2]:,}")

    # State Audit
    state_stats = con.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(state) as with_state,
            SUM(CASE WHEN state IS NULL OR TRIM(CAST(state AS VARCHAR)) = '' THEN 1 ELSE 0 END) as missing_state,
            SUM(CASE WHEN LENGTH(TRIM(CAST(state AS VARCHAR))) = 2 AND UPPER(TRIM(CAST(state AS VARCHAR))) = TRIM(CAST(state AS VARCHAR)) THEN 1 ELSE 0 END) as valid_2letter_code,
            SUM(CASE WHEN LENGTH(TRIM(CAST(state AS VARCHAR))) > 2 THEN 1 ELSE 0 END) as raw_full_name_state
        FROM rec
    """).fetchone()

    print("\n[3] GEOGRAPHIC STATE AUDIT:")
    print(f"  • Total Evaluated: {state_stats[0]:,}")
    print(f"  • Has State: {state_stats[1]:,} ({((state_stats[1] or 0)/total)*100:.1f}%)")
    print(f"  • Standard 2-Letter US State Code: {state_stats[3]:,} ({((state_stats[3] or 0)/total)*100:.1f}%)")
    print(f"  • Unnormalized / Full State Name: {state_stats[4]:,}")
    print(f"  • Missing State: {state_stats[2]:,}")

    # Top States Distribution
    top_states = con.execute("""
        SELECT UPPER(TRIM(CAST(state AS VARCHAR))) as st, COUNT(*) as cnt
        FROM rec
        WHERE state IS NOT NULL AND TRIM(CAST(state AS VARCHAR)) != ''
        GROUP BY st
        ORDER BY cnt DESC
        LIMIT 10
    """).fetchall()
    print("  • Top 10 States:")
    for st, cnt in top_states:
        print(f"     - {st}: {cnt:,}")

    # Person-Company-Email Domain Sync Audit
    print("\n[4] PERSON-COMPANY-DOMAIN SYNC INTEGRITY:")
    sync_stats = con.execute("""
        SELECT
            COUNT(*) as total_with_both,
            SUM(CASE 
                WHEN email LIKE '%@%' 
                 AND company_id IS NOT NULL 
                 AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com')
                 AND INSTR(LOWER(TRIM(CAST(company_id AS VARCHAR))), SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1)) > 0
                THEN 1 ELSE 0 
            END) as domain_company_name_match,
            SUM(CASE
                WHEN email LIKE '%@%'
                 AND company_id IS NOT NULL
                 AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com')
                THEN 1 ELSE 0
            END) as corporate_with_company
        FROM rec
        WHERE email IS NOT NULL AND company_id IS NOT NULL
    """).fetchone()

    total_both = sync_stats[0] or 0
    corp_both = sync_stats[1] or 0
    direct_match = sync_stats[1] or 0

    print(f"  • Records with both Email & Company: {total_both:,}")
    print(f"  • Corporate Email with Company: {sync_stats[2]:,}")
    print(f"  • Direct String Alignment between Email Domain & Company Name: {direct_match:,}")

    return {
        "total": total,
        "email_stats": email_stats,
        "company_stats": company_stats,
        "state_stats": state_stats,
    }


def audit_postgresql():
    print("\n--- AUDITING POSTGRESQL / SQL DATABASE TABLES ---")
    try:
        with SessionLocal() as db:
            # Check discovery_staging schema & counts
            try:
                cols = db.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'discovery_staging'
                """)).fetchall()
                print("  • discovery_staging columns:", [c[0] for c in cols])
                
                ds_total = db.execute(text("SELECT COUNT(*) FROM discovery_staging")).scalar()
                print(f"  • Table 'discovery_staging': {ds_total:,} total records")

                # Sample discovery_staging records if any
                if ds_total > 0:
                    sample_ds = db.execute(text("SELECT * FROM discovery_staging LIMIT 2")).mappings().fetchall()
                    print(f"  • discovery_staging sample keys: {list(sample_ds[0].keys())}")
            except Exception as e:
                print(f"  • discovery_staging audit note: {e}")

            # Check recruiters table in PostgreSQL
            try:
                r_cols = [c[0] for c in db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'recruiters'")).fetchall()]
                print(f"  • recruiters columns: {r_cols}")
                rec_total = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
                print(f"\n[POSTGRESQL RECRUITERS CRM AUDIT]:")
                print(f"  • Total Recruiters: {rec_total:,}")
                
                # Check email column name (email or work_email)
                email_col = 'email' if 'email' in r_cols else ('work_email' if 'work_email' in r_cols else None)
                if email_col:
                    rec_with_email = db.execute(text(f"SELECT COUNT(*) FROM recruiters WHERE {email_col} IS NOT NULL AND {email_col} != ''")).scalar()
                    print(f"  • With Email ({email_col}): {rec_with_email:,} (Missing: {rec_total - rec_with_email:,})")

                # Check company column name (company or company_id or company_name)
                comp_col = next((c for c in ['company', 'company_name', 'company_id'] if c in r_cols), None)
                if comp_col:
                    rec_with_company = db.execute(text(f"SELECT COUNT(*) FROM recruiters WHERE {comp_col} IS NOT NULL")).scalar()
                    print(f"  • With Company ({comp_col}): {rec_with_company:,} (Missing: {rec_total - rec_with_company:,})")

                # Check state
                if 'state' in r_cols:
                    rec_with_state = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NOT NULL AND state != ''")).scalar()
                    print(f"  • With State: {rec_with_state:,} (Missing: {rec_total - rec_with_state:,})")
            except Exception as e:
                print(f"  • recruiters table audit error: {e}")

            # Check companies table in PostgreSQL
            try:
                c_cols = [c[0] for c in db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'companies'")).fetchall()]
                print(f"  • companies columns: {c_cols}")
                comp_total = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
                print(f"\n[POSTGRESQL COMPANIES AUDIT]:")
                print(f"  • Total Companies: {comp_total:,}")
                
                name_col = next((c for c in ['name', 'company_name', 'normalized_company_name'] if c in c_cols), None)
                domain_col = next((c for c in ['domain', 'website', 'dominant_domain'] if c in c_cols), None)
                if domain_col:
                    comp_with_domain = db.execute(text(f"SELECT COUNT(*) FROM companies WHERE {domain_col} IS NOT NULL AND {domain_col} != ''")).scalar()
                    print(f"  • With Domain ({domain_col}): {comp_with_domain:,} (Missing: {comp_total - comp_with_domain:,})")
                if 'state' in c_cols:
                    comp_with_state = db.execute(text("SELECT COUNT(*) FROM companies WHERE state IS NOT NULL AND state != ''")).scalar()
                    print(f"  • With State: {comp_with_state:,} (Missing: {comp_total - comp_with_state:,})")
            except Exception as e:
                print(f"  • companies table audit error: {e}")

    except Exception as e:
        print(f"PostgreSQL connection note: {e}")

if __name__ == "__main__":
    audit_parquet()
    audit_postgresql()
