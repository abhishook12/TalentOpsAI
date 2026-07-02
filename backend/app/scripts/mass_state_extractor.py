import sys, os, time, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from app.models.models import Recruiter

from app.utils.state_mapper import extract_state_detailed
from sqlalchemy import text

# Area code mapping
NANP_STATE_MAP = {
    '201': 'NJ', '202': 'DC', '203': 'CT', '205': 'AL', '206': 'WA', '207': 'ME', '208': 'ID', '209': 'CA',
    '210': 'TX', '212': 'NY', '213': 'CA', '214': 'TX', '215': 'PA', '216': 'OH', '217': 'IL', '218': 'MN',
    '219': 'IN', '224': 'IL', '225': 'LA', '228': 'MS', '231': 'MI', '234': 'OH', '239': 'FL', '240': 'MD',
    '248': 'MI', '251': 'AL', '253': 'WA', '254': 'TX', '256': 'AL', '260': 'IN', '262': 'WI', '267': 'PA',
    '269': 'MI', '270': 'KY', '281': 'TX', '301': 'MD', '302': 'DE', '303': 'CO', '304': 'WV', '305': 'FL',
    '307': 'WY', '309': 'IL', '310': 'CA', '312': 'IL', '313': 'MI', '314': 'MO', '315': 'NY', '316': 'KS',
    '317': 'IN', '319': 'IA', '320': 'MN', '321': 'FL', '323': 'CA', '330': 'OH', '331': 'IL', '334': 'AL',
    '336': 'NC', '337': 'LA', '339': 'MA', '347': 'NY', '351': 'MA', '352': 'FL', '386': 'FL', '401': 'RI',
    '402': 'NE', '404': 'GA', '405': 'OK', '406': 'MT', '407': 'FL', '408': 'CA', '409': 'TX', '410': 'MD',
    '412': 'PA', '413': 'MA', '414': 'WI', '415': 'CA', '419': 'OH', '423': 'TN', '424': 'CA', '425': 'WA',
    '430': 'TX', '432': 'TX', '434': 'VA', '435': 'UT', '440': 'OH', '443': 'MD', '469': 'TX', '470': 'GA',
    '479': 'AR', '480': 'AZ', '484': 'PA', '501': 'AR', '502': 'KY', '503': 'OR', '504': 'LA', '505': 'NM',
    '507': 'MN', '508': 'MA', '509': 'WA', '510': 'CA', '512': 'TX', '513': 'OH', '515': 'IA', '516': 'NY',
    '517': 'MI', '518': 'NY', '520': 'AZ', '530': 'CA', '540': 'VA', '541': 'OR', '559': 'CA', '561': 'FL',
    '562': 'CA', '563': 'IA', '570': 'PA', '571': 'VA', '573': 'MO', '574': 'IN', '585': 'NY', '586': 'MI',
    '602': 'AZ', '603': 'NH', '607': 'NY', '608': 'WI', '609': 'NJ', '610': 'PA', '612': 'MN', '614': 'OH',
    '615': 'TN', '616': 'MI', '617': 'MA', '618': 'IL', '619': 'CA', '620': 'KS', '623': 'AZ', '626': 'CA',
    '630': 'IL', '631': 'NY', '646': 'NY', '650': 'CA', '651': 'MN', '678': 'GA', '682': 'TX', '702': 'NV',
    '703': 'VA', '704': 'NC', '706': 'GA', '707': 'CA', '708': 'IL', '712': 'IA', '713': 'TX', '714': 'CA',
    '715': 'WI', '717': 'PA', '718': 'NY', '719': 'CO', '720': 'CO', '727': 'FL', '732': 'NJ', '734': 'MI',
    '740': 'OH', '757': 'VA', '760': 'CA', '763': 'MN', '770': 'GA', '772': 'FL', '773': 'IL', '774': 'MA',
    '781': 'MA', '785': 'KS', '786': 'FL', '801': 'UT', '802': 'VT', '803': 'SC', '804': 'VA', '805': 'CA',
    '806': 'TX', '808': 'HI', '810': 'MI', '812': 'IN', '813': 'FL', '814': 'PA', '815': 'IL', '816': 'MO',
    '817': 'TX', '818': 'CA', '828': 'NC', '830': 'TX', '831': 'CA', '832': 'TX', '843': 'SC', '845': 'NY',
    '847': 'IL', '848': 'NJ', '850': 'FL', '856': 'NJ', '857': 'MA', '858': 'CA', '859': 'KY', '860': 'CT',
    '863': 'FL', '864': 'SC', '865': 'TN', '870': 'AR', '878': 'PA', '901': 'TN', '903': 'TX', '904': 'FL',
    '908': 'NJ', '909': 'CA', '910': 'NC', '912': 'GA', '913': 'KS', '914': 'NY', '915': 'TX', '916': 'CA',
    '917': 'NY', '918': 'OK', '919': 'NC', '920': 'WI', '925': 'CA', '931': 'TN', '937': 'OH', '940': 'TX',
    '941': 'FL', '949': 'CA', '951': 'CA', '952': 'MN', '954': 'FL', '956': 'TX', '970': 'CO', '971': 'OR',
    '972': 'TX', '973': 'NJ', '978': 'MA', '979': 'TX', '980': 'NC', '985': 'LA', '989': 'MI'
}

def extract_ac(phone_str):
    if not phone_str: return None
    digits = re.sub(r'\D', '', str(phone_str))
    if len(digits) >= 10:
        if len(digits) == 11 and digits.startswith('1'):
            return digits[1:4]
        return digits[:3]
    return None

def run_mass_extraction():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING MASS STATE EXTRACTION & ENRICHMENT ===", flush=True)
    
    last_id = 0
    total_updated = 0
    from_loc = 0
    from_notes = 0
    from_phone = 0
    
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, location, notes, phone
            FROM recruiters
            WHERE recruiter_id > :lid AND (state IS NULL OR state = '')
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        
        if not chunk: break
        
        batch_updates = []
        for r in chunk:
            rid = r['recruiter_id']
            loc = r['location']
            nts = r['notes']
            ph = r['phone']
            
            extracted_state = None
            
            # 1. Try location column (non-strict first, then strict)
            if loc:
                st, _ = extract_state_detailed(loc, strict=False)
                if st:
                    extracted_state = st
                    from_loc += 1
            
            # 2. Try notes column
            if not extracted_state and nts:
                st, _ = extract_state_detailed(nts, strict=False)
                if st:
                    extracted_state = st
                    from_notes += 1
                    
            # 3. Try phone area code
            if not extracted_state and ph:
                ac = extract_ac(ph)
                if ac and ac in NANP_STATE_MAP:
                    extracted_state = NANP_STATE_MAP[ac]
                    from_phone += 1
            
            if extracted_state:
                batch_updates.append({"rid": rid, "st": extracted_state})
        
        if batch_updates:
            for i in range(0, len(batch_updates), 1000):
                sub = batch_updates[i:i+1000]
                db.execute(text("UPDATE recruiters SET state = :st WHERE recruiter_id = :rid"), sub)
            db.commit()
            total_updated += len(batch_updates)
            print(f"Progress: Updated {total_updated:,} states so far... (Last ID: {last_id:,})", flush=True)
            
        last_id = chunk[-1]['recruiter_id']
        
    elapsed = round(time.time() - t0, 2)
    print("\n=======================================================")
    print(f"MASS STATE EXTRACTION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print(f"  - From Location String: {from_loc:,}")
    print(f"  - From Notes / Triangulation: {from_notes:,}")
    print(f"  - From Phone Area Code: {from_phone:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    run_mass_extraction()
