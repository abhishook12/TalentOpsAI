import sys, os, re, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from app.database import SessionLocal
from app.models.models import Recruiter
from app.services.platform_alarm import PlatformSafetyAlarm

# STATE NAME TO ABBREVIATION MAPPING FOR ACCURATE LOCATION ALIGNMENT
US_STATES_MAP = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'district of columbia': 'DC', 'washington dc': 'DC', 'd.c.': 'DC'
}

VALID_STATE_CODES = set(US_STATES_MAP.values())

def standardize_phone(raw_phone):
    if not raw_phone: return raw_phone
    s = str(raw_phone).strip()
    # If extension present, preserve it or clean main 10 digits
    digits = re.sub(r'[^0-9]', '', s)
    if len(digits) == 10:
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
    return s

def smart_title_case(text):
    if not text: return text
    s = str(text).strip()
    if len(s) < 2: return s.upper()
    
    # Common HR/Recruiting acronyms that must stay ALL-CAPS
    acronyms = {'HR', 'TA', 'IT', 'AI', 'VP', 'SVP', 'EVP', 'CEO', 'COO', 'CTO', 'CHRO', 'US', 'UK', 'ML', 'SW'}
    
    words = re.split(r'(\s+|[\-\.\/\,]+)', s)
    formatted = []
    for w in words:
        if not w or w.isspace() or re.match(r'^[\-\.\/\,]+$', w):
            formatted.append(w)
            continue
        clean_w = re.sub(r'[^a-zA-Z0-9]', '', w).upper()
        if clean_w in acronyms and len(w) <= 4:
            formatted.append(w.upper())
        elif len(w) == 2 and w.upper() in {'IV', 'VI', 'II', 'IX'}:
            formatted.append(w.upper())
        else:
            formatted.append(w.capitalize())
    return ''.join(formatted)

def extract_state_and_city_from_location(loc_str):
    if not loc_str: return None, None
    s = str(loc_str).strip()
    
    # E.g. "Austin, TX" or "San Francisco, CA 94105" or "Dallas, Texas"
    parts = [p.strip() for p in s.split(',') if p.strip()]
    if len(parts) >= 2:
        city_part = parts[0]
        state_part = parts[1]
        
        # Strip zip codes
        state_clean = re.sub(r'\b[0-9]{5}(-[0-9]{4})?\b', '', state_part).strip().upper()
        if state_clean in VALID_STATE_CODES:
            return state_clean, smart_title_case(city_part)
        
        state_lower = state_part.lower().strip()
        if state_lower in US_STATES_MAP:
            return US_STATES_MAP[state_lower], smart_title_case(city_part)
            
    # Single string match
    for name, code in US_STATES_MAP.items():
        if re.search(r'\b' + re.escape(name) + r'\b', s, flags=re.I):
            return code, None
        if re.search(r'\b' + re.escape(code) + r'\b', s):
            return code, None
            
    return None, None

def run_deep_accuracy_engine():
    db = SessionLocal()
    print("=======================================================================")
    print("=== DEEP DATA ACCURACY & LOCATION ALIGNMENT ENGINE ===")
    print("=======================================================================")
    sys.stdout.flush()

    total_recs = db.query(Recruiter).count()
    batch_size = 5000
    total_batches = (total_recs + batch_size - 1) // batch_size

    phones_standardized = 0
    names_normalized = 0
    titles_normalized = 0
    locations_extracted = 0

    for batch_idx in range(total_batches):
        # Rule #8 Safety Check: Verify platform thresholds before every batch
        audit = PlatformSafetyAlarm.check_and_alert_all()
        if audit.get('is_alarm_active'):
            print("🚨 [SAFETY SHIELD] 70% threshold reached! Pausing accuracy engine safely.")
            break

        offset = batch_idx * batch_size
        rows = db.query(Recruiter).order_by(Recruiter.recruiter_id).offset(offset).limit(batch_size).all()
        if not rows: break

        batch_dirty = False
        for r in rows:
            row_dirty = False

            # A. Phone Number Standardization
            if r.phone and re.match(r'^[0-9]{10}$|^1[0-9]{10}$|^\([0-9]{3}\)\s*[0-9]{3}\-[0-9]{4}$', str(r.phone).strip()):
                clean_p = standardize_phone(r.phone)
                if clean_p != r.phone:
                    r.phone = clean_p
                    phones_standardized += 1
                    row_dirty = True

            # B. Name Case Standardization
            if r.recruiter_name and (r.recruiter_name == r.recruiter_name.lower() or (r.recruiter_name == r.recruiter_name.upper() and len(r.recruiter_name) > 3)):
                better_n = smart_title_case(r.recruiter_name)
                if better_n != r.recruiter_name:
                    r.recruiter_name = better_n
                    r.normalized_recruiter_name = better_n.lower()
                    names_normalized += 1
                    row_dirty = True

            # C. Title Case Standardization
            if r.title and (r.title == r.title.lower() or (r.title == r.title.upper() and len(r.title) > 3)):
                better_t = smart_title_case(r.title)
                if better_t != r.title:
                    r.title = better_t
                    titles_normalized += 1
                    row_dirty = True

            # D. Location & State Code Alignment (Rule #2)
            if (not r.state or r.state == 'US' or r.state == 'N/A') and r.location:
                st_code, city_name = extract_state_and_city_from_location(r.location)
                if st_code and st_code != r.state:
                    r.state = st_code
                    if city_name and not r.normalized_city:
                        r.normalized_city = city_name
                    locations_extracted += 1
                    row_dirty = True

            if row_dirty:
                batch_dirty = True

        if batch_dirty:
            db.commit()

        if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
            print(f"   [Batch {batch_idx+1}/{total_batches}] Processed {min(offset+batch_size, total_recs):,} rows | Phones Standardized: {phones_standardized:,} | Names/Titles Cased: {names_normalized+titles_normalized:,} | States Mapped: {locations_extracted:,}")
            sys.stdout.flush()

    db.close()
    print("\n=======================================================================")
    print("=== DEEP DATA ACCURACY SUMMARY ===")
    print(f"  Total Recruiters Scanned: {total_recs:,}")
    print(f"  Phone Numbers Standardized: {phones_standardized:,}")
    print(f"  Names Normalized to Title Case: {names_normalized:,}")
    print(f"  Job Titles Standardized: {titles_normalized:,}")
    print(f"  Missing States Mapped from Location: {locations_extracted:,}")
    print("=======================================================================")
    sys.stdout.flush()

if __name__ == '__main__':
    run_deep_accuracy_engine()
