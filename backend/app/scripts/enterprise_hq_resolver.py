import sys, os, time, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from sqlalchemy import text

# Massive dictionary of corporate & staffing domains to their US State HQ / main recruiting center
DOMAIN_HQ_MAP = {
    'thehackettgroup.com': 'FL',
    'inspyr solutions.com': 'FL',
    'inspyrsolutions.com': 'FL',
    'strategic staffing solutions .com': 'MI',
    'strategicstaffingsolutions.com': 'MI',
    's3.com': 'MI',
    'oliverwaymen.com': 'NY',
    'oliverwyman.com': 'NY',
    'expediagroup.com': 'WA',
    'expedia.com': 'WA',
    'expleogroup.com': 'MI',
    'cherryroad.com': 'NJ',
    'credera.com': 'TX',
    'barringtonjames.com': 'NC',
    'indegene.com': 'NJ',
    'bartonassociates.com': 'MA',
    'leveluphcs.com': 'TX',
    'heidrick.com': 'IL',
    'global.ntt': 'NY',
    'nttdata.com': 'TX',
    'ghrhealthcare.com': 'PA',
    'force.com': 'CA',
    'salesforce.com': 'CA',
    'ensono.com': 'IL',
    'haemonetics.com': 'MA',
    'collaborativesolutions.com': 'VA',
    'spencerstuart.com': 'IL',
    'right.com': 'WI',
    'manpowergroup.com': 'WI',
    'rippling.com': 'CA',
    'qtsdatacenters.com': 'KS',
    'bhsg.cm': 'MA',
    'beaconhillstaffing.com': 'MA',
    'truesearch.com': 'NJ',
    'atriumglobal.com': 'NY',
    'jsheld.com': 'NY',
    'insperity.com': 'TX',
    'onedigital.com': 'GA',
    'saluteinc.com': 'MI',
    'levelaccess.com': 'VA',
    'netapp.com': 'CA',
    'coquinasystems.com': 'TX',
    'nordicwi.com': 'WI',
    'nordicglobal.com': 'WI',
    'flexcarestaff.com': 'CA',
    'novonordisk.com': 'NJ',
    'kearney.com': 'IL',
    'groupo.com': 'IL',
    'vxi.com': 'CA',
    'techrg.com': 'CA',
    'ibexglobal.com': 'DC',
    'raymondjames.com': 'FL',
    'merkleinc.com': 'MD',
    'aspirepartnersusa.com': 'GA',
    'civicplus.com': 'KS',
    'hp.com': 'CA',
    'csihealthcareit.com': 'FL',
    'aberdeenadv.com': 'FL',
    'bswift com': 'IL',
    'bswift.com': 'IL',
    'nexergroup.com': 'MI',
    'forsythbarnes.com': 'NY',
    'sbconsulting.com': 'TX',
    'dhrglobal.com': 'IL',
    'whisker.com': 'MI',
    'results-cx.com': 'FL',
    'auxosolutions.io': 'MI',
    'nelnet.net': 'NE',
    'nelnet.com': 'NE',
    'sisrec.com': 'GA',
    'viderity.com': 'FL',
    'tmsrecruiting.com': 'MO',
    'themickleygroup.com': 'TX',
    '24 seventalent.com': 'NY',
    '24seventalent.com': 'NY',
    'daviesgroup.com': 'TN',
    'sionic.com': 'NY',
    'thedeclericogroup.com': 'PA',
    'theschroedergroup.com': 'TX',
    'oxfordcorp.com': 'MA',
    'randstaddigital.com': 'GA',
    'randstadusa.com': 'GA',
    'akkodis.com': 'FL',
    'cerecore.net': 'TN',
    'cooksys.com': 'TN',
    'eclaro.com': 'NY',
    'idr-inc.com': 'GA',
    'kforce.com': 'FL',
    'rcmt.com': 'NJ',
    'rscsolutions.com': 'NY',
    'teksystems.com': 'MD',
    'aerotek.com': 'MD',
    'allegisgroup.com': 'MD',
    'roberthalf.com': 'CA',
    'insightglobal.com': 'GA',
    'apexsystems.com': 'VA',
    'kellyservices.com': 'MI',
    'adecco.com': 'FL',
    'collabera.com': 'NJ'
}

def resolve_enterprise_hq():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING ENTERPRISE HQ & CLEAN DOMAIN RESOLVER ===", flush=True)
    
    last_id = 0
    total_updated = 0
    
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, email
            FROM recruiters
            WHERE recruiter_id > :lid AND (state IS NULL OR state = '')
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        if not chunk: break
        
        batch_updates = []
        for r in chunk:
            rid = r['recruiter_id']
            em = (r['email'] or '').lower().strip()
            if not em or '@' not in em: continue
            
            dom = em.split('@')[-1].strip()
            clean_dom = dom.replace(' ', '')
            
            chosen_state = None
            if dom in DOMAIN_HQ_MAP:
                chosen_state = DOMAIN_HQ_MAP[dom]
            elif clean_dom in DOMAIN_HQ_MAP:
                chosen_state = DOMAIN_HQ_MAP[clean_dom]
                
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
    print(f"ENTERPRISE HQ RESOLUTION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    resolve_enterprise_hq()
