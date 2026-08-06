import os
import time
import psycopg
import re
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()
remote_url = os.getenv("DATABASE_URL")
if not remote_url:
    remote_url = "postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
elif remote_url.startswith("postgresql+psycopg://"):
    remote_url = remote_url.replace("postgresql+psycopg://", "postgresql://")

conn = psycopg.connect(remote_url)
cur = conn.cursor()

def extract_domain(email):
    if not email: return None
    parts = email.split('@')
    if len(parts) == 2:
        domain = parts[1].lower().strip()
        # Filter out common personal email domains
        personal_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'aol.com'}
        if domain not in personal_domains and '.' in domain:
            return domain
    return None

def format_company_name(domain):
    # e.g., oracle.com -> Oracle
    name = domain.split('.')[0]
    return name.capitalize()

def map_domains_to_companies():
    print("Fetching recruiters missing company_id...")
    cur.execute("SELECT recruiter_id, email FROM recruiters WHERE company_id IS NULL AND email IS NOT NULL")
    recruiters = cur.fetchall()
    
    print(f"Found {len(recruiters)} recruiters missing company_id.")
    
    domain_to_company_id = {}
    
    # Pre-fetch existing companies to memory for fast lookup
    cur.execute("SELECT website, company_id FROM companies WHERE website IS NOT NULL")
    for website, cid in cur.fetchall():
        domain_to_company_id[website] = cid
        
    updates = []
    new_companies = {} # domain -> company_name
    
    for r_id, email in recruiters:
        domain = extract_domain(email)
        if not domain:
            continue
            
        if domain in domain_to_company_id:
            updates.append((domain_to_company_id[domain], r_id))
        else:
            new_companies[domain] = format_company_name(domain)
            
    print(f"Found {len(new_companies)} new companies to create.")
    
    if new_companies:
        print("Inserting new companies...")
        insert_data = [(name, domain) for domain, name in new_companies.items()]
        # Batch insert companies
        cur.executemany(
            "INSERT INTO companies (company_name, website) VALUES (%s, %s)",
            insert_data
        )
        conn.commit()
        
        # Re-fetch new company IDs
        cur.execute("SELECT website, company_id FROM companies WHERE website IS NOT NULL")
        domain_to_company_id = {website: cid for website, cid in cur.fetchall()}
        
        # Now add the rest of the updates
        for r_id, email in recruiters:
            domain = extract_domain(email)
            if domain and domain in domain_to_company_id:
                # To avoid duplicate updates in the list, though it shouldn't happen
                updates.append((domain_to_company_id[domain], r_id))
                
    # Deduplicate updates
    final_updates = list(set(updates))
    print(f"Ready to link {len(final_updates)} recruiters to companies.")
    
    if final_updates:
        print("Updating recruiters...")
        cur.executemany(
            "UPDATE recruiters SET company_id = %s WHERE recruiter_id = %s",
            final_updates
        )
        conn.commit()
        
    print("Domain mapping complete.")

if __name__ == "__main__":
    start = time.time()
    map_domains_to_companies()
    print(f"Finished in {time.time() - start:.2f} seconds.")
    conn.close()
