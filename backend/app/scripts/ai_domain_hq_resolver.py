import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from sqlalchemy import text

# AI-Generated Domain to US State HQ Mapping (0 API Credits spent!)
AI_DOMAIN_MAP = {
    '84.51.com': 'OH',
    'edcconsulting.com': 'VA',
    'p3-group.com': 'MI',
    'allcovered.com': 'NJ',
    'umbrex.com': 'NY',
    'getathelas.com': 'CA',
    'cengage.com': 'MA',
    'cellaconsulting.com': 'MD',
    'duolingo.com': 'PA',
    'boyden.com': 'NY',
    'classvaluation.com': 'MI',
    'slonepartners.com': 'FL',
    'bpmcpa.com': 'CA',
    'designindc.com': 'DC',
    'bettsrecruiting.com': 'CA',
    'twilio.com': 'CA',
    'eventbrite.com': 'CA',
    'nike.com': 'OR',
    'doordash.com': 'CA',
    'zoom.us': 'CA',
    'verygood.ventures': 'NY',
    'applause.com': 'MA',
    'wayve.ai': 'CA',
    'gala.games': 'WY',
    'constellation.com': 'MD',
    'elevate.bio': 'MA',
    'superannotate.com': 'CA',
    'cas.org': 'OH',
    'finout.io': 'NY',
    'ionq.co': 'MD',
    'fueled.com': 'NY',
    'wayup.com': 'NY',
    'biworldwide.com': 'MN',
    'gdls.com': 'MI',
    'clear.ml.com': 'NY',
    'uniswap.org': 'NY',
    'fastspring.com': 'CA',
    'modmed.com': 'FL',
    'thedeltacompanies.com': 'TX',
    'techholding.co': 'CA',
    'smxpower.com': 'CA',
    'crusoeenergy.com': 'CO',
    'teamwork.net': 'NJ',
    'assess.com': 'WI',
    '66degrees.com': 'IL',
    'enovis.com': 'DE',
    'daysmart.com': 'MI',
    'coenterprise.com': 'NY',
    'yottaa.com': 'MA',
    'zivaro.com': 'CO',
    'wellsky.com': 'KS',
    'trellance.com': 'FL',
    'iproov.com': 'VA',
    'hippocraticai.com': 'CA',
    'cmsenergy.com': 'MI',
    'synectics.us': 'VA',
    'marconet.com': 'MN',
    'blacksky.com': 'VA',
    'cambridgesemantics.com': 'MA',
    'compozelabs.com': 'MN',
    'isc2.org': 'VA',
    'isotalent.com': 'UT',
    'prescientsolutions.com': 'IL',
    'tytonpartners.com': 'MA',
    'doherty.com': 'MN',
    'auxis.com': 'FL',
    'clearesult.com': 'TX',
    'intrado.com': 'NE',
    'appliedsystems.com': 'IL'
}

def resolve_unknown_domains():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING AI DOMAIN HQ RESOLVER ===", flush=True)
    
    total_updated = 0
    
    # Process updates dynamically based on the dictionary
    for domain, state in AI_DOMAIN_MAP.items():
        query = text("""
            UPDATE recruiters 
            SET state = :st 
            WHERE (state = 'Unknown' OR state IS NULL) 
            AND email ILIKE :domain
        """)
        
        result = db.execute(query, {"st": state, "domain": f"%@{domain}"})
        rows = result.rowcount
        if rows > 0:
            print(f"Mapped {rows} recruiters from {domain} to {state}")
            total_updated += rows
            
    db.commit()
    
    elapsed = round(time.time() - t0, 2)
    print("\n=======================================================")
    print(f"AI DOMAIN HQ RESOLUTION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total Recruiters Backfilled: {total_updated:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    resolve_unknown_domains()
