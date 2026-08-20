import duckdb
import os
import sys
import time

sys.path.append('backend')
from app.database import SessionLocal
from app.models.models import Company, Recruiter

FREE_DOMAINS = frozenset({
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
})
free_sql = ", ".join(f"'{d}'" for d in FREE_DOMAINS)

def extract_clean_company_name(domain: str, existing_names: list) -> str:
    """Derive a clean, professional company name from existing names or domain."""
    # Filter out junk names
    valid_names = [n for n in existing_names if n and n.lower() not in (
        'need to fill data', 'unknown', 'n/a', 'none', 'null', 'recruiter', ''
    )]
    if valid_names:
        # Pick the most frequent or clean name
        from collections import Counter
        counts = Counter(valid_names)
        # Prefer names with proper capitalization
        sorted_candidates = sorted(counts.items(), key=lambda x: (x[1], not x[0].isdigit(), len(x[0])), reverse=True)
        best_name = sorted_candidates[0][0]
        if not best_name.isdigit():
            return best_name
            
    # Fallback to domain
    name_part = domain.split('.')[0]
    # Special overrides for well known abbreviations
    overrides = {
        'rht': 'Robert Half Technology',
        'rhi': 'Robert Half International',
        'roberthalf': 'Robert Half',
        'teksystems': 'TEKsystems',
        'insightglobal': 'Insight Global',
        'kforce': 'Kforce',
        'apexsystems': 'Apex Systems',
        'randstadusa': 'Randstad USA',
        'randstaddigital': 'Randstad Digital',
        'beaconhillstaffing': 'Beacon Hill Staffing Group',
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
        'eliassen': 'Eliassen Group'
    }
    if name_part.lower() in overrides:
        return overrides[name_part.lower()]
        
    return name_part.replace('-', ' ').replace('_', ' ').title()

def main():
    print("Connecting to DuckDB & PostgreSQL...")
    con = duckdb.connect()
    db = SessionLocal()
    
    # 1. Fetch all PostgreSQL companies into a domain lookup
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
    
    # 2. Inspect all corporate domains and their associated company_ids in Parquet
    domain_summary = con.execute(f"""
        SELECT 
            LOWER(SPLIT_PART(email, '@', 2)) as domain,
            COUNT(*) as recruiter_count,
            MODE(company_id) as dominant_company_id,
            LIST(DISTINCT company_id) as all_cids
        FROM 'backend/data/recruiters_full.parquet'
        WHERE email LIKE '%@%' AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_sql})
        GROUP BY domain
    """).fetchall()
    
    print(f"Discovered {len(domain_summary):,} distinct corporate domains across Parquet.")
    
    # 3. Build the Domain -> Canonical Company ID mapping
    domain_to_canonical_cid = {}
    new_companies_to_create = []
    
    for domain, count, dominant_cid, all_cids in domain_summary:
        # Check if domain already has a PostgreSQL company
        canonical_cid = None
        if domain in pg_domain_to_company:
            canonical_cid = str(pg_domain_to_company[domain].company_id)
        else:
            # Check if dominant_cid is a valid PG company ID
            if dominant_cid and str(dominant_cid) in pg_id_to_company:
                canonical_cid = str(dominant_cid)
            else:
                # Find if ANY of all_cids is a valid PG company ID
                for cid in all_cids:
                    if cid and str(cid) in pg_id_to_company:
                        canonical_cid = str(cid)
                        break
                        
        if not canonical_cid:
            # Create a new canonical company ID from the dominant_cid or assign a clean ID
            if dominant_cid and str(dominant_cid).isdigit():
                canonical_cid = str(dominant_cid)
            else:
                # We will assign dominant_cid or derive
                canonical_cid = str(dominant_cid) if dominant_cid else domain
                
        domain_to_canonical_cid[domain] = canonical_cid
        
    print(f"Built canonical map for {len(domain_to_canonical_cid):,} domains.")
    print("Sample canonical mappings:")
    for dom in ['rht.com', 'roberthalf.com', 'insightglobal.com', 'teksystems.com', 'aerotek.com', 'kforce.com']:
        print(f"  {dom} -> Canonical CID: {domain_to_canonical_cid.get(dom)}")

    db.close()

if __name__ == "__main__":
    main()
