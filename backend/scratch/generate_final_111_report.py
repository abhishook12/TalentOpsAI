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

def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        df_pg = pd.read_sql("SELECT company_id, company_name, normalized_company_name, canonical_name, primary_domain, website FROM companies", conn)
    
    df_pg['clean_name'] = df_pg['company_name'].apply(clean_company_name)
    df_pg['clean_norm'] = df_pg['normalized_company_name'].fillna('').apply(clean_company_name)
    df_pg['clean_canonical'] = df_pg['canonical_name'].fillna('').apply(clean_company_name)
    
    parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
    if not os.path.exists(parquet_path):
        parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full.parquet"
    con = duckdb.connect()
    
    # Also load local_storage_import
    local_parquet_path = "c:/TalentOpsAI/local_storage_import.parquet"
    df_local = pd.DataFrame()
    if os.path.exists(local_parquet_path):
        df_local = con.execute(f"SELECT * FROM '{local_parquet_path}' WHERE company IS NOT NULL").df()
        df_local['clean_company'] = df_local['company'].apply(clean_company_name)

    results = []
    
    # Specific known domain overrides for precise matching
    domain_map = {
        "ContractStaffingRecruiters.com": "contractstaffingrecruiters.com",
        "Linksap Europe Ltd": "linksap.eu",
        "cloudteam.com": "cloudteam.com",
        "SAFTech Software Solutions": "saftechusa.com",
        "ETHOS - Talent & Advisory": "ethosatwork.com",
        "Innovatus Technology Consulting": "innovatus-tech.com",
        "Cleartech Recruiting": "cleartechuk.com",
        "Geeks on Site": "geeksonsite.com",
        "DBI Staffing": "dbistaffing.com",
        "ProspHire": "prosphire.com",
        "SOLTECHPR": "soltechpr.com",
        "People4Net Inc": "people4net.com",
        "XMS Solutions, Inc.": "xmssolutions.com",
        "Rylex": "rylex.com",
        "OCT Consulting LLC": "octconsulting.com",
        "Tech 20 Solutions, Inc": "tech20solutions.com",
        "Covenant HR": "covenant-consulting.com",
        "Interactive Resources - iR": "iresources.com",
        "Makai Labs": "makailabs.com",
        "PM Solutions / PM College": "pmsolutions.com",
        "Outlier Mentors": "outlier.ai",
        "Prospectus IT Recruitment": "prospectusit.com",
        "Object Data Inc": "objectdata.com",
        "Full Cycle Services": "fullcycleservices.com",
        "ASAP Talent Services, a VMG Company": "asaptalent.com",
        "E Quality Corporation": "equalitycorp.com",
        "Apogee Global RMS": "apogeeglobal.com",
        "DCI Resources, LLC - Pending 8(a) Certified Company": "dciresources.com",
        "BTerminal Systems": "bterminal.com"
    }

    for idx, raw_query in enumerate(COMPANIES_LIST, 1):
        clean_q = clean_company_name(raw_query)
        lower_q = raw_query.lower().strip()
        custom_dom = domain_map.get(raw_query, "")
        
        # 1. Check in PG companies
        matched_pg = df_pg[
            (df_pg['company_name'].str.lower() == lower_q) |
            (df_pg['normalized_company_name'].str.lower() == lower_q) |
            (df_pg['canonical_name'].str.lower() == lower_q)
        ]
        
        if len(matched_pg) == 0 and clean_q:
            matched_pg = df_pg[
                (df_pg['clean_name'] == clean_q) |
                (df_pg['clean_norm'] == clean_q) |
                (df_pg['clean_canonical'] == clean_q)
            ]
            
        if len(matched_pg) == 0 and custom_dom:
            matched_pg = df_pg[
                (df_pg['primary_domain'].fillna('').str.contains(custom_dom, regex=False)) |
                (df_pg['website'].fillna('').str.contains(custom_dom, regex=False))
            ]
            
        if len(matched_pg) == 0 and len(clean_q) >= 4:
            matched_pg = df_pg[
                (df_pg['clean_name'].str.contains(clean_q, regex=False)) |
                (df_pg['clean_canonical'].str.contains(clean_q, regex=False)) |
                (df_pg['primary_domain'].fillna('').str.contains(clean_q, regex=False))
            ]

        # 2. Check in local storage import
        matched_local = pd.DataFrame()
        if len(df_local) > 0:
            matched_local = df_local[
                (df_local['company'].str.lower() == lower_q) |
                (df_local['clean_company'] == clean_q)
            ]
            if len(matched_local) == 0 and len(clean_q) >= 4:
                matched_local = df_local[df_local['clean_company'].str.contains(clean_q, regex=False)]

        # 3. Check in DuckDB Parquet by company_ids or direct email domain
        company_ids = matched_pg['company_id'].dropna().astype(str).tolist() if len(matched_pg) > 0 else []
        
        sample_recs = []
        rec_count = 0
        if company_ids:
            id_list_str = "','".join([cid.replace("'", "''") for cid in company_ids[:50]])
            df_recs = con.execute(f"""
                SELECT recruiter_name, email, title, location 
                FROM '{parquet_path}' 
                WHERE company_id IN ('{id_list_str}') OR canonical_company_id IN ('{id_list_str}')
                LIMIT 50
            """).df()
            rec_count = len(df_recs)
            if len(df_recs) > 0:
                sample_recs = df_recs[['recruiter_name', 'email', 'title']].to_dict(orient='records')[:3]
                
        # Direct email domain lookup in parquet if still 0
        if rec_count == 0 and custom_dom:
            df_recs_dom = con.execute(f"""
                SELECT recruiter_name, email, title, location 
                FROM '{parquet_path}' 
                WHERE email LIKE '%@{custom_dom}%' OR email LIKE '%.{custom_dom}%'
                LIMIT 50
            """).df()
            if len(df_recs_dom) > 0:
                rec_count = len(df_recs_dom)
                sample_recs = df_recs_dom[['recruiter_name', 'email', 'title']].to_dict(orient='records')[:3]

        if len(matched_local) > 0:
            rec_count += len(matched_local)
            for _, r in matched_local.head(3).iterrows():
                sample_recs.append({
                    "recruiter_name": r.get('name'),
                    "email": r.get('email'),
                    "title": r.get('title')
                })

        is_present = (len(matched_pg) > 0 or len(matched_local) > 0 or rec_count > 0)
        
        matched_names = matched_pg['company_name'].unique().tolist() if len(matched_pg) > 0 else []
        matched_domains = matched_pg['primary_domain'].dropna().unique().tolist() if len(matched_pg) > 0 else ([custom_dom] if rec_count > 0 and custom_dom else [])
        
        results.append({
            "index": idx,
            "company": raw_query,
            "status": "EXISTING (FOUND)" if is_present else "NEW (NOT IN DATA)",
            "matched_names": matched_names,
            "domains": matched_domains,
            "recruiter_count": rec_count,
            "samples": sample_recs
        })

    with open("c:/TalentOpsAI/backend/scratch/final_111_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    found_list = [r for r in results if "FOUND" in r['status']]
    new_list = [r for r in results if "NEW" in r['status']]
    
    print("="*80)
    print(f"FINAL AUDIT: {len(found_list)} ALREADY IN DATABASE/FILES ({len(found_list)/111*100:.1f}%) | {len(new_list)} COMPLETELY NEW ({len(new_list)/111*100:.1f}%)")
    print("="*80)
    
if __name__ == "__main__":
    main()
