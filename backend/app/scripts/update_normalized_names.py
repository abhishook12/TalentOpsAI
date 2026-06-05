import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ..database import SessionLocal
from ..models.models import Recruiter, Company
from ..utils.normalizer import normalize_text

def main():
    db = SessionLocal()
    try:
        # Update companies
        companies = db.query(Company).all()
        comp_count = 0
        for c in companies:
            norm = normalize_text(c.company_name)
            if c.normalized_company_name != norm:
                c.normalized_company_name = norm
                comp_count += 1
        db.commit()
        print(f"Updated {comp_count} companies.")

        # Update recruiters
        # Using keyset pagination for speed
        last_rec = db.query(Recruiter).filter(Recruiter.normalized_recruiter_name.isnot(None)).order_by(Recruiter.recruiter_id.desc()).first()
        last_id = last_rec.recruiter_id if last_rec else 0
        batch_size = 5000
        rec_count = 0
        
        while True:
            recruiters = db.query(Recruiter).filter(Recruiter.recruiter_id > last_id).order_by(Recruiter.recruiter_id.asc()).limit(batch_size).all()
            if not recruiters:
                break
                
            for r in recruiters:
                norm = normalize_text(r.recruiter_name)
                if r.normalized_recruiter_name != norm:
                    r.normalized_recruiter_name = norm
                    rec_count += 1
            
            db.commit()
            last_id = recruiters[-1].recruiter_id
            print(f"Processed up to recruiter ID {last_id}")
            
        print(f"Updated {rec_count} recruiters.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
