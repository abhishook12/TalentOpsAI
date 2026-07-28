#!/usr/bin/env python
"""
Phase 2: Email Domain → Company Location Mapper
================================================
For companies with NO recruiter state data, we can still infer location
by looking at other companies that share the same email domain and DO have locations.
Also uses the email domain suffix (.uk, .au, .de) for international companies.
"""
import sqlite3
import time
from collections import Counter

DB_PATH = 'dev.db'

# Country TLD to location mapping
TLD_LOCATIONS = {
    '.uk': 'United Kingdom',
    '.co.uk': 'United Kingdom',
    '.au': 'Australia',
    '.ca': 'Canada',
    '.de': 'Germany',
    '.fr': 'France',
    '.in': 'India',
    '.jp': 'Japan',
    '.br': 'Brazil',
    '.mx': 'Mexico',
    '.nl': 'Netherlands',
    '.se': 'Sweden',
    '.no': 'Norway',
    '.dk': 'Denmark',
    '.fi': 'Finland',
    '.ch': 'Switzerland',
    '.at': 'Austria',
    '.be': 'Belgium',
    '.es': 'Spain',
    '.it': 'Italy',
    '.pt': 'Portugal',
    '.ie': 'Ireland',
    '.nz': 'New Zealand',
    '.sg': 'Singapore',
    '.hk': 'Hong Kong',
    '.kr': 'South Korea',
    '.cn': 'China',
    '.tw': 'Taiwan',
    '.za': 'South Africa',
    '.il': 'Israel',
    '.ae': 'UAE',
    '.pl': 'Poland',
    '.cz': 'Czech Republic',
    '.ru': 'Russia',
}

def run():
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print(f"[{time.strftime('%X')}] === EMAIL DOMAIN LOCATION MAPPER ===")

    # Get all companies still missing location
    missing_comps = c.execute("""
        SELECT company_id, company_name 
        FROM companies 
        WHERE location IS NULL OR location = ''
    """).fetchall()
    print(f"  Companies missing location: {len(missing_comps)}")

    # Build domain→location map from recruiters who have location data
    print(f"[{time.strftime('%X')}] Building domain->location knowledge base...")
    domain_loc_map = {}
    rows = c.execute("""
        SELECT SUBSTR(email, INSTR(email, '@') + 1) AS domain, state, COUNT(*) as cnt
        FROM recruiters
        WHERE email LIKE '%@%' AND state IS NOT NULL AND state != ''
        GROUP BY domain, state
        ORDER BY domain, cnt DESC
    """).fetchall()
    
    for row in rows:
        dom = row['domain']
        if dom not in domain_loc_map:
            domain_loc_map[dom] = row['state']
    
    print(f"  Built location map for {len(domain_loc_map)} email domains")

    # For each missing company, check their recruiters' email domains
    updates = []
    for comp in missing_comps:
        cid = comp['company_id']
        # Get the dominant email domain for this company's recruiters
        dom_row = c.execute("""
            SELECT SUBSTR(email, INSTR(email, '@') + 1) AS domain, COUNT(*) as cnt
            FROM recruiters
            WHERE company_id = ? AND email LIKE '%@%'
            GROUP BY domain ORDER BY cnt DESC LIMIT 1
        """, (cid,)).fetchone()
        
        if dom_row:
            domain = dom_row['domain']
            # Check if we know the location from other recruiters with same domain
            if domain in domain_loc_map:
                updates.append((domain_loc_map[domain], cid))
                continue
            
            # Check country TLD
            for tld, country in TLD_LOCATIONS.items():
                if domain.endswith(tld):
                    updates.append((country, cid))
                    break
    
    if updates:
        c.executemany("UPDATE companies SET location = ? WHERE company_id = ?", updates)
        conn.commit()
    print(f"[{time.strftime('%X')}] Updated {len(updates)} companies from email domain cross-referencing")

    # Phase 2: Now backfill recruiter states from these newly-located companies
    print(f"[{time.strftime('%X')}] Backfilling recruiter states...")
    STATE_MAP = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
    }
    
    newly_located = c.execute("""
        SELECT company_id, location FROM companies
        WHERE location IS NOT NULL AND location != ''
    """).fetchall()
    
    backfilled = 0
    for comp in newly_located:
        loc = comp['location'].strip()
        state = None
        # Check if location ends with a 2-letter state code
        parts = loc.split(',')
        if len(parts) >= 2:
            candidate = parts[-1].strip().upper()
            if candidate in STATE_MAP:
                state = candidate
        elif loc.upper() in STATE_MAP:
            state = loc.upper()
        
        if state:
            result = c.execute("""
                UPDATE recruiters SET state = ?
                WHERE company_id = ? AND (state IS NULL OR state = '')
            """, (state, comp['company_id']))
            backfilled += result.rowcount
    
    conn.commit()

    # Final stats
    final_missing_loc = c.execute("SELECT COUNT(*) FROM companies WHERE location IS NULL OR location = ''").fetchone()[0]
    final_missing_states = c.execute("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''").fetchone()[0]
    total_companies = c.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    
    elapsed = round(time.time() - t0, 2)
    print(f"\n{'='*60}")
    print(f"EMAIL DOMAIN LOCATION MAPPER COMPLETE!")
    print(f"{'='*60}")
    print(f"Execution Time: {elapsed}s")
    print(f"Companies with location: {total_companies - final_missing_loc:,} / {total_companies:,}")
    print(f"Companies still missing: {final_missing_loc:,}")
    print(f"Domain cross-ref matches: {len(updates):,}")
    print(f"Recruiter states backfilled: {backfilled:,}")
    print(f"Total missing recruiter states: {final_missing_states:,}")
    print(f"{'='*60}")
    
    conn.close()

if __name__ == '__main__':
    run()
