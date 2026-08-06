import os
import glob
import time
import pandas as pd
from sqlalchemy import text
from app.database import SessionLocal

def import_shredded_data():
    db = SessionLocal()
    print("Starting broad data ingestion of shredded archives...", flush=True)
    start_time = time.time()
    
    # 1. Read all CSVs
    files = glob.glob(r'C:\TalentOpsAI\exports\archives\*.csv')
    dfs = []
    for f in files:
        if 'shredded_archive' in f or 'perpetual_shred' in f:
            try:
                df = pd.read_csv(f)
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {f}: {e}")
                
    if not dfs:
        print("No files found!")
        return
        
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"Total rows read: {len(combined_df)}")
    
    # 2. Filter out invalid emails and deduplicate by email
    combined_df = combined_df.dropna(subset=['email'])
    combined_df = combined_df[combined_df['email'].str.strip() != '']
    combined_df['email'] = combined_df['email'].str.strip().str.lower()
    combined_df = combined_df.drop_duplicates(subset=['email'])
    print(f"Unique valid emails: {len(combined_df)}")
    
    # 3. Deduplicate against existing DB
    print("Fetching existing emails from DB...")
    existing_emails = set(row[0] for row in db.execute(text("SELECT email FROM recruiters WHERE email IS NOT NULL")).fetchall())
    new_df = combined_df[~combined_df['email'].isin(existing_emails)]
    print(f"Total unique new records to import: {len(new_df)}")
    
    if new_df.empty:
        print("Nothing new to import.")
        return
        
    # 4. Extract domains for company mapping
    print("Extracting domains and mapping companies...")
    def extract_domain(email):
        try:
            return email.split('@')[-1].strip()
        except:
            return 'unlinked'
            
    new_df['domain'] = new_df['email'].apply(extract_domain)
    unique_domains = set(new_df['domain'].unique()) - {'unlinked'}
    
    domain_to_company_id = {}
    missing_list = list(unique_domains)
    for i in range(0, len(missing_list), 5000):
        batch_domains = missing_list[i:i+5000]
        rows = db.execute(text("SELECT company_id, website FROM companies WHERE website = ANY(:domains)"), {"domains": batch_domains}).fetchall()
        for comp_id, website in rows:
            if website:
                domain_to_company_id[website.strip().lower()] = comp_id
                
    # 5. Insert in batches
    print("Preparing inserts...")
    batch_size = 5000
    records = new_df.to_dict(orient='records')
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        insert_data = []
        for r in batch:
            domain = r["domain"]
            comp_id = domain_to_company_id.get(domain)
            
            name = (str(r.get("recruiter_name", "")) if pd.notna(r.get("recruiter_name")) else "Unknown")[:150]
            phone = str(r.get("phone", ""))[:30] if pd.notna(r.get("phone")) else None
            loc = str(r.get("state", ""))[:255] if pd.notna(r.get("state")) else None
            spec = str(r.get("title", ""))[:150] if pd.notna(r.get("title")) else None
            
            insert_data.append({
                "recruiter_name": name,
                "email": r["email"][:150],
                "phone": phone,
                "location": loc,
                "specialization": spec,
                "company_id": comp_id,
                "is_active": True,
                "needs_review": False
            })
            
        print(f"  Batch {i//batch_size + 1}: {len(insert_data)} inserts")
        db.execute(text(
            "INSERT INTO recruiters (recruiter_name, email, phone, location, specialization, company_id, is_active, needs_review, created_at, updated_at) "
            "VALUES (:recruiter_name, :email, :phone, :location, :specialization, :company_id, :is_active, :needs_review, NOW(), NOW()) "
            "ON CONFLICT (email) DO NOTHING"
        ), insert_data)
        db.commit()

    elapsed = time.time() - start_time
    print(f"Finished successfully. Took {elapsed:.2f} seconds.")

if __name__ == "__main__":
    import_shredded_data()
