"""
Resolve Unknown State Recruiters — 7-Pass Inference Engine
============================================================
Run:  python backend/scripts/resolve_unknown_states.py
"""
import os, sys, re, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.utils.state_mapper import extract_state_detailed, ABBR_TO_NAME

DATABASE_URL = os.environ.get('DATABASE_URL', '').replace('+psycopg', '')

PERSONAL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'protonmail.com', 'live.com', 'msn.com', 'ymail.com',
    'zoho.com', 'mail.com', 'gmx.com', 'me.com', 'comcast.net',
    'att.net', 'verizon.net', 'sbcglobal.net', 'cox.net', 'charter.net',
    'earthlink.net', 'mac.com', 'rocketmail.com', 'inbox.com',
}

# US area code → state mapping (major codes only, unambiguous)
AREA_CODE_TO_STATE = {
    '201':'NJ','202':'DC','203':'CT','205':'AL','206':'WA','207':'ME','208':'ID',
    '209':'CA','210':'TX','212':'NY','213':'CA','214':'TX','215':'PA','216':'OH',
    '217':'IL','218':'MN','219':'IN','224':'IL','225':'LA','228':'MS','229':'GA',
    '231':'MI','234':'OH','239':'FL','240':'MD','248':'MI','251':'AL','252':'NC',
    '253':'WA','254':'TX','256':'AL','260':'IN','262':'WI','267':'PA','269':'MI',
    '270':'KY','272':'PA','276':'VA','281':'TX','301':'MD','302':'DE','303':'CO',
    '304':'WV','305':'FL','307':'WY','308':'NE','309':'IL','310':'CA','312':'IL',
    '313':'MI','314':'MO','315':'NY','316':'KS','317':'IN','318':'LA','319':'IA',
    '320':'MN','321':'FL','323':'CA','325':'TX','330':'OH','331':'IL','334':'AL',
    '336':'NC','337':'LA','339':'MA','340':'VI','346':'TX','347':'NY','351':'MA',
    '352':'FL','360':'WA','361':'TX','385':'UT','386':'FL','401':'RI','402':'NE',
    '404':'GA','405':'OK','406':'MT','407':'FL','408':'CA','409':'TX','410':'MD',
    '412':'PA','413':'MA','414':'WI','415':'CA','417':'MO','419':'OH','423':'TN',
    '424':'CA','425':'WA','430':'TX','432':'TX','434':'VA','435':'UT','440':'OH',
    '443':'MD','469':'TX','470':'GA','475':'CT','478':'GA','479':'AR','480':'AZ',
    '484':'PA','501':'AR','502':'KY','503':'OR','504':'LA','505':'NM','507':'MN',
    '508':'MA','509':'WA','510':'CA','512':'TX','513':'OH','515':'IA','516':'NY',
    '517':'MI','518':'NY','520':'AZ','530':'CA','531':'NE','534':'WI','539':'OK',
    '540':'VA','541':'OR','551':'NJ','559':'CA','561':'FL','562':'CA','563':'IA',
    '567':'OH','570':'PA','571':'VA','573':'MO','574':'IN','575':'NM','580':'OK',
    '585':'NY','586':'MI','601':'MS','602':'AZ','603':'NH','605':'SD','606':'KY',
    '607':'NY','608':'WI','609':'NJ','610':'PA','612':'MN','614':'OH','615':'TN',
    '616':'MI','617':'MA','618':'IL','619':'CA','620':'KS','623':'AZ','626':'CA',
    '629':'TN','630':'IL','631':'NY','636':'MO','641':'IA','646':'NY','650':'CA',
    '651':'MN','657':'CA','660':'MO','661':'CA','662':'MS','667':'MD','669':'CA',
    '678':'GA','681':'WV','682':'TX','689':'FL','701':'ND','702':'NV','703':'VA',
    '704':'NC','706':'GA','707':'CA','708':'IL','712':'IA','713':'TX','714':'CA',
    '715':'WI','716':'NY','717':'PA','718':'NY','719':'CO','720':'CO','724':'PA',
    '727':'FL','731':'TN','732':'NJ','734':'MI','737':'TX','740':'OH','743':'NC',
    '747':'CA','754':'FL','757':'VA','760':'CA','762':'GA','763':'MN','765':'IN',
    '769':'MS','770':'GA','772':'FL','773':'IL','774':'MA','775':'NV','779':'IL',
    '781':'MA','785':'KS','786':'FL','801':'UT','802':'VT','803':'SC','804':'VA',
    '805':'CA','806':'TX','808':'HI','810':'MI','812':'IN','813':'FL','814':'PA',
    '815':'IL','816':'MO','817':'TX','818':'CA','828':'NC','830':'TX','831':'CA',
    '832':'TX','838':'NY','843':'SC','845':'NY','847':'IL','848':'NJ','850':'FL',
    '856':'NJ','857':'MA','858':'CA','859':'KY','860':'CT','862':'NJ','863':'FL',
    '864':'SC','865':'TN','870':'AR','872':'IL','878':'PA','901':'TN','903':'TX',
    '904':'FL','906':'MI','907':'AK','908':'NJ','909':'CA','910':'NC','912':'GA',
    '913':'KS','914':'NY','915':'TX','916':'CA','917':'NY','918':'OK','919':'NC',
    '920':'WI','925':'CA','928':'AZ','929':'NY','931':'TN','936':'TX','937':'OH',
    '938':'AL','940':'TX','941':'FL','947':'MI','949':'CA','951':'CA','952':'MN',
    '954':'FL','956':'TX','959':'CT','970':'CO','971':'OR','972':'TX','973':'NJ',
    '978':'MA','979':'TX','980':'NC','984':'NC','985':'LA',
}


