import sys
import re
from sqlalchemy import text
from app.database import engine
from app.models.models import Recruiter, Company
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def extract_name_from_email(email):
    if not email or "@" not in email:
        return None
    local_part = email.split('@')[0].lower()
    local_part = re.sub(r'[^a-z0-9\.]', '', local_part)
    
    # f.last@domain
    if '.' in local_part:
        parts = local_part.split('.')
        if len(parts) >= 2 and len(parts[0]) >= 1 and len(parts[1]) >= 2:
            first = parts[0].capitalize()
            last = parts[1].capitalize()
            return f"{first} {last}"
            
    # flast@domain
    if len(local_part) > 3 and sum(c.isdigit() for c in local_part) < 3:
        first = local_part[0].upper() + "."
        last = local_part[1:].capitalize()
        return f"{first} {last}"
        
    return None

def run_repair():
    db = SessionLocal()
    try:
        print("Finding corrupted recruiters...", flush=True)
        # Query 1: names that exactly match their company name
        q1 = """
        SELECT r.recruiter_id, r.email, c.company_name, r.recruiter_name
        FROM recruiters r
        JOIN companies c ON r.company_id = c.company_id
        WHERE lower(trim(r.recruiter_name)) = lower(trim(c.company_name))
           OR lower(trim(r.recruiter_name)) IN ('tek systems', 'bcubed engineering corp.', 'tek system')
        """
        rows = db.execute(text(q1)).fetchall()
        print(f"Found {len(rows)} corrupted records by company match.", flush=True)
        
        updates = []
        for row in rows:
            rec_id, email, c_name, old_name = row
            new_name = extract_name_from_email(email)
            if not new_name:
                new_name = f"Unknown {c_name} Recruiter"
            updates.append({"id": rec_id, "name": new_name, "reason": f"Recovered from email (was {old_name})"})
            
        print("Cleaning up 'Robert Mihalyi' bug...", flush=True)
        q2 = """
        SELECT recruiter_id, email, recruiter_name
        FROM recruiters
        WHERE recruiter_name ILIKE '%Robert Mihalyi%'
          AND email NOT ILIKE '%rmihalyi%'
          AND email NOT ILIKE '%robert%'
        """
        rob_rows = db.execute(text(q2)).fetchall()
        print(f"Found {len(rob_rows)} Robert Mihalyi corrupted records.", flush=True)
        for row in rob_rows:
            rec_id, email, old_name = row
            new_name = extract_name_from_email(email) or "Unknown Recruiter"
            updates.append({"id": rec_id, "name": new_name, "reason": "Fixed Robert Mihalyi bug"})
            
        if updates:
            print(f"Applying {len(updates)} updates...", flush=True)
            for i, u in enumerate(updates):
                db.execute(
                    text("UPDATE recruiters SET recruiter_name = :name, repair_reason = :reason WHERE recruiter_id = :id"),
                    u
                )
                if i > 0 and i % 500 == 0:
                    db.commit()
                    print(f"Committed {i}...", flush=True)
            db.commit()
            print("Done!", flush=True)
        else:
            print("No updates needed.", flush=True)
            
    finally:
        db.close()
        
if __name__ == "__main__":
    run_repair()
