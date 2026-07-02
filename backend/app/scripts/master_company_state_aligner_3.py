import sys, os, time, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from sqlalchemy import text

CANONICAL_COMPANIES_3 = {
    'beaconhillsg.com': {'id': 26993, 'name': 'Beacon Hill Staffing Group', 'hq': 'MA'},
    'optomi.com': {'id': 1404, 'name': 'Optomi', 'hq': 'GA'},
    'theintersectgroup.com': {'id': 67013, 'name': 'The Intersect Group', 'hq': 'GA'},
    'mondo.com': {'id': 2672, 'name': 'Mondo', 'hq': 'NY'},
    'lasallenetwork.com': {'id': 43202, 'name': 'LaSalle Network', 'hq': 'IL'},
    'procomservices.com': {'id': 9, 'name': 'Procom', 'hq': 'NC'},
    'nigelfrank.com': {'id': 41815, 'name': 'Nigel Frank International', 'hq': 'NY'},
    'talentbridge.com': {'id': 198, 'name': 'TalentBridge', 'hq': 'NC'},
    'greenkeyllc.com': {'id': 60281, 'name': 'Green Key Resources', 'hq': 'NY'},
    'stevendouglas.com': {'id': 1388, 'name': 'StevenDouglas', 'hq': 'FL'},
    'eliassen.com': {'id': 61023, 'name': 'Eliassen Group', 'hq': 'MA'},
    'akkodisgroup.com': {'id': 25552, 'name': 'Akkodis (Modis)', 'hq': 'FL'},
    'ultimatestaffing.com': {'id': 61638, 'name': 'Ultimate Staffing', 'hq': 'CA'},
    'bcforward.com': {'id': 38097, 'name': 'BCforward', 'hq': 'IN'},
    'cdw.com': {'id': 857, 'name': 'CDW', 'hq': 'IL'},
    'opensystemstech.com': {'id': 1226, 'name': 'Open Systems Technologies', 'hq': 'NY'},
    'turnberry solutions.com': {'id': 37651, 'name': 'Turnberry Solutions', 'hq': 'PA'},
    'guidehouse.com': {'id': 28285, 'name': 'Guidehouse', 'hq': 'VA'},
    'cybercoders.com': {'id': 42995, 'name': 'CyberCoders', 'hq': 'CA'},
    'randstadtechnologies.com': {'id': 50849, 'name': 'Randstad', 'hq': 'GA'},
    'mitchellmartin.com': {'id': 32549, 'name': 'Mitchell Martin', 'hq': 'NY'},
    'atriumstaff.com': {'id': 61920, 'name': 'Atrium', 'hq': 'NY'},
    'strategic staffing solutions .com': {'id': 41709, 'name': 'Strategic Staffing Solutions', 'hq': 'MI'},
    'bachrachgroup.com': {'id': 332, 'name': 'The Bachrach Group', 'hq': 'NY'},
    'elwoodstaffing.com': {'id': 297, 'name': 'Elwood Staffing', 'hq': 'IN'},
    'csicompanies.com': {'id': 61902, 'name': 'The CSI Companies', 'hq': 'FL'},
    'ettaingroup.com': {'id': 43539, 'name': 'Experis', 'hq': 'WI'},
    'matlensilver.com': {'id': 41705, 'name': 'Matlen Silver', 'hq': 'NJ'},
    'unisys.com': {'id': 60729, 'name': 'Unisys', 'hq': 'PA'},
    'peopleready.com': {'id': 50613, 'name': 'PeopleReady', 'hq': 'WA'},
    'cbts.com': {'id': 41902, 'name': 'CBTS', 'hq': 'OH'},
    'gdhinc.com': {'id': 29217, 'name': 'GDH Consulting', 'hq': 'OK'}
}