def get_unknown_count(cur):
    cur.execute("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")
    return cur.fetchone()[0]


def pass_1_location_parse(cur):
    """Parse recruiter's own location field."""
    print("\n── Pass 1: Parse recruiter location field ──")
    
    cur.execute("""
        SELECT recruiter_id, location 
        FROM recruiters 
        WHERE (state IS NULL OR state = '') 
          AND location IS NOT NULL AND location != ''
    """)
    rows = cur.fetchall()
    print(f"   Candidates: {len(rows):,}")
    
    updates = []
    for rid, loc in rows:
        state_code, reason = extract_state_detailed(loc)
        if state_code and state_code in ABBR_TO_NAME:
            updates.append((state_code, 'location_field_parse', 'high', reason or 'parsed', rid))
    
    if updates:
        cur.executemany("""
            UPDATE recruiters 
            SET state = %s, state_source = %s, state_confidence = %s, state_reason = %s
            WHERE recruiter_id = %s AND (state IS NULL OR state = '')
        """, updates)
    
    print(f"   Resolved: {len(updates):,}")
    return len(updates)


def pass_2_company_state(cur):
    """Propagate company state to linked recruiters."""
    print("\n── Pass 2: Company state propagation ──")
    
    cur.execute("""
        UPDATE recruiters r
        SET state = c.state,
            state_source = 'company_hq',
            state_confidence = 'high',
            state_reason = 'Inherited from linked company'
        FROM companies c
        WHERE r.company_id = c.company_id
          AND (r.state IS NULL OR r.state = '')
          AND c.state IS NOT NULL AND c.state != ''
          AND LENGTH(c.state) = 2
    """)
    count = cur.rowcount
    print(f"   Resolved: {count:,}")
    return count


def pass_3_company_location_parse(cur):
    """Parse company location field, then propagate."""
    print("\n── Pass 3: Parse company location → propagate ──")
    
    # Step 1: Fix companies missing state but having location
    cur.execute("""
        SELECT company_id, location 
        FROM companies 
        WHERE (state IS NULL OR state = '') 
          AND location IS NOT NULL AND location != ''
    """)
    companies = cur.fetchall()
    print(f"   Companies to parse: {len(companies):,}")
    
    company_updates = []
    for cid, loc in companies:
        state_code, reason = extract_state_detailed(loc)
        if state_code and state_code in ABBR_TO_NAME:
            company_updates.append((state_code, cid))
    
    if company_updates:
        cur.executemany("""
            UPDATE companies SET state = %s WHERE company_id = %s AND (state IS NULL OR state = '')
        """, company_updates)
    print(f"   Companies fixed: {len(company_updates):,}")
    
    # Step 2: Propagate to recruiters (same as pass 2 but with new source tag)
    cur.execute("""
        UPDATE recruiters r
        SET state = c.state,
            state_source = 'company_location_parsed',
            state_confidence = 'medium',
            state_reason = 'Parsed from company location'
        FROM companies c
        WHERE r.company_id = c.company_id
          AND (r.state IS NULL OR r.state = '')
          AND c.state IS NOT NULL AND c.state != ''
          AND LENGTH(c.state) = 2
    """)
    count = cur.rowcount
    print(f"   Recruiters resolved: {count:,}")
    return count


