#!/usr/bin/env python
"""
Comprehensive Company Location Recovery Engine
==============================================
Fixes the Directory page "Location not listed" problem by:
1. Inferring company HQ location from the majority state of its recruiters
2. Mapping well-known staffing companies to their real HQ locations
3. Backfilling recruiter states from their company's newly-set location
"""
import sqlite3
import time
from collections import Counter

DB_PATH = 'dev.db'

# Known HQ locations for major staffing/recruiting firms
KNOWN_HQ = {
    'roberthalf': 'Menlo Park, CA',
    'robert half': 'Menlo Park, CA',
    'insightglobal': 'Atlanta, GA',
    'insight global': 'Atlanta, GA',
    'teksystems': 'Hanover, MD',
    'tek systems': 'Hanover, MD',
    'manpower': 'Milwaukee, WI',
    'manpowergroup': 'Milwaukee, WI',
    'vaco': 'Brentwood, TN',
    'beaconhillstaffing': 'Boston, MA',
    'beacon hill staffing': 'Boston, MA',
    'beaconhill': 'Boston, MA',
    'experis': 'Milwaukee, WI',
    'kforce': 'Tampa, FL',
    'randstadusa': 'Atlanta, GA',
    'randstad': 'Atlanta, GA',
    'brooksource': 'Indianapolis, IN',
    'aerotek': 'Hanover, MD',
    'judge': 'Wayne, PA',
    'the judge group': 'Wayne, PA',
    'kornferry': 'Los Angeles, CA',
    'korn ferry': 'Los Angeles, CA',
    'lhh': 'Zurich, Switzerland',
    'akkodis': 'Paris, France',
    'ahead': 'Chicago, IL',
    'hcl': 'Noida, India',
    'hcltech': 'Noida, India',
    'publicissapient': 'New York, NY',
    'publicis sapient': 'New York, NY',
    'kellyservices': 'Troy, MI',
    'kelly services': 'Troy, MI',
    'kelly': 'Troy, MI',
    'optomi': 'Atlanta, GA',
    'morganstanley': 'New York, NY',
    'morgan stanley': 'New York, NY',
    'walmart': 'Bentonville, AR',
    'crosscountry': 'Boca Raton, FL',
    'cross country': 'Boca Raton, FL',
    'teemagroup': 'Irvine, CA',
    'teema': 'Irvine, CA',
    'actalentservices': 'Hanover, MD',
    'actalentsservices': 'Hanover, MD',
    'actalent': 'Hanover, MD',
    'jobot': 'Irvine, CA',
    'hays': 'London, UK',
    'adecco': 'Zurich, Switzerland',
    'spherion': 'Atlanta, GA',
    'citigroup': 'New York, NY',
    'citi': 'New York, NY',
    'deloitte': 'London, UK',
    'pwc': 'London, UK',
    'pricewaterhousecoopers': 'London, UK',
    'ey': 'London, UK',
    'ernst young': 'London, UK',
    'accenture': 'Dublin, Ireland',
    'cognizant': 'Teaneck, NJ',
    'infosys': 'Bengaluru, India',
    'wipro': 'Bengaluru, India',
    'tata': 'Mumbai, India',
    'tcs': 'Mumbai, India',
    'capgemini': 'Paris, France',
    'google': 'Mountain View, CA',
    'amazon': 'Seattle, WA',
    'microsoft': 'Redmond, WA',
    'meta': 'Menlo Park, CA',
    'facebook': 'Menlo Park, CA',
    'apple': 'Cupertino, CA',
    'netflix': 'Los Gatos, CA',
    'salesforce': 'San Francisco, CA',
    'oracle': 'Austin, TX',
    'ibm': 'Armonk, NY',
    'dell': 'Round Rock, TX',
    'hp': 'Palo Alto, CA',
    'cisco': 'San Jose, CA',
    'intel': 'Santa Clara, CA',
    'nvidia': 'Santa Clara, CA',
    'adobe': 'San Jose, CA',
    'vmware': 'Palo Alto, CA',
    'servicenow': 'Santa Clara, CA',
    'workday': 'Pleasanton, CA',
    'uber': 'San Francisco, CA',
    'lyft': 'San Francisco, CA',
    'airbnb': 'San Francisco, CA',
    'stripe': 'San Francisco, CA',
    'square': 'San Francisco, CA',
    'paypal': 'San Jose, CA',
    'intuit': 'Mountain View, CA',
    'zoom': 'San Jose, CA',
    'slack': 'San Francisco, CA',
    'twitter': 'San Francisco, CA',
    'snap': 'Santa Monica, CA',
    'pinterest': 'San Francisco, CA',
    'linkedin': 'Sunnyvale, CA',
    'jpmorgan': 'New York, NY',
    'jpmorganchase': 'New York, NY',
    'bankofamerica': 'Charlotte, NC',
    'bank of america': 'Charlotte, NC',
    'wellsfargo': 'San Francisco, CA',
    'wells fargo': 'San Francisco, CA',
    'goldmansachs': 'New York, NY',
    'goldman sachs': 'New York, NY',
    'htcinc': 'Atlanta, GA',
    'cybercoders': 'Irvine, CA',
    'cybersearch': 'Atlanta, GA',
    'staffing solutions enterprises': 'Independence, OH',
    'creative circle': 'Los Angeles, CA',
    'adeccousa': 'Jacksonville, FL',
    'matrixresources': 'Atlanta, GA',
    'matrix resources': 'Atlanta, GA',
    'motionrecruitment': 'New York, NY',
    'motion recruitment': 'New York, NY',
    'michaelpage': 'New York, NY',
    'michael page': 'New York, NY',
    'heidrichandstruggles': 'Chicago, IL',
    'heidrick': 'Chicago, IL',
    'spencerstuart': 'Chicago, IL',
    'spencer stuart': 'Chicago, IL',
    'russellreynolds': 'New York, NY',
    'russell reynolds': 'New York, NY',
    'egonzehnder': 'Zurich, Switzerland',
    'egon zehnder': 'Zurich, Switzerland',
}

