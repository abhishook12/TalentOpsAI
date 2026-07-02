#!/usr/bin/env python
"""Universal State Triangulation & Dashboard Sync Engine - TalentOpsAI"""
import sys, os, time, re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

STATE_MAP = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'ON', 'PE', 'QC', 'SK', 'UK', 'DE', 'FR', 'IN', 'AU', 'SG', 'IE'
}

FULL_STATE_NAMES = {
    'CALIFORNIA': 'CA', 'NEW YORK': 'NY', 'TEXAS': 'TX', 'FLORIDA': 'FL', 'ILLINOIS': 'IL',
    'PENNSYLVANIA': 'PA', 'OHIO': 'OH', 'GEORGIA': 'GA', 'NORTH CAROLINA': 'NC', 'MICHIGAN': 'MI',
    'NEW JERSEY': 'NJ', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'MASSACHUSETTS': 'MA', 'ARIZONA': 'AZ',
    'INDIANA': 'IN', 'TENNESSEE': 'TN', 'MISSOURI': 'MO', 'MARYLAND': 'MD', 'WISCONSIN': 'WI',
    'MINNESOTA': 'MN', 'COLORADO': 'CO', 'ALABAMA': 'AL', 'SOUTH CAROLINA': 'SC', 'LOUISIANA': 'LA',
    'KENTUCKY': 'KY', 'OREGON': 'OR', 'OKLAHOMA': 'OK', 'CONNECTICUT': 'CT', 'UTAH': 'UT',
    'IOWA': 'IA', 'NEVADA': 'NV', 'ARKANSAS': 'AR', 'MISSISSIPPI': 'MS', 'KANSAS': 'KS',
    'NEW MEXICO': 'NM', 'NEBRASKA': 'NE', 'IDAHO': 'ID', 'WEST VIRGINIA': 'WV', 'HAWAII': 'HI',
    'NEW HAMPSHIRE': 'NH', 'MAINE': 'ME', 'RHODE ISLAND': 'RI', 'MONTANA': 'MT', 'DELAWARE': 'DE',
    'SOUTH DAKOTA': 'SD', 'NORTH DAKOTA': 'ND', 'ALASKA': 'AK', 'VERMONT': 'VT', 'WYOMING': 'WY',
    'DISTRICT OF COLUMBIA': 'DC', 'ONTARIO': 'ON', 'BRITISH COLUMBIA': 'BC', 'QUEBEC': 'QC',
    'ALBERTA': 'AB', 'ENGLAND': 'UK', 'UNITED KINGDOM': 'UK', 'GERMANY': 'DE', 'AUSTRALIA': 'AU'
}

# Quick area code lookup for stray phone numbers
NANP_STATE = {
    '201': 'NJ', '202': 'DC', '203': 'CT', '205': 'AL', '206': 'WA', '207': 'ME', '208': 'ID', '209': 'CA',
    '210': 'TX', '212': 'NY', '213': 'CA', '214': 'TX', '215': 'PA', '216': 'OH', '217': 'IL', '218': 'MN',
    '219': 'IN', '224': 'IL', '225': 'LA', '228': 'MS', '231': 'MI', '234': 'OH', '239': 'FL', '240': 'MD',
    '248': 'MI', '251': 'AL', '253': 'WA', '254': 'TX', '256': 'AL', '260': 'IN', '262': 'WI', '267': 'PA',
    '269': 'MI', '270': 'KY', '281': 'TX', '301': 'MD', '302': 'DE', '303': 'CO', '304': 'WV', '305': 'FL',
    '307': 'WY', '309': 'IL', '310': 'CA', '312': 'IL', '313': 'MI', '314': 'MO', '315': 'NY', '316': 'KS',
    '317': 'IN', '319': 'IA', '320': 'MN', '321': 'FL', '323': 'CA', '330': 'OH', '331': 'IL', '334': 'AL',
    '336': 'NC', '337': 'LA', '339': 'MA', '347': 'NY', '351': 'MA', '352': 'FL', '386': 'FL', '401': 'RI',
    '402': 'NE', '404': 'GA', '405': 'OK', '406': 'MT', '407': 'FL', '408': 'CA', '409': 'TX', '410': 'MD',
    '412': 'PA', '413': 'MA', '414': 'WI', '415': 'CA', '419': 'OH', '423': 'TN', '424': 'CA', '425': 'WA',
    '430': 'TX', '432': 'TX', '434': 'VA', '435': 'UT', '440': 'OH', '443': 'MD', '469': 'TX', '470': 'GA',
    '479': 'AR', '480': 'AZ', '484': 'PA', '501': 'AR', '502': 'KY', '503': 'OR', '504': 'LA', '505': 'NM',
    '507': 'MN', '508': 'MA', '509': 'WA', '510': 'CA', '512': 'TX', '513': 'OH', '515': 'IA', '516': 'NY',
    '517': 'MI', '518': 'NY', '520': 'AZ', '530': 'CA', '540': 'VA', '541': 'OR', '559': 'CA', '561': 'FL',
    '562': 'CA', '563': 'IA', '570': 'PA', '571': 'VA', '573': 'MO', '574': 'IN', '585': 'NY', '586': 'MI',
    '602': 'AZ', '603': 'NH', '604': 'BC', '607': 'NY', '608': 'WI', '609': 'NJ', '610': 'PA', '612': 'MN',
    '614': 'OH', '615': 'TN', '616': 'MI', '617': 'MA', '618': 'IL', '619': 'CA', '620': 'KS', '623': 'AZ',
    '626': 'CA', '630': 'IL', '631': 'NY', '646': 'NY', '650': 'CA', '651': 'MN', '678': 'GA', '682': 'TX',
    '702': 'NV', '703': 'VA', '704': 'NC', '706': 'GA', '707': 'CA', '708': 'IL', '712': 'IA', '713': 'TX',
    '714': 'CA', '715': 'WI', '717': 'PA', '718': 'NY', '719': 'CO', '720': 'CO', '727': 'FL', '732': 'NJ',
    '734': 'MI', '740': 'OH', '757': 'VA', '760': 'CA', '763': 'MN', '770': 'GA', '772': 'FL', '773': 'IL',
    '774': 'MA', '781': 'MA', '785': 'KS', '786': 'FL', '801': 'UT', '802': 'VT', '803': 'SC', '804': 'VA',
    '805': 'CA', '806': 'TX', '808': 'HI', '810': 'MI', '812': 'IN', '813': 'FL', '814': 'PA', '815': 'IL',
    '816': 'MO', '817': 'TX', '818': 'CA', '828': 'NC', '830': 'TX', '831': 'CA', '832': 'TX', '843': 'SC',
    '845': 'NY', '847': 'IL', '848': 'NJ', '850': 'FL', '856': 'NJ', '857': 'MA', '858': 'CA', '859': 'KY',
    '860': 'CT', '863': 'FL', '864': 'SC', '865': 'TN', '870': 'AR', '878': 'PA', '901': 'TN', '903': 'TX',
    '904': 'FL', '908': 'NJ', '909': 'CA', '910': 'NC', '912': 'GA', '913': 'KS', '914': 'NY', '915': 'TX',
    '916': 'CA', '917': 'NY', '918': 'OK', '919': 'NC', '920': 'WI', '925': 'CA', '931': 'TN', '937': 'OH',
    '940': 'TX', '941': 'FL', '949': 'CA', '951': 'CA', '952': 'MN', '954': 'FL', '956': 'TX', '970': 'CO',
    '971': 'OR', '972': 'TX', '973': 'NJ', '978': 'MA', '979': 'TX', '980': 'NC', '985': 'LA', '989': 'MI',
    '403': 'AB', '416': 'ON', '514': 'QC', '613': 'ON'
}