def pass_4_email_domain_company(cur):
    """Match email domain to company website → inherit state."""
    print("\n── Pass 4: Email domain → company website → state ──")
    
    # Build domain→state lookup from companies
    cur.execute(r"""
        SELECT 
            LOWER(REGEXP_REPLACE(
                REGEXP_REPLACE(website, '^https?://', ''),
                '^www\.', ''
            )) as domain, 
            state
        FROM companies
        WHERE state IS NOT NULL AND state != '' AND LENGTH(state) = 2
          AND website IS NOT NULL AND website != ''
    """)
    
    company_states = {}
    for domain, state in cur.fetchall():
        # Clean trailing slashes
        domain = domain.rstrip('/').strip()
        if domain and state:
            company_states[domain] = state
    
    print(f"   Company domains with known state: {len(company_states):,}")
    
    # Get unknown recruiters with emails
    cur.execute("""
        SELECT recruiter_id, email
        FROM recruiters
        WHERE (state IS NULL OR state = '')
          AND email IS NOT NULL AND email LIKE '%@%'
    """)
    candidates = cur.fetchall()
    print(f"   Candidates: {len(candidates):,}")
    
    updates = []
    for rid, email in candidates:
        parts = email.split('@')
        if len(parts) == 2:
            domain = parts[1].lower().strip()
            if domain not in PERSONAL_DOMAINS and domain in company_states:
                updates.append((company_states[domain], rid))
    
    if updates:
        cur.executemany("""
            UPDATE recruiters 
            SET state = %s, 
                state_source = 'email_domain_company_match', 
                state_confidence = 'medium',
                state_reason = 'Email domain matched company website'
            WHERE recruiter_id = %s AND (state IS NULL OR state = '')
        """, updates)
    
    print(f"   Resolved: {len(updates):,}")
    return len(updates)


def pass_5_peer_clustering(cur):
    """Peer domain clustering — majority vote."""
    print("\n── Pass 5: Peer domain clustering ──")
    
    cur.execute("""
        WITH domain_states AS (
            SELECT split_part(email, '@', 2) as domain,
                   state,
                   COUNT(*) as cnt
            FROM recruiters
            WHERE state IS NOT NULL AND state != '' 
              AND email LIKE '%%@%%'
              AND LENGTH(state) = 2
            GROUP BY split_part(email, '@', 2), state
        ),
        domain_totals AS (
            SELECT domain, SUM(cnt) as total
            FROM domain_states
            GROUP BY domain
        ),
        best AS (
            SELECT ds.domain, ds.state, ds.cnt, dt.total,
                   ROUND(ds.cnt::numeric / dt.total * 100) as pct,
                   ROW_NUMBER() OVER(PARTITION BY ds.domain ORDER BY ds.cnt DESC) as rn
            FROM domain_states ds
            JOIN domain_totals dt ON ds.domain = dt.domain
            WHERE dt.total >= 3
        )
        SELECT domain, state, cnt, total, pct
        FROM best
        WHERE rn = 1 AND pct >= 60
    """)
    
    domain_map = {}
    for domain, state, cnt, total, pct in cur.fetchall():
        if domain not in PERSONAL_DOMAINS:
            domain_map[domain] = (state, int(pct), int(total))
    
    print(f"   Domains with strong consensus: {len(domain_map):,}")
    
    # Get unknowns
    cur.execute("""
        SELECT recruiter_id, split_part(email, '@', 2) as domain
        FROM recruiters
        WHERE (state IS NULL OR state = '')
          AND email LIKE '%%@%%'
    """)
    
    updates = []
    for rid, domain in cur.fetchall():
        if domain in domain_map:
            state, pct, total = domain_map[domain]
            reason = f"Majority state ({pct}%) from {total} peers at @{domain}"
            updates.append((state, 'peer_domain_cluster', 'low', reason, rid))
    
    if updates:
        cur.executemany("""
            UPDATE recruiters 
            SET state = %s, state_source = %s, state_confidence = %s, state_reason = %s
            WHERE recruiter_id = %s AND (state IS NULL OR state = '')
        """, updates)
    
    print(f"   Resolved: {len(updates):,}")
    return len(updates)


