import sys, os, time, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from sqlalchemy import text

# Expanded Substring & Domain HQ Map
EXPANDED_HQ_MAP = {
    'engine.com': 'NY', 'chatsworth': 'CA', 'astrion': 'AL', 'paconsulting': 'NY', 'nationalstaff': 'TX',
    'sequoia': 'CA', 'pax8': 'CO', 'hubspot': 'MA', 'maritz': 'MO', 'altoslabs': 'CA', 'virtustream': 'VA',
    'topsort': 'CA', 'globalsolgroup': 'MI', 'talentohc': 'FL', 'clearspeed': 'CA', 'biotalent': 'MA',
    'grailbio': 'CA', 'navapbc': 'DC', 'jonesnet': 'NC', 'convergeone': 'MN', 'greenlightworldwide': 'GA',
    'bounteous': 'IL', 'blackbox': 'PA', 'axleinfo': 'MD', 'herodigital': 'CA', 'bigbear': 'MD',
    'teamhuber': 'NJ', 'century-group': 'CA', 'xyntek': 'PA', 'stelvio': 'NY', 'somewhere': 'TX',
    'effectual': 'NJ', 'grahamjobs': 'NC', 'hhstechgroup': 'FL', 'availity': 'FL', 'rphonthego': 'IL',
    'islllc': 'CO', 'sledgehammer': 'CA', 'emeraldhs': 'CA', 'culvercareers': 'CA', 'coastalcloud': 'FL',
    'asmr.com': 'DC', 'westinghouse': 'PA', 'digitalglobe': 'CO', 'dpptech': 'CA', 'parthenon': 'MA',
    'drhorton': 'TX', 'avenuecode': 'CA', 'expresspro': 'OK', 'kratosdefense': 'CA', 'careermovement': 'CA',
    'actionet': 'VA', 'flextrades': 'IN', 'srg-us': 'MA', 'feditc': 'MD', 'himaxwell': 'CO',
    'jt4llc': 'NV', 'axiologik': 'MA', 'phdata': 'MN', 'catapultsystems': 'TX', 'sentinelone': 'CA',
    'dataannotation': 'NY', 'disqo': 'CA', 'medpace': 'OH', 'northboundsearch': 'NY', 'thinkconsulting': 'MD',
    'calamp': 'CA', 'dsdinc': 'MA', 'syndicatebleu': 'CA', 'gotyto': 'VA', 'sada.com': 'CA',
    'stantonchase': 'MD', 'workbetternow': 'NY', 'spauldingridge': 'IL', 'oculusgroup': 'CA', 'inl.gov': 'ID',
    'coforge': 'NJ', 'diversifiedus': 'NJ', 'wsp.com': 'NY', 'hugeinc': 'NY', '4cornerresources': 'FL',
    '4 corner resources': 'FL', 'elitetecherie': 'PA', 'hrpals': 'CA', 'jmfamily': 'FL', 'lloydstaffing': 'NY',
    'newburypartners': 'TX', 'docusign': 'CA', 'cotiviti': 'GA', 'swissre': 'NY', 'tatum': 'GA',
    'fedex': 'TN', 'teksystem': 'MD', 'github': 'CA', 'covermymeds': 'OH', 'trinitylifesciences': 'MA',
    'meetlifesciences': 'NY', 'worldpay': 'OH', 'nakupuna': 'VA', 'gitlab': 'CA', 'visa.com': 'CA',
    'lrshealthcare': 'NE', 'ipghealth': 'NY', 'sagility': 'CO', 'corestaff': 'TX', 'hendersonscott': 'NY',
    'fasttek': 'MI', 'onenorth': 'IL', 'thrivenextgen': 'MA', 'hackajob': 'NY', 'analysisgroup': 'MA',
    'campusworks': 'FL', 'carahsoft': 'VA', 'lightspeed': 'TX', 'ecstech': 'VA', 'geico': 'MD',
    'latentview': 'NJ', 'bullhorn': 'MA', 'fool.com': 'VA', 'parkplace': 'OH', 'memoryblue': 'VA',
    'avispl': 'FL', 'quantumworld': 'CA', 'sikich': 'IL', 'cpsjobs': 'IL', 'steampunk': 'VA',
    'veracity': 'KS', 'jacksontherapy': 'FL', 'planetgroup': 'IL', 'abeam': 'TX', 'gdhinc': 'OK',
    'hackett': 'FL', 'inspyr': 'FL', 'strategicstaffing': 'MI', 'oliverwyman': 'NY', 'oliverwaymen': 'NY',
    'expedia': 'WA', 'expleo': 'MI', 'cherryroad': 'NJ', 'credera': 'TX', 'barrington': 'NC',
    'indegene': 'NJ', 'barton': 'MA', 'levelup': 'TX', 'heidrick': 'IL', 'nttdata': 'TX',
    'ghrhealthcare': 'PA', 'salesforce': 'CA', 'ensono': 'IL', 'haemonetics': 'MA', 'collaborative': 'VA',
    'spencerstuart': 'IL', 'manpower': 'WI', 'rippling': 'CA', 'qtsdata': 'KS', 'beaconhill': 'MA',
    'truesearch': 'NJ', 'atrium': 'NY', 'jsheld': 'NY', 'insperity': 'TX', 'onedigital': 'GA',
    'saluteinc': 'MI', 'levelaccess': 'VA', 'netapp': 'CA', 'coquina': 'TX', 'nordic': 'WI',
    'flexcare': 'CA', 'novonordisk': 'NJ', 'kearney': 'IL', 'vxi.com': 'CA', 'techrg': 'CA',
    'ibex': 'DC', 'raymondjames': 'FL', 'merkle': 'MD', 'civicplus': 'KS', 'csihealthcare': 'FL',
    'bswift': 'IL', 'dhrglobal': 'IL', 'nelnet': 'NE', 'sisrec': 'GA', 'viderity': 'FL', 'tmsrecruiting': 'MO',
    'mickleygroup': 'TX', '24seventalent': 'NY', 'daviesgroup': 'TN', 'sionic': 'NY', 'declericogroup': 'PA',
    'schroedergroup': 'TX', 'oxfordcorp': 'MA', 'randstaddigital': 'GA', 'akkodis': 'FL', 'cerecore': 'TN',
    'cooksys': 'TN', 'eclaro': 'NY', 'idr-inc': 'GA', 'kforce': 'FL', 'rcmt.com': 'NJ', 'rscsolutions': 'NY',
    'aerotek': 'MD', 'allegis': 'MD', 'roberthalf': 'CA', 'insightglobal': 'GA',
    'apexsystems': 'VA', 'kellyservices': 'MI', 'adecco': 'FL', 'collabera': 'NJ', 'workwithglee': 'AL',
    'consultinq': 'FL', 'consultingsolutions': 'FL', 'automus': 'MA', 'raininqvirtue': 'IL', 'rainingvirtue': 'IL',
    'hyperec': 'TX', 'rockcrest': 'MD', 'askachiefofstaff': 'CA', 'entrecs': 'VA', 'sourceowls': 'NY',
    'kognitiv': 'CA', '189banaco': 'NY'
}

