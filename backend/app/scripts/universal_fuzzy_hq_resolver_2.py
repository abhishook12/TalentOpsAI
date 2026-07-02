import sys, os, time, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from sqlalchemy import text

EXPANDED_HQ_MAP_2 = {
    'whitlock': 'VA', 'gpstrategies': 'MD', 'actfore': 'CA', 'collectiveinsights': 'GA',
    'sdqqroup': 'FL', 'sdqgroup': 'FL', 'blhtech': 'MD', 'yer.com': 'GA', 'technium': 'MA',
    'xlpro': 'TX', 'hssi.com': 'VA', 'j29inc': 'MD', 'sunqardas': 'PA', 'sungardas': 'PA',
    'rinvio': 'TX', 'americaninternationalfoods': 'MI', 'abilegroup': 'MD', 'cubiq': 'MA',
    'atlasprofessionals': 'TX', 'forpeople': 'CA', 'thejobsquad': 'MN', 'caracorp': 'IL',
    'threelink': 'TX', 'inabia': 'WA', 'e360': 'CA', 'entisys360': 'CA', 'tuvli': 'VA',
    'dominotech': 'PA', 'anaghtech': 'NJ', 'artandlogic': 'CA', 'spartansolutions': 'TX',
    'redballoon': 'ID', 'claritisolutions': 'VA', 'consensus': 'UT', 'thinkingbigpicture': 'GA',
    'reisystems': 'VA', 'core4ce': 'VA', 'op.tech': 'CA', 'altuscc': 'TX', 'kellyocg': 'MI',
    'fastly': 'CA', 'astrobotic': 'PA', 'joinhandshake': 'CA', 'zonatherm': 'IL', 'centroid': 'MI',
    'capspire': 'OK', 'twu.edu': 'TX', 'gettruss': 'CA', 'bbh.com': 'NY', 'htijobs': 'SC',
    'sourcegroupinternational': 'NY', 'veteransemployment': 'FL', 'jacobsononline': 'IL',
    'detegohealth': 'UT', 'cariad': 'VA', 'accordance': 'CA', 'whitmanpartners': 'OR',
    'slingshotconnections': 'CA', 'cef.inc': 'TX', 'encora': 'AZ', 'unitysearch': 'TX',
    'enterone': 'NC', 'creativepeopleinc': 'FL', 'vectorsynergy': 'FL', 'vercel': 'CA',
    'nlx.ai': 'NY', 'thinkbrg': 'CA', 'hexure': 'CO', 'hunterphilips': 'MA', 'metrostar': 'VA',
    'finatal': 'NY', 'bridgergrp': 'MI', 'aifund': 'CA', 'efor-group': 'PA', 'apolis': 'CA',
    'consultingpoint': 'NY', 'elastify': 'IL', 'aandbtalent': 'TX', 'glowgfs': 'TX',
    'milliman': 'WA', 'wavetalent': 'CA', 'farohealth': 'CA', 'sstaffing': 'IL', 'bcg.com': 'MA',
    'kgstechnology': 'GA', 'docker': 'CA', 'ptaginc': 'TX', 'saltboxmgmt': 'GA', 'wtalent': 'NY',
    'dynamicssolutions': 'VA', 'compqsoft': 'TX', 'credohealth': 'CO', 'audacy': 'PA',
    'headfarmer': 'AZ', 'fivepack': 'TX'
}

def resolve_pass_2():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING EXPANDED FUZZY SUBSTRING HQ RESOLVER PASS 2 ===", flush=True)
    
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
            for kw, st in EXPANDED_HQ_MAP_2.items():
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
    print(f"PASS 2 RESOLUTION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    resolve_pass_2()