def pass_6_structured_locations(cur):
    """Check recruiter_locations table."""
    print("\n── Pass 6: Structured locations table ──")
    
    cur.execute("""
        UPDATE recruiters r
        SET state = rl.state,
            state_source = 'structured_locations_table',
            state_confidence = 'medium',
            state_reason = 'From recruiter_locations (' || rl.location_type || ')'
        FROM (
            SELECT DISTINCT ON (recruiter_id) recruiter_id, state, location_type
            FROM recruiter_locations
            WHERE state IS NOT NULL AND state != ''
              AND LENGTH(state) <= 2
            ORDER BY recruiter_id,
                     CASE location_type 
                        WHEN 'person' THEN 1
                        WHEN 'company_headquarters' THEN 2
                        WHEN 'office' THEN 3
                        ELSE 4
                     END
        ) rl
        WHERE r.recruiter_id = rl.recruiter_id
          AND (r.state IS NULL OR r.state = '')
    """)
    count = cur.rowcount
    print(f"   Resolved: {count:,}")
    return count


def pass_7_phone_area_code(cur):
    """Map phone area codes to states."""
    print("\n── Pass 7: Phone area code → state ──")
    
    # Get phones for unknown-state recruiters
    cur.execute("""
        SELECT rp.recruiter_id, rp.phone_number
        FROM recruiter_phones rp
        JOIN recruiters r ON rp.recruiter_id = r.recruiter_id
        WHERE (r.state IS NULL OR r.state = '')
          AND rp.phone_number IS NOT NULL
    """)
    
    updates = []
    seen = set()
    for rid, phone in cur.fetchall():
        if rid in seen:
            continue
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        # Handle +1 prefix
        if digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]
        if len(digits) == 10:
            area = digits[:3]
            if area in AREA_CODE_TO_STATE:
                state = AREA_CODE_TO_STATE[area]
                updates.append((state, 'phone_area_code', 'low', f'Area code {area}', rid))
                seen.add(rid)
    
    if updates:
        cur.executemany("""
            UPDATE recruiters 
            SET state = %s, state_source = %s, state_confidence = %s, state_reason = %s
            WHERE recruiter_id = %s AND (state IS NULL OR state = '')
        """, updates)
    
    print(f"   Resolved: {len(updates):,}")
    return len(updates)


def run():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    
    initial = get_unknown_count(cur)
    print(f"\n{'='*60}")
    print(f" UNKNOWN STATE RECRUITERS AT START: {initial:,}")
    print(f"{'='*60}")
    
    results = {}
    
    try:
        results['Pass 1: Location field parse']     = pass_1_location_parse(cur)
        results['Pass 2: Company state propagation'] = pass_2_company_state(cur)
        results['Pass 3: Company location parse']    = pass_3_company_location_parse(cur)
        results['Pass 4: Email domain → company']    = pass_4_email_domain_company(cur)
        results['Pass 5: Peer domain clustering']    = pass_5_peer_clustering(cur)
        results['Pass 6: Structured locations']      = pass_6_structured_locations(cur)
        results['Pass 7: Phone area code']           = pass_7_phone_area_code(cur)
        
        conn.commit()
        print("\n✅ All changes committed successfully.")
        
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
    print(f"{'TOTAL RESOLVED':<40} {total_resolved:>10,}")
    print(f"{'REMAINING UNKNOWN':<40} {final:>10,}")
    print(f"{'='*60}\n")
    
    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
