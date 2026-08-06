import time
import pandas as pd
import sqlite3
from sqlalchemy import text
from app.database import SessionLocal

def import_local_data():
    db = SessionLocal()
    
    print("Fetching existing emails from DB...")
    db_emails = set(row[0].lower() for row in db.execute(text("SELECT email FROM recruiters WHERE email IS NOT NULL")).fetchall() if row[0])
    print(f"Found {len(db_emails)} existing emails.")
    
    print("\nReading parquet file...")
    try:
        df_parquet = pd.read_parquet('../local_storage_import.parquet')
        df_parquet = df_parquet.dropna(subset=['email'])
        parquet_records = df_parquet.to_dict('records')
        print(f"Read {len(parquet_records)} valid rows from parquet.")
    except Exception as e:
        print("Error reading parquet:", e)
        parquet_records = []
        
    print("\nReading sqlite deep extract...")
    try:
        conn = sqlite3.connect('../local_deep_extract.db')
        cursor = conn.cursor()
        # The table only has email and name
        cursor.execute("SELECT name, email FROM recruiters WHERE email IS NOT NULL")
        deep_records = [{"name": r[0], "email": r[1]} for r in cursor.fetchall()]
        print(f"Read {len(deep_records)} valid rows from sqlite.")
    except Exception as e:
        print("Error reading sqlite:", e)
        deep_records = []

    # Merge and deduplicate
    unique_records = {}
    
    # Process basic records first, so rich records overwrite them if there is an overlap
    for r in deep_records:
        email = r["email"].strip().lower()
        if email and email not in db_emails:
            unique_records[email] = {
                "recruiter_name": r["name"],
                "email": email,
                "title": None,
                "location": None,
                "phone": None,
                "company_name": None
            }
            
    # Process rich records
    for r in parquet_records:
        email = r["email"].strip().lower()
        if email and email not in db_emails:
            unique_records[email] = {
                "recruiter_name": r["name"],
                "email": email,
                "title": r.get("title"),
                "location": r.get("location"),
                "phone": r.get("phone"),
                "company_name": r.get("company")
            }
            
    records_to_import = list(unique_records.values())
    print(f"\nTotal unique new records to import: {len(records_to_import)}")
    
    if not records_to_import:
        print("Nothing to import.")
        return
        
    print("\nExtracting domains and mapping companies...")
    domains_to_records = {}
    for r in records_to_import:
        if '@' in r['email']:
            domain = r['email'].split('@')[1].strip().lower()
            if len(domain) >= 3 and '.' in domain and domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com']:
                if domain not in domains_to_records:
                    domains_to_records[domain] = []
                domains_to_records[domain].append(r)
            else:
                # Add a dummy domain for freemail so it still gets imported (but unlinked)
                if 'unlinked' not in domains_to_records:
                    domains_to_records['unlinked'] = []
                domains_to_records['unlinked'].append(r)

    print("Fetching existing companies...")
    existing = db.execute(text("SELECT company_id, website, email_pattern FROM companies")).fetchall()
    
    domain_to_company_id = {}
    for comp_id, website, email_pattern in existing:
        if website:
            domain_to_company_id[website.strip().lower()] = comp_id
        if email_pattern:
            domain_to_company_id[email_pattern.strip().lower()] = comp_id
            
    missing_domains = set([d for d in domains_to_records.keys() if d != 'unlinked']) - set(domain_to_company_id.keys())
    print(f"Need to create {len(missing_domains)} new companies.")
    
    if missing_domains:
        # Create companies in bulk using raw SQL
        insert_data = []
        for d in missing_domains:
            name = d.split('.')[0].replace('-', ' ').title()
            insert_data.append({"company_name": name, "website": d, "email_pattern": d, "is_active": True})
            
        print("Inserting new companies in batches...")
        batch_size = 5000
        for i in range(0, len(insert_data), batch_size):
            batch = insert_data[i:i+batch_size]
            db.execute(text(
                "INSERT INTO companies (company_name, website, email_pattern, is_active, created_at, updated_at) "
                "VALUES (:company_name, :website, :email_pattern, :is_active, NOW(), NOW())"
            ), batch)
            db.commit()
            
        print("Refetching new company IDs...")
        # Since missing_domains might be huge, use smaller batches for IN clause
        missing_list = list(missing_domains)
        for i in range(0, len(missing_list), 5000):
            batch_domains = missing_list[i:i+5000]
            new_existing = db.execute(text("SELECT company_id, website FROM companies WHERE website = ANY(:domains)"), {"domains": batch_domains}).fetchall()
            for comp_id, website in new_existing:
                if website:
                    domain_to_company_id[website.strip().lower()] = comp_id
                
    print("\nPreparing recruiter inserts...")
    insert_data = []
    
    for domain, recs in domains_to_records.items():
        comp_id = domain_to_company_id.get(domain) if domain != 'unlinked' else None
        for r in recs:
            name = (r["recruiter_name"] if pd.notna(r["recruiter_name"]) else "Unknown")[:150]
            phone = str(r["phone"])[:30] if pd.notna(r["phone"]) else None
            loc = str(r["location"])[:255] if pd.notna(r["location"]) else None
            spec = str(r["title"])[:150] if pd.notna(r["title"]) else None
            
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
            
    print(f"Executing raw bulk insert for {len(insert_data)} recruiters in batches...")
    
    batch_size = 5000
    for i in range(0, len(insert_data), batch_size):
        batch = insert_data[i:i+batch_size]
        print(f"  Batch {i//batch_size + 1}: {len(batch)} inserts", flush=True)
        db.execute(text(
            "INSERT INTO recruiters (recruiter_name, email, phone, location, specialization, company_id, is_active, needs_review, created_at, updated_at) "
            "VALUES (:recruiter_name, :email, :phone, :location, :specialization, :company_id, :is_active, :needs_review, NOW(), NOW()) "
            "ON CONFLICT (email) DO NOTHING"
        ), batch)
        db.commit()
        
    print(f"Finished successfully. Inserted {len(insert_data)} new recruiters.", flush=True)

if __name__ == "__main__":
    start = time.time()
    import_local_data()
    print(f"Took {time.time() - start:.2f} seconds.", flush=True)