NANP_STATE_MAP = {
    "201": "NJ", "202": "DC", "203": "CT", "205": "AL", "206": "WA", "207": "ME", "208": "ID", "209": "CA",
    "210": "TX", "212": "NY", "213": "CA", "214": "TX", "215": "PA", "216": "OH", "217": "IL", "218": "MN",
    "219": "IN", "224": "IL", "225": "LA", "228": "MS", "229": "GA", "231": "MI", "234": "OH", "239": "FL",
    "240": "MD", "248": "MI", "251": "AL", "252": "NC", "253": "WA", "254": "TX", "256": "AL", "260": "IN",
    "262": "WI", "267": "PA", "269": "MI", "270": "KY", "272": "PA", "276": "VA", "281": "TX", "301": "MD",
    "302": "DE", "303": "CO", "304": "WV", "305": "FL", "307": "WY", "308": "NE", "309": "IL", "310": "CA",
    "312": "IL", "313": "MI", "314": "MO", "315": "NY", "316": "KS", "317": "IN", "318": "LA", "319": "IA",
    "320": "MN", "321": "FL", "323": "CA", "325": "TX", "330": "OH", "331": "IL", "334": "AL", "336": "NC",
    "337": "LA", "339": "MA", "346": "TX", "347": "NY", "351": "MA", "352": "FL", "360": "WA", "361": "TX",
    "386": "FL", "401": "RI", "402": "NE", "404": "GA", "405": "OK", "406": "MT", "407": "FL", "408": "CA",
    "409": "TX", "410": "MD", "412": "PA", "413": "MA", "414": "WI", "415": "CA", "417": "MO", "419": "OH",
    "423": "TN", "424": "CA", "425": "WA", "430": "TX", "432": "TX", "434": "VA", "435": "UT", "440": "OH",
    "443": "MD", "458": "OR", "469": "TX", "470": "GA", "475": "CT", "478": "GA", "479": "AR", "480": "AZ",
    "484": "PA", "501": "AR", "502": "KY", "503": "OR", "504": "LA", "505": "NM", "507": "MN", "508": "MA",
    "509": "WA", "510": "CA", "512": "TX", "513": "OH", "515": "IA", "516": "NY", "517": "MI", "518": "NY",
    "520": "AZ", "530": "CA", "540": "VA", "541": "OR", "551": "NJ", "559": "CA", "561": "FL", "562": "CA",
    "563": "IA", "567": "OH", "570": "PA", "571": "VA", "573": "MO", "574": "IN", "575": "NM", "580": "OK",
    "585": "NY", "586": "MI", "601": "MS", "602": "AZ", "603": "NH", "605": "SD", "606": "KY", "607": "NY",
    "608": "WI", "609": "NJ", "610": "PA", "612": "MN", "614": "OH", "615": "TN", "616": "MI", "617": "MA",
    "618": "IL", "619": "CA", "620": "KS", "623": "AZ", "626": "CA", "630": "IL", "631": "NY", "636": "MO",
    "641": "IA", "646": "NY", "650": "CA", "651": "MN", "660": "MO", "661": "CA", "662": "MS", "678": "GA",
    "682": "TX", "701": "ND", "702": "NV", "703": "VA", "704": "NC", "706": "GA", "707": "CA", "708": "IL",
    "712": "IA", "713": "TX", "714": "CA", "715": "WI", "716": "NY", "717": "PA", "718": "NY", "719": "CO",
    "720": "CO", "724": "PA", "727": "FL", "731": "TN", "732": "NJ", "734": "MI", "740": "OH", "757": "VA",
    "760": "CA", "762": "GA", "763": "MN", "765": "IN", "770": "GA", "772": "FL", "773": "IL", "774": "MA",
    "775": "NV", "781": "MA", "785": "KS", "786": "FL", "801": "UT", "802": "VT", "803": "SC", "804": "VA",
    "805": "CA", "806": "TX", "808": "HI", "810": "MI", "812": "IN", "813": "FL", "814": "PA", "815": "IL",
    "816": "MO", "817": "TX", "818": "CA", "828": "NC", "830": "TX", "831": "CA", "832": "TX", "843": "SC",
    "845": "NY", "847": "IL", "848": "NJ", "850": "FL", "856": "NJ", "857": "MA", "858": "CA", "859": "KY",
    "860": "CT", "862": "NJ", "863": "FL", "864": "SC", "865": "TN", "870": "AR", "878": "PA", "901": "TN",
    "903": "TX", "904": "FL", "906": "MI", "907": "AK", "908": "NJ", "909": "CA", "910": "NC", "912": "GA",
    "913": "KS", "914": "NY", "915": "TX", "916": "CA", "917": "NY", "918": "OK", "919": "NC", "920": "WI",
    "925": "CA", "928": "AZ", "931": "TN", "936": "TX", "937": "OH", "940": "TX", "941": "FL", "947": "MI",
    "949": "CA", "951": "CA", "952": "MN", "954": "FL", "956": "TX", "970": "CO", "971": "OR", "972": "TX",
    "973": "NJ", "978": "MA", "979": "TX", "980": "NC", "985": "LA", "989": "MI"
}

