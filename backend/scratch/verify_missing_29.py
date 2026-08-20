import os
import re
import json
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("c:/TalentOpsAI/backend/.env")

MISSING_29 = [
    (12, "Geeks on Site"),
    (16, "ETHOS - Talent & Advisory"),
    (25, "ContractStaffingRecruiters.com"),
    (28, "BTerminal Systems"),
    (43, "Linksap Europe Ltd"),
    (45, "Apogee Global RMS"),
    (47, "DCI Resources, LLC - Pending 8(a) Certified Company"),
    (50, "PM Solutions / PM College"),
    (52, "DBI Staffing"),
    (53, "Rylex"),
    (59, "OCT Consulting LLC"),
    (60, "Tech 20 Solutions, Inc"),
    (61, "Covenant HR"),
    (63, "cloudteam.com"),
    (64, "Cleartech Recruiting"),
    (66, "E Quality Corporation"),
    (68, "SAFTech Software Solutions"),
    (72, "Makai Labs"),
    (80, "Prospectus IT Recruitment"),
    (81, "Outlier Mentors"),
    (84, "SOLTECHPR"),
    (92, "Innovatus Technology Consulting"),
    (96, "ProspHire"),
    (98, "People4Net Inc"),
    (99, "Interactive Resources - iR"),
    (100, "ASAP Talent Services, a VMG Company"),
    (103, "Object Data Inc"),
    (105, "Full Cycle Services"),
    (109, "XMS Solutions, Inc.")
]

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    df_pg = pd.read_sql("SELECT company_id, company_name, normalized_company_name, canonical_name, primary_domain, website FROM companies", conn)

parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
con = duckdb.connect()

print(f"Loaded {len(df_pg)} companies from PG.")

for idx, comp in MISSING_29:
    # Try keywords and token splits
    tokens = [t for t in re.split(r'[^a-zA-Z0-9]', comp.lower()) if t and t not in ['inc', 'llc', 'corp', 'ltd', 'company', 'services', 'solutions', 'consulting', 'group', 'the', 'com']]
    
    matches_pg = []
    for _, row in df_pg.iterrows():
        cname = str(row['company_name']).lower()
        cdom = str(row['primary_domain']).lower()
        cweb = str(row['website']).lower()
        
        # Check tokens
        for tok in tokens:
            if len(tok) >= 4 and (tok in cname or tok in cdom or tok in cweb):
                matches_pg.append((row['company_name'], row['primary_domain']))
                break
                
    # Also check duckdb parquet directly on email domains
    recruiter_matches = []
    for tok in tokens:
        if len(tok) >= 4:
            df_recs = con.execute(f"""
                SELECT recruiter_name, email, title 
                FROM '{parquet_path}' 
                WHERE email LIKE '%{tok}%' OR recruiter_name LIKE '%{tok}%'
                LIMIT 5
            """).df()
            if len(df_recs) > 0:
                for _, r in df_recs.iterrows():
                    if f"@{tok}" in str(r['email']).lower() or f"{tok}." in str(r['email']).lower():
                        recruiter_matches.append((r['recruiter_name'], r['email'], r['title']))
                        
    print(f"\n[{idx:3d}] Query: {comp} | Tokens: {tokens}")
    if matches_pg:
        print(f"   PG Candidate Matches: {matches_pg[:3]}")
    if recruiter_matches:
        print(f"   Parquet Email Domain Matches: {recruiter_matches[:2]}")
    if not matches_pg and not recruiter_matches:
        print("   -> DEFINITELY NOT IN DATA (Clean New Lead)")
