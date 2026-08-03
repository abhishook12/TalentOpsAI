"""
Resolve Ghost Recruiters — Phase 2 Inference Engine
============================================================
Run:  python backend/scripts/resolve_ghosts.py
"""
import os, sys, re
import psycopg2
from dotenv import load_dotenv

load_dotenv(r'C:\TalentOpsAI\backend\.env')
DATABASE_URL = os.environ.get('DATABASE_URL', '').replace('+psycopg', '')

# Hardcoded top dirty domains -> States
HARDCODED_DOMAINS = {
    'inspyr solutions.com': 'FL',
    'strategic staffing solutions .com': 'MI',
    'bain.com': 'MA',
    'highspring.com': 'TN',
    'eogresources.com': 'TX',
    'southerncompany.com': 'GA',
    'southernco.com': 'GA',
    'lupusconsulting.com': 'ZZ', # International
    'csdef.com': 'XX',           # Unknown
    'insourcess.com': 'XX',
    'llh.com': 'XX',
    '84.51˚.com': 'OH',
    'prominenceadvisors.com': 'WI',
    'eosits.com': 'CA',
    'claconnect.com': 'MN',
    'truitypartners.com': 'WI',
    'tacworldwide.com': 'MA',
    'barrinqtonjames.com': 'ZZ',
    'universalorlando.com': 'FL',
    'gcstechtalent.com': 'TX',
    '24 seven talent.com': 'NY',
    'freshminds.co.uk': 'ZZ',
    'laserfiche.com': 'CA',
    'bjc.org': 'MO',
    'soal technologies - perfect hire, guaranteed!.com': 'TX',
    'huxley.fr': 'ZZ',
    'mcbrideconsulting.net': 'NY',
    'exadel.com': 'CA',
    'phs.org': 'NM',
    'vancon.com': 'UT',
    'natera.com': 'TX',
    'omnicommediagroup.com': 'NY',
    'bcdme.com': 'ZZ',
    'prometsource.com': 'IL',
    'k2integrity.com': 'NY',
    'd4m-int.com': 'ZZ',
    'usgrpinc.com': 'TX',
    'brightcoregroup.com': 'FL',
    'makenotion.com': 'CA',
    'coreweave.com': 'NJ',
}

# International and Remote keywords
INTL_REMOTE_KEYWORDS = [
    ('United Kingdom', 'ZZ'),
    ('UK', 'ZZ'),
    ('Canada', 'ZZ'),
    ('Ireland', 'ZZ'),
    ('France', 'ZZ'),
    ('Netherlands', 'ZZ'),
    ('Switzerland', 'ZZ'),
    ('Australia', 'ZZ'),
    ('Toronto', 'ZZ'),
    ('Montreal', 'ZZ'),
    ('London', 'ZZ'),
    ('Remote', 'RM'),
    ('Telecommute', 'RM'),
    ('Distributed', 'RM')
]

def get_unknown_count(cur):
    cur.execute("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")
    return cur.fetchone()[0]


def pass_8_hardcoded_domains(cur):
    print("\n── Pass 8: Hardcode top dirty domains ──")
    
    cur.execute("""
        SELECT recruiter_id, split_part(email, '@', 2) as domain
        FROM recruiters
        WHERE (state IS NULL OR state = '') AND email LIKE '%%@%%'
    """)
    rows = cur.fetchall()
    
    updates = []
    for rid, domain in rows:
        d = domain.lower().strip()
        if d in HARDCODED_DOMAINS:
            state = HARDCODED_DOMAINS[d]
            updates.append((state, 'hardcoded_domain_fallback', 'high', f'Matched dirty domain: {d}', rid))
            
    if updates:
        cur.executemany("""
            UPDATE recruiters 
            SET state = %s, state_source = %s, state_confidence = %s, state_reason = %s
            WHERE recruiter_id = %s AND (state IS NULL OR state = '')
        """, updates)
        
    print(f"   Resolved: {len(updates):,}")
    return len(updates)


def pass_9_intl_remote(cur):
    print("\n── Pass 9: International & Remote Tagging ──")
    
    cur.execute("""
        SELECT recruiter_id, notes, location
        FROM recruiters
        WHERE (state IS NULL OR state = '')
          AND (
            (notes IS NOT NULL AND notes != '')
            OR (location IS NOT NULL AND location != '')
          )
    """)
    rows = cur.fetchall()
    
    updates = []
    for rid, notes, loc in rows:
        notes_str = (notes or '').lower()
        loc_str = (loc or '').lower()
        full_text = f"{notes_str} {loc_str}"
        
        assigned = False
        for keyword, code in INTL_REMOTE_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', full_text):
                updates.append((code, 'intl_remote_keyword', 'medium', f'Matched keyword: {keyword}', rid))
                assigned = True
                break
        
        # If it has a GEO tag but wasn't matched above, just set it to ZZ anyway if it's not US-looking
        if not assigned and '[geo:' in notes_str:
            # Check if it has a US state pattern
            if not re.search(r'\b[A-Z]{2}\b', notes_str, re.IGNORECASE):
                updates.append(('ZZ', 'intl_geo_fallback', 'low', 'Has non-US GEO tag', rid))
                
    if updates:
        cur.executemany("""
            UPDATE recruiters 
            SET state = %s, state_source = %s, state_confidence = %s, state_reason = %s
            WHERE recruiter_id = %s AND (state IS NULL OR state = '')
        """, updates)
        
    print(f"   Resolved: {len(updates):,}")
    return len(updates)


def pass_10_quarantine(cur):
    print("\n── Pass 10: Quarantine True Ghosts ──")
    
    cur.execute("""
        UPDATE recruiters
        SET state = 'XX',
            state_source = 'quarantined',
            state_confidence = 'none',
            state_reason = 'Exhausted all inference passes (no location, no phone, no company, no domain match)'
        WHERE state IS NULL OR state = ''
    """)
    count = cur.rowcount
    print(f"   Quarantined: {count:,}")
    return count


def run():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    
    initial = get_unknown_count(cur)
    print(f"\n{'='*60}")
    print(f" GHOST RECRUITERS AT START: {initial:,}")
    print(f"{'='*60}")
    
    results = {}
    
    try:
        results['Pass 8: Hardcoded dirty domains'] = pass_8_hardcoded_domains(cur)
        results['Pass 9: INTL/Remote tags']        = pass_9_intl_remote(cur)
        results['Pass 10: Quarantined']            = pass_10_quarantine(cur)
        
        conn.commit()
        print("\n✅ All ghost updates committed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR — Transaction rolled back: {e}")
        raise
    
    final = get_unknown_count(cur)
    total_resolved = initial - final
    
    print(f"\n{'='*60}")
    print(f" RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Pass':<40} {'Resolved':>10}")
    print(f"{'-'*40} {'-'*10}")
    for name, count in results.items():
        print(f"{name:<40} {count:>10,}")
    print(f"{'-'*40} {'-'*10}")
    print(f"{'TOTAL PROCESSED':<40} {total_resolved:>10,}")
    print(f"{'REMAINING NULL STATES':<40} {final:>10,}")
    print(f"{'='*60}\n")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    run()
