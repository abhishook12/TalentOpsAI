import duckdb
import os
import sys
import time
import shutil

sys.path.append('backend')
from app.database import SessionLocal
from app.models.models import Company, Recruiter

PARQUET_PATH = 'backend/data/recruiters_full.parquet'
BACKUP_PATH = 'backend/data/recruiters_full.parquet.bak_domain_unification'

FREE_DOMAINS = frozenset({
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
})
free_sql = ", ".join(f"'{d}'" for d in FREE_DOMAINS)

def get_well_known_name(domain: str) -> str:
    name_part = domain.split('.')[0].lower()
    overrides = {
        'rht': 'Robert Half Technology',
        'rhi': 'Robert Half International',
        'roberthalf': 'Robert Half',
        'teksystems': 'TEKsystems',
        'insightglobal': 'Insight Global',
        'kforce': 'Kforce',
        'apexsystems': 'Apex Systems',
        'apexsystemsinc': 'Apex Systems',
        'randstadusa': 'Randstad USA',
        'randstaddigital': 'Randstad Digital',
        'beaconhillstaffing': 'Beacon Hill Staffing Group',
        'bhsg': 'Beacon Hill Staffing Group',
        'brooksource': 'Brooksource',
        'judge': 'The Judge Group',
        'aerotek': 'Aerotek',
        'actalentservices': 'Actalent',
        'allegisgroup': 'Allegis Group',
        'disys': 'DISYS',
        'modis': 'Modis',
        'experis': 'Experis',
        'manpower': 'ManpowerGroup',
        'kellyservices': 'Kelly Services',
        'adeccousa': 'Adecco',
        'hays': 'Hays',
        'collabera': 'Collabera',
        'eliassen': 'Eliassen Group',
        'rcmt': 'RCM Technologies',
        'rgp': 'Resources Global Professionals',
        'renuke': 'ReNuke Services',
        'rangam': 'Rangam Consultants',
        'reyrey': 'Reynolds and Reynolds',
        'procomservices': 'Procom Services',
        'yoh': 'Yoh Staffing',
        'medixteam': 'Medix',
        'entegee': 'Entegee',
        'vaco': 'Vaco'
    }
    if name_part in overrides:
        return overrides[name_part]
    return name_part.replace('-', ' ').replace('_', ' ').title()

