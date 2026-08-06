import os
import time
from collections import Counter
from sqlalchemy import text
from app.database import SessionLocal

def infer_pattern(email, name):
    if not name or not email or '@' not in email:
        return None
        
    domain = email.split('@')[1]
    local_part = email.split('@')[0].lower()
    
    parts = name.strip().lower().split()
    if len(parts) < 2:
        return None
        
    first = parts[0]
    last = parts[-1]
    
    # Try common patterns
    if local_part == f"{first}.{last}":
        return "{first}.{last}@{domain}"
    elif local_part == f"{first}{last}":
        return "{first}{last}@{domain}"
    elif local_part == f"{first[0]}{last}":
        return "{first_initial}{last}@{domain}"
    elif local_part == f"{first}_{last}":
        return "{first}_{last}@{domain}"
    elif local_part == first:
        return "{first}@{domain}"
    return None

def fill_email_patterns():
    db = SessionLocal()
    print("Starting Email Pattern Inference Engine...", flush=True)
    start_time = time.time()
    
    # 1. Fetch companies missing email_pattern
    companies = db.execute(text("SELECT company_id FROM companies WHERE email_pattern IS NULL OR TRIM(email_pattern) = ''")).fetchall()
    company_ids = [c[0] for c in companies]
    
    if not company_ids:
        print("No companies missing email_pattern.")
        return
        
    print(f"Analyzing {len(company_ids)} companies for email patterns...")
    
    updated_count = 0
    batch_size = 1000
    
    for i in range(0, len(company_ids), batch_size):
        batch = company_ids[i:i+batch_size]
        
        # Get recruiters for these companies
        recruiters = db.execute(text(
            "SELECT company_id, recruiter_name, email FROM recruiters WHERE company_id = ANY(:cids) AND email IS NOT NULL AND recruiter_name IS NOT NULL"
        ), {"cids": batch}).fetchall()
        
        # Group by company
        comp_recruiters = {}
        for r in recruiters:
            comp_recruiters.setdefault(r[0], []).append((r[1], r[2]))
            
        update_data = []
        for cid, recs in comp_recruiters.items():
            patterns = []
            for name, email in recs:
                pat = infer_pattern(email, name)
                if pat:
                    patterns.append(pat)
                    
            if patterns:
                most_common = Counter(patterns).most_common(1)[0][0]
                update_data.append({"company_id": cid, "pattern": most_common})
                
        if update_data:
            # Batch update
            for item in update_data:
                db.execute(text("UPDATE companies SET email_pattern = :pattern, updated_at = NOW() WHERE company_id = :company_id"), item)
            db.commit()
            updated_count += len(update_data)
            print(f"Batch {i//batch_size + 1}: Inferred {len(update_data)} patterns.")
            
    print(f"Finished. Successfully inferred and updated {updated_count} email patterns in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    fill_email_patterns()
