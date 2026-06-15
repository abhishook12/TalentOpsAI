import os
import sys
import re

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ..database import SessionLocal
from ..models.models import Recruiter, Company
from ..utils.state_mapper import normalize_state, CITY_TO_STATE, ABBR_TO_NAME

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


def is_placeholder_location(value: str | None) -> bool:
    if not value:
        return True
    text = str(value).strip().lower()
    return text in {"-", "—", "n/a", "na", "none", "null", "nil", "#error!", "not available"}


def looks_like_phone(value: str | None) -> bool:
    if not value:
        return False
    text = str(value).strip()
    if re.search(r"[A-Za-z]", text):
        alpha_count = len(re.findall(r"[A-Za-z]", text))
        if alpha_count > 6:
            return False
    phone_pattern = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if phone_pattern:
        return True
    digits = re.sub(r"\D", "", text)
    return len(digits) == 10 and len(text) <= 20


def extract_phone_value(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if match:
        cleaned = re.sub(r"\D", "", match.group(0))
        if len(cleaned) == 11 and cleaned.startswith("1"):
            cleaned = cleaned[1:]
        if len(cleaned) == 10:
            return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return None


def looks_like_email(value: str | None) -> bool:
    if not value:
        return False
    text = str(value).strip()
    return "@" in text and "." in text


def looks_like_location(value: str | None) -> bool:
    if not value or is_placeholder_location(value):
        return False
    text = str(value).strip()
    if looks_like_phone(text) or looks_like_email(text):
        return False
    if re.fullmatch(r"[0-9\-\+\s()./xextEXT#]+", text):
        return False
    return any(char.isalpha() for char in text)

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
                company_location = r.company.location if r.company else None
                original_loc = r.location or company_location
                norm_state = normalize_state(original_loc)
                norm_city = extract_city(original_loc)

                if company_location and looks_like_location(company_location):
                    if is_placeholder_location(r.location) or not r.location or not looks_like_location(r.location):
                        if r.location != company_location:
                            r.location = company_location
                            changed = True

                # Salvage obviously misparsed contact data that landed in the location field.
                if looks_like_phone(r.location):
                    if not r.phone:
                        clean_phone = extract_phone_value(r.location)
                        if clean_phone:
                            r.phone = clean_phone
                    r.location = company_location if looks_like_location(company_location) else None
                    changed = True
                elif looks_like_email(r.location):
                    if not r.email:
                        r.email = r.location.lower()
                    r.location = company_location if looks_like_location(company_location) else None
                    changed = True
                
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
