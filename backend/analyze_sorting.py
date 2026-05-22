import sys
import os

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models.models import Recruiter
from sqlalchemy import func

def run_analysis():
    db = SessionLocal()
    try:
        # Total counts
        total = db.query(Recruiter).count()
        enriched = db.query(Recruiter).filter(Recruiter.completeness_score > 0).count()
        
        # State distribution
        print("\n--- TOP 10 STATES ---")
        state_counts = db.query(Recruiter.state, func.count(Recruiter.recruiter_id)).group_by(Recruiter.state).order_by(func.count(Recruiter.recruiter_id).desc()).limit(10).all()
        for s, c in state_counts:
            print(f"{s or 'UNKNOWN'}: {c}")
            
        print("\n--- COMPLETENESS DISTRIBUTION ---")
        comp_counts = db.query(Recruiter.completeness_score, func.count(Recruiter.recruiter_id)).group_by(Recruiter.completeness_score).order_by(Recruiter.completeness_score.desc()).all()
        for s, c in comp_counts:
            print(f"Score {s}: {c} records")
            
        print("\n--- CONFIDENCE METRICS ---")
        needs_review = db.query(Recruiter).filter(Recruiter.needs_review == True).count()
        high_conf = db.query(Recruiter).filter(Recruiter.location_confidence == 'high').count()
        low_conf = db.query(Recruiter).filter(Recruiter.location_confidence == 'low').count()
        print(f"High Confidence: {high_conf}")
        print(f"Low Confidence: {low_conf}")
        print(f"Needs Manual Review: {needs_review}")
        
        print("\n--- MAPPING EXAMPLES (Original -> Normalized) ---")
        examples = db.query(Recruiter.location, Recruiter.normalized_city, Recruiter.state).filter(Recruiter.normalized_city != None).limit(20).all()
        for loc, city, state in examples:
            print(f"'{loc}' -> City: {city}, State: {state}")
            
    finally:
        db.close()

if __name__ == "__main__":
    run_analysis()
