import os
import sys
import re

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.state_mapper import normalize_state, CITY_TO_STATE, ABBR_TO_NAME

def get_completeness_score(r: Recruiter) -> int:
    score = 0
    if r.recruiter_name and r.recruiter_name.strip(): score += 20
    if r.email and r.email.strip(): score += 30
    if r.phone and r.phone.strip(): score += 10
    if r.linkedin and r.linkedin.strip(): score += 10
    if r.specialization and r.specialization.strip(): score += 10
    if (r.location and r.location.strip()) or (r.state and r.state.strip()): score += 20
    return score

def extract_city(location: str) -> str:
    if not location: return None
    loc_upper = str(location).upper()
    
    # Simple extraction of common cities
    for city in CITY_TO_STATE.keys():
        if re.search(r'\b' + re.escape(city) + r'\b', loc_upper):
            return city.title()
    
    # Fallback parsing for "City, ST" format
    parts = [p.strip() for p in re.split(r'[,]+', location) if p.strip()]
    if parts:
        possible_city = parts[0]
        # Ignore if it's just a state name or abbr
        if possible_city.upper() not in ABBR_TO_NAME and possible_city.upper() not in ABBR_TO_NAME.values():
            return possible_city.title()
    
    return None

def main():
    db = SessionLocal()
    try:
        total = db.query(Recruiter).count()
        print(f"Total recruiters in DB: {total}")
        
        batch_size = 500
        updated = 0
        
        last_id = 0
        state_file = os.path.join(os.path.dirname(__file__), "last_id.txt")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        last_id = int(content)
                        print(f"Resuming safely from ID: {last_id}")
            except ValueError:
                print("last_id.txt was corrupted. Starting from beginning.")
                last_id = 0
        
        while True:
            from sqlalchemy.orm import joinedload
            recruiters = db.query(Recruiter).options(joinedload(Recruiter.company)).filter(Recruiter.recruiter_id > last_id).order_by(Recruiter.recruiter_id.asc()).limit(batch_size).all()
            if not recruiters:
                break
                
            for r in recruiters:
                changed = False
                
                # 1. Update completeness score
                score = get_completeness_score(r)
                if r.completeness_score != score:
                    r.completeness_score = score
                    changed = True
                
                # 2. Location enrichment
                original_loc = r.location or (r.company.location if r.company else None)
                norm_state = normalize_state(original_loc)
                norm_city = extract_city(original_loc)
                
                if norm_state and r.state != norm_state:
                    r.state = norm_state
                    changed = True
                
                if norm_city and r.normalized_city != norm_city:
                    r.normalized_city = norm_city
                    changed = True
                    
                # 3. Confidence and review flags
                confidence = "high"
                needs_review = False
                
                if original_loc and not norm_state:
                    # Location exists but couldn't parse state
                    confidence = "low"
                    needs_review = True
                elif original_loc and norm_state:
                    # Check if it was derived solely from city
                    loc_upper = original_loc.upper()
                    if not any(re.search(r'\b' + re.escape(st) + r'\b', loc_upper) for st in ABBR_TO_NAME.keys()) and not re.search(r'\b' + norm_state + r'\b', loc_upper):
                        confidence = "medium"
                        needs_review = True
                        
                if r.location_confidence != confidence:
                    r.location_confidence = confidence
                    changed = True
                if r.needs_review != needs_review:
                    r.needs_review = needs_review
                    changed = True
                    
                if changed:
                    updated += 1
            
            db.commit()
            last_id = recruiters[-1].recruiter_id
            with open(state_file, "w") as f:
                f.write(str(last_id))
                
            print(f"Processed up to ID {last_id}...")
            
        print(f"Enrichment completely finished. Updated {updated} records.")
        if os.path.exists(state_file):
            os.remove(state_file)
    except Exception as e:
        print(f"Error during enrichment: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