# State abbreviation extraction from location strings
STATE_MAP = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
}

def extract_state_from_location(loc):
    """Extract 2-letter state code from a location string like 'Menlo Park, CA'"""
    if not loc:
        return None
    parts = loc.strip().split(',')
    if len(parts) >= 2:
        state_part = parts[-1].strip().upper()
        if state_part in STATE_MAP:
            return state_part
    return None


def run():
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print(f"[{time.strftime('%X')}] === COMPANY LOCATION RECOVERY ENGINE ===")
    print()

    # ─── PHASE 1: Known HQ Mapping ───
    print(f"[{time.strftime('%X')}] Phase 1: Mapping known company HQs...")
    companies = c.execute("SELECT company_id, company_name FROM companies WHERE location IS NULL OR location = ''").fetchall()
    
    known_updates = []
    for comp in companies:
        cid = comp['company_id']
        name = (comp['company_name'] or '').strip()
        normalized = name.lower().replace(' ', '').replace('-', '').replace('_', '').replace('.', '')
        
        if normalized in KNOWN_HQ:
            known_updates.append((KNOWN_HQ[normalized], cid))
    
    if known_updates:
        c.executemany("UPDATE companies SET location = ? WHERE company_id = ?", known_updates)
        conn.commit()
    print(f"  -> Mapped {len(known_updates)} companies from known HQ database")

    # ─── PHASE 2: Infer from Recruiter Majority State ───
    print(f"[{time.strftime('%X')}] Phase 2: Inferring HQ from recruiter state density...")
    
    still_missing = c.execute("SELECT company_id, company_name FROM companies WHERE location IS NULL OR location = ''").fetchall()
    print(f"  -> {len(still_missing)} companies still need locations")
    
    inferred = 0
    batch = []
    for comp in still_missing:
        cid = comp['company_id']
        # Get state distribution for this company's recruiters
        states = c.execute("""
            SELECT state, COUNT(*) as cnt 
            FROM recruiters 
            WHERE company_id = ? AND state IS NOT NULL AND state != ''
            GROUP BY state ORDER BY cnt DESC LIMIT 1
        """, (cid,)).fetchone()
        
        if states and states['cnt'] >= 1:
            majority_state = states['state']
            # Try to get a city too from the recruiter locations
            city_row = c.execute("""
                SELECT location FROM recruiters
                WHERE company_id = ? AND state = ? AND location IS NOT NULL AND location != ''
                LIMIT 1
            """, (cid, majority_state)).fetchone()
            
            if city_row and city_row['location']:
                loc = city_row['location']
            else:
                loc = majority_state  # Just use state abbreviation
            
            batch.append((loc, cid))
            inferred += 1
    
    if batch:
        c.executemany("UPDATE companies SET location = ? WHERE company_id = ?", batch)
        conn.commit()
    print(f"  -> Inferred locations for {inferred} companies from recruiter data")

    # ─── PHASE 3: Backfill recruiter states from company location ───
    print(f"[{time.strftime('%X')}] Phase 3: Backfilling recruiter states from company locations...")
    
    companies_with_loc = c.execute("""
        SELECT company_id, location FROM companies 
        WHERE location IS NOT NULL AND location != ''
    """).fetchall()
    
    backfilled = 0
    for comp in companies_with_loc:
        cid = comp['company_id']
        loc = comp['location']
        state = extract_state_from_location(loc)
        if not state:
            # Maybe the location IS a state abbreviation
            if loc.strip().upper() in STATE_MAP:
                state = loc.strip().upper()
        
        if state:
            result = c.execute("""
                UPDATE recruiters SET state = ? 
                WHERE company_id = ? AND (state IS NULL OR state = '')
            """, (state, cid))
            backfilled += result.rowcount
    
    conn.commit()
    print(f"  -> Backfilled state for {backfilled} recruiters from their company location")

    # ─── FINAL STATS ───
    final_null_loc = c.execute("SELECT COUNT(*) FROM companies WHERE location IS NULL OR location = ''").fetchone()[0]
    total_companies = c.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    missing_states = c.execute("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''").fetchone()[0]
    total_recruiters = c.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
    
    elapsed = round(time.time() - t0, 2)
    
    print(f"\n{'='*60}")
    print(f"COMPANY LOCATION RECOVERY COMPLETE!")
    print(f"{'='*60}")
    print(f"Execution Time: {elapsed}s")
    print(f"Companies with location: {total_companies - final_null_loc:,} / {total_companies:,}")
    print(f"Companies still missing location: {final_null_loc:,}")
    print(f"Known HQ mappings applied: {len(known_updates):,}")
    print(f"Locations inferred from recruiter density: {inferred:,}")
    print(f"Recruiter states backfilled: {backfilled:,}")
    print(f"Total missing recruiter states remaining: {missing_states:,}")
    print(f"{'='*60}")
    
    conn.close()

if __name__ == '__main__':
    run()
