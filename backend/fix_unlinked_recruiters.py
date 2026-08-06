import time
import sys
from sqlalchemy import text
from app.database import SessionLocal

def fix_recruiters_fast():
    db = SessionLocal()
    
    print("Fetching unlinked recruiters with raw SQL...", flush=True)
    # Fetch only needed columns
    recruiters = db.execute(text("SELECT recruiter_id, email FROM recruiters WHERE company_id IS NULL AND email IS NOT NULL AND email != ''")).fetchall()
    print(f"Found {len(recruiters)} unlinked recruiters.", flush=True)
    
    domains_to_ids = {}
    for r_id, email in recruiters:
        if '@' in email:
            domain = email.split('@')[1].strip().lower()
            if len(domain) >= 3 and '.' in domain and domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com']:
                if domain not in domains_to_ids:
                    domains_to_ids[domain] = []
                domains_to_ids[domain].append(r_id)
                
    print(f"Grouped into {len(domains_to_ids)} valid unique domains.", flush=True)
    
    if not domains_to_ids:
        print("Nothing to do.")
        return
        
    print("Fetching existing companies...", flush=True)
    existing = db.execute(text("SELECT company_id, website, email_pattern FROM companies")).fetchall()
    
    domain_to_company_id = {}
    for comp_id, website, email_pattern in existing:
        if website:
            domain_to_company_id[website.strip().lower()] = comp_id
        if email_pattern:
            domain_to_company_id[email_pattern.strip().lower()] = comp_id
            
    missing_domains = set(domains_to_ids.keys()) - set(domain_to_company_id.keys())
    print(f"Need to create {len(missing_domains)} new companies.", flush=True)
    
    if missing_domains:
        # Create companies in bulk using raw SQL
        insert_data = []
        for d in missing_domains:
            name = d.split('.')[0].replace('-', ' ').title()
            insert_data.append({"company_name": name, "website": d, "email_pattern": d, "is_active": True})
            
        print("Inserting new companies...", flush=True)
        db.execute(text(
            "INSERT INTO companies (company_name, website, email_pattern, is_active, created_at, updated_at) "
            "VALUES (:company_name, :website, :email_pattern, :is_active, NOW(), NOW())"
        ), insert_data)
        db.commit()
        
        # Refetch the new companies to get their IDs
        new_existing = db.execute(text("SELECT company_id, website FROM companies WHERE website IN :domains"), {"domains": tuple(missing_domains)}).fetchall()
        for comp_id, website in new_existing:
            if website:
                domain_to_company_id[website.strip().lower()] = comp_id
                
    print("Preparing recruiter updates...", flush=True)
    update_data = []
    skipped = 0
    for domain, r_ids in domains_to_ids.items():
        comp_id = domain_to_company_id.get(domain)
        if comp_id:
            for r_id in r_ids:
                update_data.append({"r_id": r_id, "c_id": comp_id})
        else:
            skipped += len(r_ids)
            
    print(f"Executing raw bulk update for {len(update_data)} recruiters in batches...", flush=True)
    
    batch_size = 5000
    for i in range(0, len(update_data), batch_size):
        batch = update_data[i:i+batch_size]
        print(f"  Batch {i//batch_size + 1}: {len(batch)} updates", flush=True)
        # Using a fast Postgres UNNEST bulk update
        r_ids = [d["r_id"] for d in batch]
        c_ids = [d["c_id"] for d in batch]
        
        db.execute(text("""
            UPDATE recruiters AS r
            SET company_id = u.c_id
            FROM (SELECT unnest(:r_ids\\:\\:int[]) AS r_id, unnest(:c_ids\\:\\:int[]) AS c_id) AS u
            WHERE r.recruiter_id = u.r_id
        """), {"r_ids": r_ids, "c_ids": c_ids})
        db.commit()
        
    print(f"Finished successfully. Skipped {skipped} generic domains.", flush=True)

if __name__ == "__main__":
    start = time.time()
    fix_recruiters_fast()
    print(f"Took {time.time() - start:.2f} seconds.", flush=True)
