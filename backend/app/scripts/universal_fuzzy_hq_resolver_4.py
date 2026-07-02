import sys, os, time, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from sqlalchemy import text

EXPANDED_HQ_MAP_4 = {
    'implementation.com': 'MN', 'opsecsecurity': 'PA', 'ipsdb': 'PA', 'humbition': 'NY',
    'airjoule': 'DE', 'jaanhealth': 'NY', 'g2m.ai': 'CA', 'enqubes': 'NJ', 'harperharrison': 'NY',
    'advisiondevelopment': 'CO', 'approfessionals': 'NY', 'caliola': 'CO', 'nucorevision': 'MD',
    'fruitiongroup': 'IL', 'l2rconsulting': 'TX', 'vandh': 'WI', 'amaze-systems': 'IL',
    'asap.us.com': 'GA', 'erg.com': 'MA', 'wavestrong': 'CA', 'rightbalance': 'CA',
    'aspect-consulting': 'PA', 'perrygo': 'MD', 'intelliware': 'MA', 'lrwonline': 'CA',
    'bradfordangalt': 'MO', 'forte.com': 'WI', 'focusga': 'GA', 'londonapproach': 'NY',
    'stealthstartup': 'CA', 'meditech': 'MA', 'semperis': 'NJ', 'firstenergycorp': 'OH',
    'markjamessearch': 'GA', 'tiello': 'CA', 'automationhelpers': 'CO', 'exostalent': 'GA',
    'hyqoo': 'TX', 'surfpci': 'MI', 'irisrecruiting': 'IN', 'hbstaffing': 'CA', 'prgusa': 'PA',
    'idelsoft': 'CA', '9dots': 'CA', 'mass.gov': 'MA', 'teamtorc': 'VA', 'pimco': 'CA',
    'finchloom': 'CA', 'aocwins': 'VA', 'butterball': 'NC', 'dorrean': 'MD', 'assistrx': 'FL',
    'epmainc': 'TX', 'adhoclabs': 'CA', 'technicalstaffingresources': 'DE', 'andela': 'NY',
    'hightrail': 'TX', 'virtasant': 'FL', 'blueorange': 'NY', 'merative': 'MI', 'trmlabs': 'CA',
    'platform-recruitment': 'TX', 'pps.com': 'PA', 'synaptek': 'VA', 'nelsonjobs': 'CA',
    'horizonhospitality': 'KS', 'checkr': 'CA', 'execsallied': 'WA', 'digitalreachagency': 'CA',
    'jamesdavidstaffing': 'CA', 'grantthornton': 'IL', 'nirsense': 'VA', 'clockwork': 'MN',
    'babich': 'TX', 'talsearchgroup': 'FL'
}

def resolve_pass_4():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING EXPANDED FUZZY SUBSTRING HQ RESOLVER PASS 4 ===", flush=True)
    
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
            for kw, st in EXPANDED_HQ_MAP_4.items():
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
    print(f"PASS 4 RESOLUTION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    resolve_pass_4()
