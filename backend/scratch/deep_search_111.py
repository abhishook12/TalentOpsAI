import os
import re
import json
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("c:/TalentOpsAI/backend/.env")

COMPANIES_LIST = [
    "Rabun Enterprise Solutions",
    "ACS Professional Staffing",
    "Adastra",
    "Global Path Resources, Inc.",
    "The Bolton Group",
    "SilverSearch, Inc",
    "Bull City Talent Group",
    "The Doyle Group",
    "Incendia Partners",
    "Talution Group",
    "Albano Systems, Inc.",
    "Geeks on Site",
    "Marchon Partners",
    "Valiant Harbor International, LLC",
    "BravoTECH",
    "ETHOS - Talent & Advisory",
    "Reperio Human Capital",
    "Resourceful",
    "Catapult Federal Services",
    "IT Staffing, Inc",
    "Alleare Consulting, LLC",
    "The Structures Company, LLC",
    "Hire Hangar Global",
    "Blue Star Partners",
    "ContractStaffingRecruiters.com",
    "Crossfire Consulting",
    "Premier Resources Group (PRG)",
    "BTerminal Systems",
    "EDGE Services, Inc",
    "Marathon TS",
    "Applied Resource Group",
    "Marketeq Talent",
    "CorSource",
    "The Brixton Group",
    "SoloPoint Solutions",
    "C&G Consulting Services, Inc",
    "ERP Recruiting, LLC",
    "Entegee",
    "Gruntwork",
    "EVONA",
    "Lunova Group",
    "FuseGlobal",
    "Linksap Europe Ltd",
    "Acceler8 Talent",
    "Apogee Global RMS",
    "WorkGenius Group",
    "DCI Resources, LLC - Pending 8(a) Certified Company",
    "Mainz Brady Group",
    "e&e IT Consulting Services, Inc.",
    "PM Solutions / PM College",
    "Turnberry Solutions",
    "DBI Staffing",
    "Rylex",
    "ConsultUSA",
    "Patriot Technical Consulting",
    "Red Oak Technologies",
    "Blackstone Talent Group",
    "Adaptive Solutions Group",
    "OCT Consulting LLC",
    "Tech 20 Solutions, Inc",
    "Covenant HR",
    "Stockell Consulting",
    "cloudteam.com",
    "Cleartech Recruiting",
    "The Norland Group",
    "E Quality Corporation",
    "Staff Perm",
    "SAFTech Software Solutions",
    "PSR Associates, Inc.",
    "Harvest Technical Services, Inc.",
    "Access Data Consulting Corporation",
    "Makai Labs",
    "Prominent",
    "iSphere",
    "hackajob",
    "IFIT Solutions",
    "Delphi-US, LLC",
    "IntePros",
    "Smith Arnold Partners",
    "Prospectus IT Recruitment",
    "Outlier Mentors",
    "Swoon",
    "Career Developers, Inc.",
    "SOLTECHPR",
    "Technical-Link N. America",
    "Alderson Loop",
    "TJ Consulting Group",
    "IDR, Inc.",
    "The Hiring Group",
    "TrustNet Technologies",
    "Workforce Connections",
    "Innovatus Technology Consulting",
    "Magee Resource Group",
    "The E Group.",
    "Motivf",
    "ProspHire",
    "MeeBoss",
    "People4Net Inc",
    "Interactive Resources - iR",
    "ASAP Talent Services, a VMG Company",
    "Technical Source",
    "UpRecruit",
    "Object Data Inc",
    "ClearBridge Technology Group",
    "Full Cycle Services",
    "Apera",
    "Iceberg",
    "Hollstadt Consulting",
    "XMS Solutions, Inc.",
    "Spyglass Partners, LLC",
    "Patriot Talent Solutions"
]

def clean_company_name(name: str) -> str:
    if not name:
        return ""
    s = name.lower()
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r'\b(inc|incorporated|llc|corp|corporation|ltd|limited|group|services|solutions|consulting|partners|technologies|talent|staffing|systems|company|co|the|international|enterprise|resources|technical|associates|global)\b', '', s)
    s = re.sub(r'[^a-z0-9]', '', s)
    return s.strip()

def normalize_domain_from_name(name: str) -> str:
    s = re.sub(r'\b(inc|incorporated|llc|corp|corporation|ltd|limited|company|co)\b', '', name.lower())
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

