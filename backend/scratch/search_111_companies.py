import os
import re
import json
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text

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
    # remove legal suffixes, parentheses, punctuation
    s = name.lower()
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r'\b(inc|incorporated|llc|corp|corporation|ltd|limited|group|services|solutions|consulting|partners|technologies|talent|staffing|systems|company|co)\b', '', s)
    s = re.sub(r'[^a-z0-9]', '', s)
    return s.strip()

def main():
    print(f"Total companies to search: {len(COMPANIES_LIST)}")
    
    parquet_files = [
        "c:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet",
        "c:/TalentOpsAI/backend/data/recruiters_full.parquet",
        "c:/TalentOpsAI/backend/archived_recruiters_unified.parquet",
        "c:/TalentOpsAI/local_storage_import.parquet"
    ]
    
    existing_parquets = [p for p in parquet_files if os.path.exists(p)]
    print(f"Found {len(existing_parquets)} parquet files to search: {existing_parquets}")
    
    con = duckdb.connect()
    
    dfs = []
    for p in existing_parquets:
        try:
            print(f"Reading {p}...")
            df = con.execute(f"SELECT DISTINCT company, website, recruiter_email, recruiter_name, location, '{os.path.basename(p)}' as source_file FROM '{p}' WHERE company IS NOT NULL").df()
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {p}: {e}")
            
    if dfs:
        df_all = pd.concat(dfs, ignore_index=True)
    else:
        df_all = pd.DataFrame(columns=['company', 'website', 'recruiter_email', 'recruiter_name', 'location', 'source_file'])
        
    print(f"Total records loaded across all parquet files: {len(df_all)}")
    df_all['clean_company'] = df_all['company'].apply(clean_company_name)
    
    # Load Postgres DB
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        from dotenv import load_dotenv
        load_dotenv("c:/TalentOpsAI/backend/.env")
        db_url = os.environ.get("DATABASE_URL")
    
    pg_companies = {}
    pg_recruiters = []
    if db_url:
        try:
            engine = create_engine(db_url)
            with engine.connect() as pg_con:
                res = pg_con.execute(text("SELECT id, name, domain, industry, website FROM companies"))
                for row in res.fetchall():
                    pg_companies[row[1]] = {
                        "id": row[0],
                        "name": row[1],
                        "domain": row[2],
                        "clean": clean_company_name(row[1])
                    }
                print(f"Total companies in PostgreSQL DB: {len(pg_companies)}")
                
                res_rec = pg_con.execute(text("SELECT id, name, email, company, title FROM recruiters WHERE company IS NOT NULL LIMIT 500000"))
                for row in res_rec.fetchall():
                    pg_recruiters.append({
                        "name": row[1],
                        "email": row[2],
                        "company": row[3],
                        "clean_company": clean_company_name(row[3])
                    })
                print(f"Total recruiters in PostgreSQL DB: {len(pg_recruiters)}")
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")

    results = []
    
    for idx, comp in enumerate(COMPANIES_LIST, 1):
        clean_target = clean_company_name(comp)
        
        # 1. Parquet Search
        exact_matches = df_all[df_all['company'].str.lower() == comp.lower()]
        
        if len(exact_matches) == 0 and clean_target:
            clean_matches = df_all[df_all['clean_company'] == clean_target]
        else:
            clean_matches = pd.DataFrame()
            
        if len(exact_matches) == 0 and len(clean_matches) == 0 and len(clean_target) >= 4:
            # Word boundary regex or contains
            partial_matches = df_all[df_all['clean_company'].str.contains(clean_target, regex=False)]
        else:
            partial_matches = pd.DataFrame()
            
        matched_df = exact_matches if len(exact_matches) > 0 else (clean_matches if len(clean_matches) > 0 else partial_matches)
        
        # 2. Postgres Companies Search
        matched_pg_comps = []
        for name, data in pg_companies.items():
            if name.lower() == comp.lower() or (clean_target and data['clean'] == clean_target) or (clean_target and len(clean_target) >= 5 and clean_target in data['clean']):
                matched_pg_comps.append(name)
                
        # 3. Postgres Recruiters Search
        matched_pg_rec = [r for r in pg_recruiters if r['company'].lower() == comp.lower() or (clean_target and r['clean_company'] == clean_target) or (clean_target and len(clean_target) >= 5 and clean_target in r['clean_company'])]
        
        num_parquet_records = len(matched_df)
        distinct_names = matched_df['company'].unique().tolist() if num_parquet_records > 0 else []
        sources = matched_df['source_file'].unique().tolist() if num_parquet_records > 0 else []
        sample_emails = matched_df['recruiter_email'].dropna().unique().tolist()[:3] if num_parquet_records > 0 else []
        sample_websites = matched_df['website'].dropna().unique().tolist()[:2] if num_parquet_records > 0 else []
        
        is_found = (num_parquet_records > 0 or len(matched_pg_comps) > 0 or len(matched_pg_rec) > 0)
        status = "FOUND" if is_found else "NOT FOUND"
        
        res_item = {
            "index": idx,
            "query_company": comp,
            "status": status,
            "parquet_count": num_parquet_records,
            "sources": sources,
            "matched_names_in_data": distinct_names,
            "sample_websites": sample_websites,
            "sample_emails": sample_emails,
            "postgres_companies": matched_pg_comps,
            "postgres_recruiters_count": len(matched_pg_rec)
        }
        results.append(res_item)
        
    out_file = "c:/TalentOpsAI/backend/scratch/search_111_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    found_list = [r for r in results if r["status"] == "FOUND"]
    not_found_list = [r for r in results if r["status"] == "NOT FOUND"]
    
    print("\n" + "="*80)
    print(f"SEARCH SUMMARY: {len(found_list)} FOUND | {len(not_found_list)} NOT FOUND out of {len(COMPANIES_LIST)}")
    print("="*80)
    
    print("\n--- FOUND COMPANIES ---")
    for r in found_list:
        print(f"[{r['index']:3d}] {r['query_company']} -> {r['parquet_count']} parquet records | PG: {r['postgres_companies']} ({r['postgres_recruiters_count']} recs)")
        
    print("\n--- NOT FOUND COMPANIES ---")
    for r in not_found_list:
        print(f"[{r['index']:3d}] {r['query_company']}")

if __name__ == "__main__":
    main()
