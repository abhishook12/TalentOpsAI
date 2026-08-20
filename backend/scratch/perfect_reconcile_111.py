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

def clean_tokens(name: str):
    tokens = re.findall(r'[a-zA-Z0-9]+', name.lower())
    stop = {'inc', 'llc', 'corp', 'corporation', 'ltd', 'limited', 'group', 'services', 'solutions', 'consulting', 'partners', 'technologies', 'technology', 'talent', 'staffing', 'systems', 'company', 'co', 'the', 'international', 'enterprise', 'resources', 'technical', 'associates', 'global', 'com', 'a', 'vmg', 'pending', '8', 'certified'}
    return [t for t in tokens if t not in stop]

def simplify(s: str) -> str:
    return "".join(clean_tokens(s))

def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        df_pg = pd.read_sql("SELECT company_id, company_name, normalized_company_name, canonical_name, primary_domain, website, location, industry FROM companies", conn)
    
    df_pg['sim_name'] = df_pg['company_name'].apply(simplify)
    df_pg['sim_norm'] = df_pg['normalized_company_name'].fillna('').apply(simplify)
    df_pg['sim_canonical'] = df_pg['canonical_name'].fillna('').apply(simplify)
    
    parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
    if not os.path.exists(parquet_path):
        parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full.parquet"
    con = duckdb.connect()
    
    local_parquet_path = "c:/TalentOpsAI/local_storage_import.parquet"
    df_local = pd.DataFrame()
    if os.path.exists(local_parquet_path):
        df_local = con.execute(f"SELECT * FROM '{local_parquet_path}' WHERE company IS NOT NULL").df()
        df_local['sim_comp'] = df_local['company'].apply(simplify)

    results = []

    for idx, raw_query in enumerate(COMPANIES_LIST, 1):
        q_tokens = clean_tokens(raw_query)
        q_sim = "".join(q_tokens)
        q_lower = raw_query.lower().strip()
        
        # Exact/Strict Matches in PG
        # 1. Exact string match on company_name / normalized / canonical
        matched_pg = df_pg[
            (df_pg['company_name'].str.lower() == q_lower) |
            (df_pg['normalized_company_name'].str.lower() == q_lower) |
            (df_pg['canonical_name'].str.lower() == q_lower)
        ]
        
        # 2. Strict simplified tokens match (e.g. "Rabun Enterprise Solutions" -> "rabun", matched to "Rabun Enterprise")
        if len(matched_pg) == 0 and len(q_sim) >= 3:
            matched_pg = df_pg[
                (df_pg['sim_name'] == q_sim) |
                (df_pg['sim_norm'] == q_sim) |
                (df_pg['sim_canonical'] == q_sim)
            ]
            
        # 3. If multi-token query (e.g. "Global Path Resources" -> ['global', 'path']), all tokens must match
        if len(matched_pg) == 0 and len(q_tokens) >= 2:
            mask = pd.Series([True]*len(df_pg))
            for tok in q_tokens:
                mask = mask & (df_pg['company_name'].str.lower().str.contains(tok, regex=False) | df_pg['primary_domain'].fillna('').str.lower().str.contains(tok, regex=False))
            matched_pg = df_pg[mask]
            
        # 4. Local storage import exact/strict match
        matched_local = pd.DataFrame()
        if len(df_local) > 0:
            matched_local = df_local[
                (df_local['company'].str.lower() == q_lower) |
                (df_local['sim_comp'] == q_sim)
            ]

        # Fetch recruiters count
        company_ids = matched_pg['company_id'].dropna().astype(str).tolist() if len(matched_pg) > 0 else []
        
        sample_recs = []
        rec_count = 0
        if company_ids:
            id_list_str = "','".join([cid.replace("'", "''") for cid in company_ids[:30]])
            df_recs = con.execute(f"""
                SELECT recruiter_name, email, title, location 
                FROM '{parquet_path}' 
                WHERE (company_id IN ('{id_list_str}') OR canonical_company_id IN ('{id_list_str}'))
                  AND (recruiter_name IS NOT NULL OR email IS NOT NULL)
                LIMIT 50
            """).df()
            rec_count = len(df_recs)
            if len(df_recs) > 0:
                sample_recs = df_recs.fillna('').to_dict(orient='records')[:3]
                
        # Direct email domain lookup if 0 recruiters found but key token is specific
        if rec_count == 0 and len(q_tokens) >= 1:
            main_slug = "".join([t for t in q_tokens if len(t) >= 4])
            if len(main_slug) >= 5:
                df_recs_dom = con.execute(f"""
                    SELECT recruiter_name, email, title, location 
                    FROM '{parquet_path}' 
                    WHERE (email LIKE '%@{main_slug}.%' OR email LIKE '%@{main_slug}-%')
                      AND (recruiter_name IS NOT NULL OR email IS NOT NULL)
                    LIMIT 50
                """).df()
                if len(df_recs_dom) > 0:
                    rec_count = len(df_recs_dom)
                    sample_recs = df_recs_dom.fillna('').to_dict(orient='records')[:3]

        if len(matched_local) > 0:
            rec_count += len(matched_local)
            for _, r in matched_local.head(3).iterrows():
                sample_recs.append({
                    "recruiter_name": r.get('name') or '',
                    "email": r.get('email') or '',
                    "title": r.get('title') or '',
                    "location": r.get('location') or ''
                })

        is_present = (len(matched_pg) > 0 or len(matched_local) > 0 or rec_count > 0)
        
        matched_comp_names = matched_pg['company_name'].unique().tolist()[:3] if len(matched_pg) > 0 else []
        matched_domains = matched_pg['primary_domain'].dropna().unique().tolist()[:3] if len(matched_pg) > 0 else []
        
        results.append({
            "index": idx,
            "company": raw_query,
            "status": "ALREADY_EXISTS" if is_present else "NOT_FOUND",
            "matched_names": matched_comp_names,
            "domains": matched_domains,
            "recruiter_count": rec_count,
            "samples": sample_recs
        })

    with open("c:/TalentOpsAI/backend/scratch/perfect_reconcile_111.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    found_list = [r for r in results if r['status'] == "ALREADY_EXISTS"]
    not_found_list = [r for r in results if r['status'] == "NOT_FOUND"]

    print("="*80)
    print(f"STRICT VERIFICATION: {len(found_list)} ALREADY PRESENT | {len(not_found_list)} NOT FOUND (NEW)")
    print("="*80)

    print("\n--- NEW COMPANIES (NOT FOUND IN YOUR SYSTEM) ---")
    for r in not_found_list:
        print(f"{r['index']:3d}. {r['company']}")

if __name__ == "__main__":
    main()
