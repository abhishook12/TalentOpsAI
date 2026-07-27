import sys
import os
from sqlalchemy import text
from app.database import SessionLocal

def run_fix():
    print("Starting Comprehensive Company Fix...")
    db = SessionLocal()
    try:
        # 1. Fix company names that are emails
        print("Fixing company names that contain emails...")
        bad_companies = db.execute(text("SELECT company_id, company_name FROM companies WHERE company_name LIKE '%@%'")).mappings().all()
        
        fixed_names = 0
        for comp in bad_companies:
            email = comp["company_name"]
            if "@" in email:
                domain = email.split("@")[-1].lower()
                # Remove .com, .net, etc.
                name = domain.split(".")[0].replace("-", " ").title()
                
                # Manual overrides for known big ones
                if "insightglobal" in name.lower(): name = "Insight Global"
                elif "teksystems" in name.lower(): name = "TEKsystems"
                elif "roberthalf" in name.lower(): name = "Robert Half"
                elif "kforce" in name.lower(): name = "Kforce"
                elif "aerotek" in name.lower(): name = "Aerotek"
                elif "beaconhill" in name.lower(): name = "Beacon Hill Staffing"
                elif "randstad" in name.lower(): name = "Randstad"
                elif "judge" in name.lower(): name = "The Judge Group"
                
                db.execute(text("UPDATE companies SET company_name = :name WHERE company_id = :cid"), {"name": name, "cid": comp["company_id"]})
                fixed_names += 1
                
        print(f"Fixed {fixed_names} corrupted company names.")

        # 2. Fix locations that are phone numbers or junk
        print("Scrubbing junk locations...")
        res = db.execute(text("""
            UPDATE companies 
            SET location = NULL 
            WHERE location LIKE '%-%-%' OR location LIKE '%ext.%' OR location = '' OR location IS NULL;
        """))
        print(f"Scrubbed {res.rowcount} junk locations.")

        # 3. Infer headquarters from the majority of recruiters
        print("Inferring Headquarters location from recruiter density...")
        hq_res_data = db.execute(text("""
            SELECT company_id, normalized_city || ', ' || state as loc
            FROM recruiters
            WHERE normalized_city IS NOT NULL AND normalized_city != '' AND state IS NOT NULL AND state != ''
        """)).mappings().all()

        from collections import defaultdict
        comp_locs = defaultdict(list)
        for row in hq_res_data:
            comp_locs[row['company_id']].append(row['loc'])

        updates = 0
        for cid, locs in comp_locs.items():
            top_loc = max(set(locs), key=locs.count)
            db.execute(text("UPDATE companies SET location = :loc WHERE company_id = :cid AND location IS NULL"), {"loc": top_loc, "cid": cid})
            updates += 1

        print(f"Inferred {updates} Headquarters locations!")

        db.commit()
        print("All company fixes applied successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_fix()