CITY_STATE_MAP = {
    'atlanta': 'GA', 'new york': 'NY', 'nyc': 'NY', 'chicago': 'IL', 'dallas': 'TX', 'houston': 'TX',
    'austin': 'TX', 'charlotte': 'NC', 'raleigh': 'NC', 'tampa': 'FL', 'miami': 'FL', 'orlando': 'FL',
    'jacksonville': 'FL', 'boston': 'MA', 'seattle': 'WA', 'denver': 'CO', 'phoenix': 'AZ', 'scottsdale': 'AZ',
    'los angeles': 'CA', 'san francisco': 'CA', 'san diego': 'CA', 'sanjose': 'CA', 'sacramento': 'CA',
    'minneapolis': 'MN', 'detroit': 'MI', 'philadelphia': 'PA', 'pittsburgh': 'PA', 'baltimore': 'MD',
    'washington dc': 'DC', 'richmond': 'VA', 'mclean': 'VA', 'reston': 'VA', 'columbus': 'OH',
    'cleveland': 'OH', 'cincinnati': 'OH', 'indianapolis': 'IN', 'milwaukee': 'WI', 'madison': 'WI',
    'nashville': 'TN', 'st louis': 'MO', 'st. louis': 'MO', 'kansas city': 'MO', 'louisville': 'KY',
    'salt lake city': 'UT', 'las vegas': 'NV', 'portland': 'OR'
}

def extract_phone_state(phone):
    if not phone: return None
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 10 and digits[:3] in NANP_STATE_MAP:
        return NANP_STATE_MAP[digits[:3]]
    elif len(digits) == 11 and digits.startswith('1') and digits[1:4] in NANP_STATE_MAP:
        return NANP_STATE_MAP[digits[1:4]]
    return None

def extract_notes_state(text_str):
    if not text_str: return None
    t = text_str.lower()
    for city, st in CITY_STATE_MAP.items():
        if city in t:
            return st
    return None

def align_companies_and_states_3():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING MASTER COMPANY & STATE ALIGNMENT PIPELINE BATCH 3 ===", flush=True)
    
    unique_canonical = {}
    for dom, info in CANONICAL_COMPANIES_3.items():
        cid = info['id']
        cname = info['name']
        unique_canonical[cid] = cname
        
    for cid, cname in unique_canonical.items():
        db.execute(text("UPDATE companies SET company_name = :name WHERE company_id = :id"), {"name": cname, "id": cid})
    db.commit()
    print(f"Updated {len(unique_canonical)} canonical company records.", flush=True)
    
    last_id = 0
    total_aligned_company = 0
    total_aligned_state = 0
    
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, email, notes, location, phone, company_id, state
            FROM recruiters
            WHERE recruiter_id > :lid
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        if not chunk: break
        
        batch_company_updates = []
        batch_state_updates = []
        
        for r in chunk:
            rid = r['recruiter_id']
            em = (r['email'] or '').lower().strip()
            dom = em.split('@')[-1] if '@' in em else ''
            nts = str(r['notes'] or '') + ' ' + str(r['location'] or '')
            curr_cid = r['company_id']
            curr_st = r['state']
            
            target_info = None
            if dom in CANONICAL_COMPANIES_3:
                target_info = CANONICAL_COMPANIES_3[dom]
            else:
                nts_lower = nts.lower()
                for d_key, c_info in CANONICAL_COMPANIES_3.items():
                    if c_info['name'].lower() in nts_lower:
                        target_info = c_info
                        break
                        
            if target_info and curr_cid != target_info['id']:
                batch_company_updates.append({"rid": rid, "cid": target_info['id']})
                
            if (curr_st == 'US' or not curr_st) and target_info:
                new_st = extract_phone_state(r['phone'])
                if not new_st:
                    new_st = extract_notes_state(nts)
                if not new_st:
                    new_st = target_info['hq']
                    
                if new_st and new_st != curr_st:
                    batch_state_updates.append({"rid": rid, "st": new_st})
                    
        if batch_company_updates:
            for i in range(0, len(batch_company_updates), 1000):
                sub = batch_company_updates[i:i+1000]
                db.execute(text("UPDATE recruiters SET company_id = :cid WHERE recruiter_id = :rid"), sub)
            db.commit()
            total_aligned_company += len(batch_company_updates)
            
        if batch_state_updates:
            for i in range(0, len(batch_state_updates), 1000):
                sub = batch_state_updates[i:i+1000]
                db.execute(text("UPDATE recruiters SET state = :st WHERE recruiter_id = :rid"), sub)
            db.commit()
            total_aligned_state += len(batch_state_updates)
            
        print(f"Progress: Aligned {total_aligned_company:,} company IDs | Disambiguated {total_aligned_state:,} states... (Last ID: {last_id:,})", flush=True)
        last_id = chunk[-1]['recruiter_id']
        
    elapsed = round(time.time() - t0, 2)
    print("\n=======================================================")
    print(f"BATCH 3 ALIGNMENT COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total Recruiter Companies Aligned: {total_aligned_company:,}")
    print(f"Total Recruiter States Disambiguated: {total_aligned_state:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    align_companies_and_states_3()