def run_deep_search():
    print("="*80)
    print("STARTING DEEP SCAN FOR 111 COMPANIES")
    print("="*80)
    
    db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(db_url)
    
    # 1. Load all companies from Postgres
    print("Fetching companies from PostgreSQL...")
    with engine.connect() as conn:
        df_pg_companies = pd.read_sql(
            "SELECT company_id, company_name, normalized_company_name, canonical_name, primary_domain, website, location, state, industry FROM companies", 
            conn
        )
    print(f"Loaded {len(df_pg_companies)} companies from Postgres.")
    df_pg_companies['clean_name'] = df_pg_companies['company_name'].apply(clean_company_name)
    df_pg_companies['clean_norm'] = df_pg_companies['normalized_company_name'].fillna('').apply(clean_company_name)
    df_pg_companies['clean_canonical'] = df_pg_companies['canonical_name'].fillna('').apply(clean_company_name)
    
    # 2. Check local_storage_import.parquet
    local_parquet_path = "c:/TalentOpsAI/local_storage_import.parquet"
    df_local = pd.DataFrame()
    if os.path.exists(local_parquet_path):
        con = duckdb.connect()
        df_local = con.execute(f"SELECT * FROM '{local_parquet_path}' WHERE company IS NOT NULL").df()
        df_local['clean_company'] = df_local['company'].apply(clean_company_name)
        print(f"Loaded {len(df_local)} rows from local_storage_import.parquet")
        
    # 3. Check Parquet Recruiters with DuckDB
    parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
    if not os.path.exists(parquet_path):
        parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full.parquet"
    
    con = duckdb.connect()
    print(f"Connecting to DuckDB with parquet: {parquet_path}")
    
    results = []
    
    for idx, raw_query in enumerate(COMPANIES_LIST, 1):
        clean_q = clean_company_name(raw_query)
        dom_q = normalize_domain_from_name(raw_query)
        lower_q = raw_query.lower().strip()
        
        # Match in Postgres companies
        # Conditions:
        # a) Exact lower match
        # b) Clean string match
        # c) Domain contains
        # d) Substring match if clean string is >= 4 chars
        
        matched_companies = df_pg_companies[
            (df_pg_companies['company_name'].str.lower() == lower_q) |
            (df_pg_companies['normalized_company_name'].str.lower() == lower_q) |
            (df_pg_companies['canonical_name'].str.lower() == lower_q)
        ]
        
        if len(matched_companies) == 0 and clean_q:
            matched_companies = df_pg_companies[
                (df_pg_companies['clean_name'] == clean_q) |
                (df_pg_companies['clean_norm'] == clean_q) |
                (df_pg_companies['clean_canonical'] == clean_q)
            ]
            
        if len(matched_companies) == 0 and len(clean_q) >= 4:
            matched_companies = df_pg_companies[
                (df_pg_companies['clean_name'].str.contains(clean_q, regex=False)) |
                (df_pg_companies['clean_canonical'].str.contains(clean_q, regex=False)) |
                (df_pg_companies['primary_domain'].fillna('').str.contains(clean_q, regex=False))
            ]
            
        # Match in local_storage_import.parquet
        matched_local = pd.DataFrame()
        if len(df_local) > 0:
            matched_local = df_local[
                (df_local['company'].str.lower() == lower_q) |
                (df_local['clean_company'] == clean_q)
            ]
            if len(matched_local) == 0 and len(clean_q) >= 4:
                matched_local = df_local[df_local['clean_company'].str.contains(clean_q, regex=False)]
                
        # If we have matched companies from PG, fetch recruiters count from DuckDB parquet or Postgres
        company_ids = matched_companies['company_id'].dropna().astype(str).tolist() if len(matched_companies) > 0 else []
        
        recruiter_count = 0
        sample_recruiters = []
        if company_ids:
            # Query DuckDB
            id_list_str = "','".join([cid.replace("'", "''") for cid in company_ids[:100]])
            rec_df = con.execute(f"""
                SELECT recruiter_name, email, title, location 
                FROM '{parquet_path}' 
                WHERE company_id IN ('{id_list_str}') OR canonical_company_id IN ('{id_list_str}')
                LIMIT 50
            """).df()
            recruiter_count = len(rec_df)
            if len(rec_df) > 0:
                sample_recruiters = rec_df[['recruiter_name', 'email', 'title']].to_dict(orient='records')[:3]
                
        # Also check local storage recruiters
        if len(matched_local) > 0:
            recruiter_count += len(matched_local)
            for _, r in matched_local.head(3).iterrows():
                sample_recruiters.append({
                    "recruiter_name": r.get('name'),
                    "email": r.get('email'),
                    "title": r.get('title')
                })
                
        is_found = (len(matched_companies) > 0 or len(matched_local) > 0)
        
        matched_comp_names = matched_companies['company_name'].unique().tolist() if len(matched_companies) > 0 else []
        matched_domains = matched_companies['primary_domain'].dropna().unique().tolist() if len(matched_companies) > 0 else []
        matched_websites = matched_companies['website'].dropna().unique().tolist() if len(matched_companies) > 0 else []
        
        results.append({
            "index": idx,
            "query_company": raw_query,
            "status": "FOUND" if is_found else "NOT FOUND",
            "matched_company_names": matched_comp_names,
            "primary_domains": matched_domains,
            "websites": matched_websites,
            "recruiter_count": recruiter_count,
            "sample_recruiters": sample_recruiters,
            "local_import_matches": len(matched_local)
        })
        
    # Save full results
    out_file = "c:/TalentOpsAI/backend/scratch/detailed_111_search_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    found = [r for r in results if r['status'] == "FOUND"]
    not_found = [r for r in results if r['status'] == "NOT FOUND"]
    
    print("\n" + "="*80)
    print(f"SEARCH COMPLETE: {len(found)} ALREADY EXIST ({len(found)/len(COMPANIES_LIST)*100:.1f}%) | {len(not_found)} NEW / NOT FOUND ({len(not_found)/len(COMPANIES_LIST)*100:.1f}%)")
    print("="*80)
    
    print(f"\n--- FOUND IN DATABASE / DATA FILES ({len(found)}) ---")
    for r in found:
        print(f"[{r['index']:3d}] {r['query_query'] if 'query_query' in r else r['query_company']} -> Matched: {r['matched_company_names']} | Domain: {r['primary_domains']} | Recruiters: {r['recruiter_count']}")
        
    print(f"\n--- NOT FOUND / MISSING ({len(not_found)}) ---")
    for r in not_found:
        print(f"[{r['index']:3d}] {r['query_company']}")

if __name__ == "__main__":
    run_deep_search()