def sync_state():
    t0 = time.time()
    print(f"[{time.strftime('%X')}] UNIVERSAL STATE TRIANGULATION & DASHBOARD SYNC...")
    db = SessionLocal()
    try:
        last_rid = 0
        synced = 0
        while True:
            chunk = db.execute(text("""
                SELECT recruiter_id, location, phone, notes
                FROM recruiters
                WHERE recruiter_id > :lid AND (state IS NULL OR TRIM(state) = '' OR LOWER(state) = 'nan') AND is_active = true
                ORDER BY recruiter_id LIMIT 10000
            """), {"lid": last_rid}).mappings().all()
            if not chunk: break

            up_batch = []
            for r in chunk:
                rid = r['recruiter_id']
                loc = (r['location'] or "").strip()
                phone_str = (r['phone'] or "").strip()
                notes_str = (r['notes'] or "").strip()
                
                st = None
                src = "recruiter_location"

                # 1. Check notes for [GEO: ... ]
                geo_m = re.search(r'\[GEO:\s*(.*?)\]', notes_str)
                if geo_m:
                    g_txt = geo_m.group(1).upper()
                    for s_full, s_abbr in FULL_STATE_NAMES.items():
                        if s_full in g_txt: st = s_abbr; src = "inferred_triangulation"; break
                    if not st:
                        toks = re.findall(r'\b[A-Z]{2}\b', g_txt)
                        for t in reversed(toks):
                            if t in STATE_MAP: st = t; src = "inferred_triangulation"; break

                # 2. Check location string
                if not st and loc and loc.lower() not in ('none', 'nan', 'not provided', 'unknown'):
                    loc_up = loc.upper()
                    # Check exact state names
                    for s_full, s_abbr in FULL_STATE_NAMES.items():
                        if re.search(rf'\b{s_full}\b', loc_up): st = s_abbr; src = "recruiter_location"; break
                    # Check 2-letter tokens
                    if not st:
                        toks = re.findall(r'\b[A-Z]{2}\b', loc_up)
                        for t in reversed(toks):
                            if t in STATE_MAP: st = t; src = "recruiter_location"; break
                    # Check if location string is actually a phone number
                    if not st:
                        digits = re.sub(r'\D', '', loc)
                        if len(digits) >= 10:
                            ac = digits[1:4] if (len(digits) == 11 and digits.startswith('1')) else digits[:3]
                            if ac in NANP_STATE: st = NANP_STATE[ac]; src = "phone_inferred"

                # 3. Check phone column
                if not st and phone_str:
                    digits = re.sub(r'\D', '', phone_str)
                    if len(digits) >= 10:
                        ac = digits[1:4] if (len(digits) == 11 and digits.startswith('1')) else digits[:3]
                        if ac in NANP_STATE: st = NANP_STATE[ac]; src = "phone_inferred"

                if st:
                    up_batch.append({"rid": rid, "st": st, "src": src})

            if up_batch:
                for i in range(0, len(up_batch), 500):
                    b = up_batch[i:i+500]
                    db.execute(text("UPDATE recruiters SET state = :st, state_source = :src WHERE recruiter_id = :rid"), b)
                db.commit()
                synced += len(up_batch)

            last_rid = chunk[-1]['recruiter_id']

        print(f"[{time.strftime('%X')}] Sync Complete! Populated dashboard state column for +{synced:,} recruiters in {round(time.time()-t0,2)}s.")
        
        # Clear analytics cache
        try:
            from app.routes.analytics import analytics_cache
            analytics_cache.clear()
            print("Analytics cache cleared!")
        except Exception:
            pass

    except Exception as e:
        db.rollback()
        print("ERROR:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    sync_state()
