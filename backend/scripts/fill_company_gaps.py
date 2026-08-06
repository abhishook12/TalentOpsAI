import os
import time
from collections import Counter
from sqlalchemy import text
from app.database import SessionLocal

def fill_company_gaps():
    db = SessionLocal()
    print("Starting Recruiter-based Location Inference for Companies...", flush=True)
    start_time = time.time()
    
    # Fetch companies missing location
    companies = db.execute(text("SELECT company_id FROM companies WHERE location IS NULL OR TRIM(location) = ''")).fetchall()
    company_ids = [c[0] for c in companies]
    
    if not company_ids:
        print("No companies missing locations.")
        return
        
    print(f"Analyzing {len(company_ids)} companies for location inference...")
    
    updated_count = 0
    batch_size = 1000
    
    for i in range(0, len(company_ids), batch_size):
        batch = company_ids[i:i+batch_size]
        
        # Get recruiters with locations for these companies
        recruiters = db.execute(text(
            "SELECT company_id, location FROM recruiters WHERE company_id = ANY(:cids) AND location IS NOT NULL AND TRIM(location) != ''"
        ), {"cids": batch}).fetchall()
        
        # Group by company
        comp_locations = {}
        for r in recruiters:
            comp_locations.setdefault(r[0], []).append(r[1].strip())
            
        update_data = []
        for cid, locs in comp_locations.items():
            if locs:
                most_common_loc = Counter(locs).most_common(1)[0][0]
                update_data.append({"company_id": cid, "location": most_common_loc})
                
        if update_data:
            for item in update_data:
                db.execute(text("UPDATE companies SET location = :location, updated_at = NOW() WHERE company_id = :company_id"), item)
            db.commit()
            updated_count += len(update_data)
            print(f"Batch {i//batch_size + 1}: Inferred {len(update_data)} locations.")
            
    print(f"Finished. Successfully inferred and updated {updated_count} company locations in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    fill_company_gaps()