def main():
    print("="*75)
    print("=== FULL DOMAIN UNIFICATION & DEDUPLICATION ENGINE ===")
    print("="*75)
    
    t0 = time.time()
    db = SessionLocal()
    con = duckdb.connect()
    
    # 1. Fetch all PostgreSQL companies
    pg_companies = db.query(Company).all()
    pg_domain_to_company = {}
    pg_id_to_company = {}
    for c in pg_companies:
        pg_id_to_company[str(c.company_id)] = c
        if c.primary_domain:
            dom = c.primary_domain.strip().lower()
            if dom not in pg_domain_to_company:
                pg_domain_to_company[dom] = c
                
    print(f"Loaded {len(pg_companies):,} companies from PostgreSQL.")
    
    # 2. Extract all corporate domains and candidate company_ids from Parquet
    print("Analyzing corporate domains in Parquet...")
    domain_summary = con.execute(f"""
        SELECT 
            LOWER(SPLIT_PART(email, '@', 2)) as domain,
            COUNT(*) as recruiter_count,
            MODE(company_id) as dominant_company_id,
            LIST(DISTINCT company_id) as all_cids
        FROM '{PARQUET_PATH}'
        WHERE email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql})
        GROUP BY domain
    """).fetchall()
    
    print(f"Found {len(domain_summary):,} distinct corporate domains.")
    
    # 3. Create mapping table
    domain_to_canonical = {}
    companies_to_create = []
    
    for domain, count, dominant_cid, all_cids in domain_summary:
        canonical_cid = None
        canonical_name = None
        
        if domain in pg_domain_to_company:
            c = pg_domain_to_company[domain]
            canonical_cid = str(c.company_id)
            canonical_name = c.company_name
        else:
            # Check dominant_cid
            if dominant_cid and str(dominant_cid) in pg_id_to_company:
                c = pg_id_to_company[str(dominant_cid)]
                canonical_cid = str(c.company_id)
                canonical_name = c.company_name
                # Also set primary_domain if missing
                if not c.primary_domain:
                    c.primary_domain = domain
            else:
                # Check other cids
                for cid in all_cids:
                    if cid and str(cid) in pg_id_to_company:
                        c = pg_id_to_company[str(cid)]
                        canonical_cid = str(c.company_id)
                        canonical_name = c.company_name
                        if not c.primary_domain:
                            c.primary_domain = domain
                        break
                        
        if not canonical_cid:
            # If dominant_cid is numeric, check if it's usable or pick one
            if dominant_cid and str(dominant_cid).isdigit() and int(dominant_cid) > 0:
                canonical_cid = str(dominant_cid)
            else:
                canonical_cid = str(dominant_cid) if dominant_cid else domain
            canonical_name = get_well_known_name(domain)
            
        domain_to_canonical[domain] = (canonical_cid, canonical_name)

    db.commit()
    print(f"Constructed canonical resolution for all {len(domain_to_canonical):,} domains.")
    
    # 4. Create DuckDB mapping table
    con.execute("CREATE TEMP TABLE domain_map (domain VARCHAR, canonical_cid VARCHAR)")
    map_rows = [(dom, cid) for dom, (cid, name) in domain_to_canonical.items()]
    con.executemany("INSERT INTO domain_map VALUES (?, ?)", map_rows)
    
    # 5. Backup current Parquet
    if not os.path.exists(BACKUP_PATH):
        print(f"Creating backup of Parquet dataset to {BACKUP_PATH}...")
        shutil.copy2(PARQUET_PATH, BACKUP_PATH)
        
    # 6. Transform Parquet with canonicalized company_id
    print("Applying canonical company_id updates across all 2.3M records in Parquet...")
    temp_parquet = 'backend/data/recruiters_unified_temp.parquet'
    
    con.execute(f"""
        COPY (
            SELECT 
                r.recruiter_id,
                r.recruiter_name,
                r.normalized_recruiter_name,
                r.email,
                r.phone,
                r.email2,
                r.phone2,
                r.email3,
                r.phone3,
                r.email4,
                r.phone4,
                r.alternate_emails,
                r.alternate_phones,
                r.linkedin,
                r.specialization,
                r.title,
                r.notes,
                r.review_reason,
                COALESCE(dm.canonical_cid, r.company_id) AS company_id,
                r.location,
                r.state,
                r.normalized_city,
                r.location_confidence,
                r.state_source,
                r.state_confidence,
                r.state_reason,
                r.last_scan_at,
                r.completeness_score,
                r.needs_review,
                r.is_active,
                r.data_source,
                r.trust_score,
                r.source_job_id,
                r.raw_data,
                r.metadata_json,
                r.tags,
                r.created_at,
                r.updated_at,
                r.taxonomy_category,
                r.report_count,
                r.email_status,
                r.email_confidence,
                r.email_source,
                r.email_pattern_id,
                r.email_generated,
                r.email_verified_at,
                r.email_last_checked_at,
                COALESCE(dm.canonical_cid, r.canonical_company_id, r.company_id) AS canonical_company_id,
                r.historical_company_id,
                r.company_domain_id,
                r.raw_email_value,
                r.repair_reason,
                r.user_id,
                r.quality_score,
                r.missing_fields,
                r.sentinel_status,
                r.last_verified_at,
                r.company_confidence,
                r.company_reasoning,
                r.is_archived,
                r.merged_into_id,
                r.logo_url,
                r.is_deliverable,
                r.seniority_level,
                r.timezone_code,
                r.timezone,
                r.company_scale
            FROM '{PARQUET_PATH}' r
            LEFT JOIN domain_map dm 
              ON LOWER(SPLIT_PART(r.email, '@', 2)) = dm.domain
             AND r.email LIKE '%@%'
        ) TO '{temp_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    
    # Replace original parquet with unified parquet
    if os.path.exists(temp_parquet):
        shutil.move(temp_parquet, PARQUET_PATH)
        print(f"Successfully generated unified {PARQUET_PATH}!")
        
    # 7. Verify the unification in the new Parquet file
    new_frag = con.execute(f"""
        SELECT 
            LOWER(SPLIT_PART(email, '@', 2)) as domain,
            COUNT(DISTINCT company_id) as distinct_cids,
            COUNT(*) as total_rows
        FROM '{PARQUET_PATH}'
        WHERE email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql})
        GROUP BY domain
        HAVING COUNT(DISTINCT company_id) > 1
    """).fetchall()
    
    print(f"\n--- VERIFICATION: Fragmented corporate domains remaining: {len(new_frag)} (Expected: 0) ---")
    
    # Check rht.com specifically
    rht_check = con.execute(f"""
        SELECT 
            company_id,
            COUNT(*) as cnt,
            MIN(email) as sample_email
        FROM '{PARQUET_PATH}'
        WHERE email LIKE '%@rht.com'
        GROUP BY company_id
    """).fetchall()
    print("--- RHT.COM IN NEW PARQUET ---")
    for r in rht_check:
        print(r)
        
    # Check roberthalf.com specifically
    rh_check = con.execute(f"""
        SELECT 
            company_id,
            COUNT(*) as cnt,
            MIN(email) as sample_email
        FROM '{PARQUET_PATH}'
        WHERE email LIKE '%@roberthalf.com'
        GROUP BY company_id
    """).fetchall()
    print("--- ROBERTHALF.COM IN NEW PARQUET ---")
    for r in rh_check:
        print(r)
        
    db.close()
    elapsed = time.time() - t0
    print(f"\n=== UNIFICATION COMPLETED IN {elapsed:.2f}s ===")

if __name__ == "__main__":
    main()
