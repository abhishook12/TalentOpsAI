import sys
import re
from sqlalchemy import text
from app.database import engine
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def extract_name_from_email(email):
    if not email or "@" not in email:
        return None
    local_part = email.split('@')[0].lower()
    local_part = re.sub(r'[^a-z0-9\.]', '', local_part)
    
    if '.' in local_part:
        parts = local_part.split('.')
        if len(parts) >= 2 and len(parts[0]) >= 1 and len(parts[1]) >= 2:
            first = parts[0].capitalize()
            last = parts[1].capitalize()
            return f"{first} {last}"
            
    if len(local_part) > 3 and sum(c.isdigit() for c in local_part) < 3:
        first = local_part[0].upper() + "."
        last = local_part[1:].capitalize()
        return f"{first} {last}"
        
    return None

def run_repair():
    db = SessionLocal()
    try:
        updates = []
        
        # We need a list of companies to find agency-like names
        print("Fetching all company names...", flush=True)
        all_companies = db.execute(text("SELECT company_name FROM companies WHERE company_name IS NOT NULL")).fetchall()
        company_name_set = {row[0].strip().lower() for row in all_companies if row[0]}
        print(f"Loaded {len(company_name_set)} company names.", flush=True)

        # Placeholders
        placeholders = {p.lower() for p in ['[Invalid Name]', 'Left Vm', 'Work Email', 'No Answer', 'Not Responding', 'Linkedin Member', 'Need to Fill Data']}
        agencies = {'robert half', 'insight global', 'mason frank international', 'apex systems', 'nesco resource', 'computer futures', 'steven douglas', 'randstad usa', 'jefferson frank', 'open system tech', 'harvey nash', 'synergy interactive', 'lorien global', 'piper companies', 'tek systems', 'bcubed engineering corp.'}
        
        # 1. Fetch ALL recruiters
        print("Fetching all recruiters... (this will take ~10 seconds)", flush=True)
        query = """
        SELECT r.recruiter_id, r.email, c.company_name, r.recruiter_name
        FROM recruiters r
        LEFT JOIN companies c ON r.company_id = c.company_id
        WHERE r.recruiter_name IS NOT NULL
        """
        all_recruiters = db.execute(text(query)).fetchall()
        print(f"Fetched {len(all_recruiters)} recruiters. Analyzing in memory...", flush=True)

        # First pass to find spammed names (names spanning > 5 companies)
        name_to_companies = {}
        for row in all_recruiters:
            rec_id, email, c_name, old_name = row
            if old_name and ' ' in old_name.strip():
                on = old_name.strip()
                if on not in name_to_companies:
                    name_to_companies[on] = set()
                name_to_companies[on].add(c_name)

        spammed_names = {name for name, comps in name_to_companies.items() if len(comps) > 5}
        print(f"Found {len(spammed_names)} spammed names.", flush=True)

        # Second pass to build updates
        for row in all_recruiters:
            rec_id, email, c_name, old_name = row
            old_name_clean = old_name.strip()
            old_name_lower = old_name_clean.lower()
            
            c_name_str = c_name or "Unknown Company"
            reason = None
            
            # Check placeholder
            if old_name_lower in placeholders:
                reason = f"Removed placeholder ({old_name_clean})"
            # Check spammed
            elif old_name_clean in spammed_names:
                new_name = extract_name_from_email(email)
                # If extracted name matches the spammed name, maybe it's valid (e.g. jsoares@ for Juliana Soares)
                if new_name and new_name.lower().replace('.', '') == old_name_lower.replace('.', ''):
                    pass # It's valid for this specific row!
                else:
                    reason = f"Fixed Spammed Name Bug ({old_name_clean})"
            # Check agency
            elif old_name_lower in company_name_set or old_name_lower in agencies:
                reason = f"Removed Agency Name ({old_name_clean})"
                
            if reason:
                new_name = extract_name_from_email(email) or f"Unknown {c_name_str} Recruiter"
                updates.append({"id": rec_id, "name": new_name, "reason": reason})

        if updates:
            print(f"Applying {len(updates)} total updates in bulk...", flush=True)
            chunk_size = 500
            for i in range(0, len(updates), chunk_size):
                chunk = updates[i:i+chunk_size]
                db.execute(text("UPDATE recruiters SET recruiter_name = :name, repair_reason = :reason WHERE recruiter_id = :id"), chunk)
                db.commit()
                print(f"Committed {i+len(chunk)}...", flush=True)
            print("Done!", flush=True)
        else:
            print("No updates needed.", flush=True)
            
    finally:
        db.close()

if __name__ == "__main__":
    run_repair()