def resolve_expanded_fuzzy():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING EXPANDED FUZZY SUBSTRING HQ RESOLVER ===", flush=True)
    
    last_id = 0
    total_updated = 0
    
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, email, notes
            FROM recruiters
            WHERE recruiter_id > :lid AND (state IS NULL OR state = '')
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        if not chunk: break
        
        batch_updates = []
        for r in chunk:
            rid = r['recruiter_id']
            em = (r['email'] or '').lower()
            nts = (r['notes'] or '').lower()
            search_str = em + ' ' + nts
            
            chosen_state = None
            for kw, st in EXPANDED_HQ_MAP.items():
                if kw in search_str:
                    chosen_state = st
                    break
                
            if chosen_state:
                batch_updates.append({"rid": rid, "st": chosen_state})
                
        if batch_updates:
            for i in range(0, len(batch_updates), 1000):
                sub = batch_updates[i:i+1000]
                db.execute(text("UPDATE recruiters SET state = :st WHERE recruiter_id = :rid"), sub)
            db.commit()
            total_updated += len(batch_updates)
            print(f"Progress: Updated {total_updated:,} states... (Last ID: {last_id:,})", flush=True)
            
        last_id = chunk[-1]['recruiter_id']
        
    elapsed = round(time.time() - t0, 2)
    print("\n=======================================================")
    print(f"EXPANDED FUZZY RESOLUTION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    resolve_expanded_fuzzy()
