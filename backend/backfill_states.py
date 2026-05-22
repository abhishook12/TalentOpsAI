import sys
sys.path.append("C:/TalentOpsAI/backend")
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.state_mapper import normalize_state

def backfill():
    db = SessionLocal()
    print("Starting backfill for companies...")
    companies = db.query(Company).all()
    updated_companies = 0
    
    for c in companies:
        if c.location:
            state = normalize_state(c.location)
            if state:
                c.state = state
                updated_companies += 1
    
    db.commit()
    print(f"Updated {updated_companies} companies with valid states.")
    
    print("Starting backfill for recruiters...")
    # Process in batches to avoid high memory usage
    batch_size = 5000
    offset = 0
    updated_recruiters = 0
    total_recruiters = db.query(Recruiter).count()
    
    while offset < total_recruiters:
        recruiters = db.query(Recruiter).offset(offset).limit(batch_size).all()
        for r in recruiters:
            # Determine location: recruiter's location, else company's location
            loc = r.location
            if not loc and r.company:
                loc = r.company.location
            
            if loc:
                state = normalize_state(loc)
                if state:
                    r.state = state
                    updated_recruiters += 1
                    
        db.commit()
        offset += batch_size
        print(f"Processed {min(offset, total_recruiters)} / {total_recruiters} recruiters...")

    print(f"Updated {updated_recruiters} recruiters with valid states.")
    db.close()

if __name__ == "__main__":
    backfill()
