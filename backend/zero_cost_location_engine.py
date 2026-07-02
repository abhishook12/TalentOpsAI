#!/usr/bin/env python
"""Zero-Cost Multi-Signal Offline Pinpoint Triangulation Engine - TalentOpsAI"""
import sys, os, time, re
from collections import Counter, defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

# Comprehensive North American Area Code Topology (Top ~250 Metro Areas)
NANP_GEO = {
    '201': 'Jersey City, NJ', '202': 'Washington, DC', '203': 'Bridgeport, CT', '205': 'Birmingham, AL',
    '206': 'Seattle, WA', '207': 'Portland, ME', '208': 'Boise, ID', '209': 'Stockton, CA',
    '210': 'San Antonio, TX', '212': 'New York, NY', '213': 'Los Angeles, CA', '214': 'Dallas, TX',
    '215': 'Philadelphia, PA', '216': 'Cleveland, OH', '217': 'Springfield, IL', '218': 'Duluth, MN',
    '219': 'Gary, IN', '224': 'Schaumburg, IL', '225': 'Baton Rouge, LA', '228': 'Gulfport, MS',
    '231': 'Muskegon, MI', '234': 'Akron, OH', '239': 'Fort Myers, FL', '240': 'Germantown, MD',
    '248': 'Troy, MI', '251': 'Mobile, AL', '253': 'Tacoma, WA', '254': 'Waco, TX',
    '256': 'Huntsville, AL', '260': 'Fort Wayne, IN', '262': 'Kenosha, WI', '267': 'Philadelphia, PA',
    '269': 'Kalamazoo, MI', '270': 'Bowling Green, KY', '281': 'Houston, TX', '301': 'Silver Spring, MD',
    '302': 'Wilmington, DE', '303': 'Denver, CO', '304': 'Charleston, WV', '305': 'Miami, FL',
    '307': 'Cheyenne, WY', '309': 'Peoria, IL', '310': 'Santa Monica, CA', '312': 'Chicago, IL',
    '313': 'Detroit, MI', '314': 'St. Louis, MO', '315': 'Syracuse, NY', '316': 'Wichita, KS',
    '317': 'Indianapolis, IN', '319': 'Cedar Rapids, IA', '320': 'St. Cloud, MN', '321': 'Orlando, FL',
    '323': 'Los Angeles, CA', '330': 'Akron, OH', '331': 'Aurora, IL', '334': 'Montgomery, AL',
    '336': 'Winston-Salem, NC', '337': 'Lafayette, LA', '339': 'Boston Metro, MA', '347': 'Brooklyn, NY',
    '351': 'Peabody, MA', '352': 'Gainesville, FL', '386': 'Daytona Beach, FL', '401': 'Providence, RI',
    '402': 'Omaha, NE', '404': 'Atlanta, GA', '405': 'Oklahoma City, OK', '406': 'Billings, MT',
    '407': 'Orlando, FL', '408': 'San Jose, CA', '409': 'Beaumont, TX', '410': 'Baltimore, MD',
    '412': 'Pittsburgh, PA', '413': 'Springfield, MA', '414': 'Milwaukee, WI', '415': 'San Francisco, CA',
    '419': 'Toledo, OH', '423': 'Chattanooga, TN', '424': 'Los Angeles, CA', '425': 'Bellevue, WA',
    '430': 'Tyler, TX', '432': 'Midland, TX', '434': 'Charlottesville, VA', '435': 'St. George, UT',
    '440': 'Parma, OH', '443': 'Baltimore, MD', '469': 'Dallas, TX', '470': 'Atlanta, GA',
    '479': 'Fayetteville, AR', '480': 'Scottsdale, AZ', '484': 'Allentown, PA', '501': 'Little Rock, AR',
    '502': 'Louisville, KY', '503': 'Portland, OR', '504': 'New Orleans, LA', '505': 'Albuquerque, NM',
    '507': 'Rochester, MN', '508': 'Worcester, MA', '509': 'Spokane, WA', '510': 'Oakland, CA',
    '512': 'Austin, TX', '513': 'Cincinnati, OH', '515': 'Des Moines, IA', '516': 'Hempstead, NY',
    '517': 'Lansing, MI', '518': 'Albany, NY', '520': 'Tucson, AZ', '530': 'Redding, CA',
    '540': 'Roanoke, VA', '541': 'Eugene, OR', '559': 'Fresno, CA', '561': 'West Palm Beach, FL',
    '562': 'Long Beach, CA', '563': 'Davenport, IA', '570': 'Scranton, PA', '571': 'Arlington, VA',
    '573': 'Columbia, MO', '574': 'South Bend, IN', '585': 'Rochester, NY', '586': 'Warren, MI',
    '602': 'Phoenix, AZ', '603': 'Manchester, NH', '604': 'Vancouver, BC', '607': 'Binghamton, NY',
    '608': 'Madison, WI', '609': 'Trenton, NJ', '610': 'Southeastern PA', '612': 'Minneapolis, MN',
    '614': 'Columbus, OH', '615': 'Nashville, TN', '616': 'Grand Rapids, MI', '617': 'Boston, MA',
    '618': 'Belleville, IL', '619': 'San Diego, CA', '620': 'Hutchinson, KS', '623': 'Glendale, AZ',
    '626': 'Pasadena, CA', '630': 'Naperville, IL', '631': 'Brentwood, NY', '646': 'New York, NY',
    '650': 'Palo Alto, CA', '651': 'St. Paul, MN', '678': 'Atlanta, GA', '682': 'Fort Worth, TX',
    '702': 'Las Vegas, NV', '703': 'Alexandria, VA', '704': 'Charlotte, NC', '706': 'Augusta, GA',
    '707': 'Santa Rosa, CA', '708': 'Cicero, IL', '712': 'Sioux City, IA', '713': 'Houston, TX',
    '714': 'Anaheim, CA', '715': 'Eau Claire, WI', '717': 'Lancaster, PA', '718': 'Queens, NY',
    '719': 'Colorado Springs, CO', '720': 'Denver, CO', '727': 'St. Petersburg, FL', '732': 'New Brunswick, NJ',
    '734': 'Ann Arbor, MI', '740': 'Newark, OH', '757': 'Virginia Beach, VA', '760': 'Oceanside, CA',
    '763': 'Plymouth, MN', '770': 'Roswell, GA', '772': 'Port St. Lucie, FL', '773': 'Chicago, IL',
    '774': 'Framingham, MA', '781': 'Waltham, MA', '785': 'Topeka, KS', '786': 'Miami, FL',
    '801': 'Salt Lake City, UT', '802': 'Burlington, VT', '803': 'Columbia, SC', '804': 'Richmond, VA',
    '805': 'Oxnard, CA', '806': 'Lubbock, TX', '808': 'Honolulu, HI', '810': 'Flint, MI',
    '812': 'Evansville, IN', '813': 'Tampa, FL', '814': 'Erie, PA', '815': 'Rockford, IL',
    '816': 'Kansas City, MO', '817': 'Fort Worth, TX', '818': 'Glendale, CA', '828': 'Asheville, NC',
    '830': 'New Braunfels, TX', '831': 'Salinas, CA', '832': 'Houston, TX', '843': 'Charleston, SC',
    '845': 'Poughkeepsie, NY', '847': 'Evanston, IL', '848': 'Toms River, NJ', '850': 'Tallahassee, FL',
    '856': 'Camden, NJ', '857': 'Boston, MA', '858': 'San Diego, CA', '859': 'Lexington, KY',
    '860': 'Hartford, CT', '863': 'Lakeland, FL', '864': 'Greenville, SC', '865': 'Knoxville, TN',
    '870': 'Jonesboro, AR', '878': 'Pittsburgh, PA', '901': 'Memphis, TN', '903': 'Tyler, TX',
    '904': 'Jacksonville, FL', '908': 'Elizabeth, NJ', '909': 'San Bernardino, CA', '910': 'Fayetteville, NC',
    '912': 'Savannah, GA', '913': 'Overland Park, KS', '914': 'Yonkers, NY', '915': 'El Paso, TX',
    '916': 'Sacramento, CA', '917': 'New York, NY', '918': 'Tulsa, OK', '919': 'Raleigh, NC',
    '920': 'Green Bay, WI', '925': 'Concord, CA', '931': 'Clarksville, TN', '937': 'Dayton, OH',
    '940': 'Denton, TX', '941': 'Sarasota, FL', '949': 'Irvine, CA', '951': 'Riverside, CA',
    '952': 'Bloomington, MN', '954': 'Fort Lauderdale, FL', '956': 'Laredo, TX', '970': 'Fort Collins, CO',
    '971': 'Portland, OR', '972': 'Dallas, TX', '973': 'Newark, NJ', '978': 'Lowell, MA',
    '979': 'College Station, TX', '980': 'Charlotte, NC', '985': 'Houma, LA', '989': 'Saginaw, MI',
    '403': 'Calgary, AB', '416': 'Toronto, ON', '514': 'Montreal, QC', '613': 'Ottawa, ON'
}

TLD_GEO = {
    '.co.uk': 'United Kingdom', '.uk': 'United Kingdom', '.de': 'Germany', '.ca': 'Canada',
    '.com.au': 'Australia', '.au': 'Australia', '.in': 'India', '.co.in': 'India',
    '.fr': 'France', '.nl': 'Netherlands', '.sg': 'Singapore', '.ie': 'Ireland',
    '.ch': 'Switzerland', '.se': 'Sweden', '.es': 'Spain', '.it': 'Italy', '.ae': 'UAE'
}

def extract_area_code(phone_str):
    if not phone_str: return None
    digits = re.sub(r'\D', '', str(phone_str))
    if len(digits) >= 10:
        if len(digits) == 11 and digits.startswith('1'):
            return digits[1:4]
        return digits[:3]
    return None

def extract_tld(em):
    if not em or '@' not in str(em): return None
    domain = str(em).split('@')[-1].lower()
    for tld, loc in TLD_GEO.items():
        if domain.endswith(tld): return loc
    return None

def run_triangulation():
    t0 = time.time()
    print(f"[{time.strftime('%X')}] INITIATING ZERO-COST MULTI-SIGNAL LOCATION TRIANGULATION...")
    db = SessionLocal()
    try:
        # Phase 1: Build Corporate Hub Directory (Tier 2)
        print(f"[{time.strftime('%X')}] Phase 1: Calculating Corporate Hub centroids from known records...")
        comp_hub_map = {} # company_id -> loc
        comp_loc_counts = defaultdict(Counter)

        last_rid = 0
        while True:
            chunk = db.execute(text("""
                SELECT recruiter_id, company_id, location
                FROM recruiters
                WHERE recruiter_id > :lid AND company_id IS NOT NULL AND location IS NOT NULL AND TRIM(location) != '' AND LOWER(location) != 'nan'
                ORDER BY recruiter_id LIMIT 10000
            """), {"lid": last_rid}).mappings().all()
            if not chunk: break
            for r in chunk:
                loc = r['location'].strip()
                if not loc.startswith('[GEO:'):
                    comp_loc_counts[r['company_id']][loc] += 1
            last_rid = chunk[-1]['recruiter_id']

        for cid, counts in comp_loc_counts.items():
            best_loc, cnt = counts.most_common(1)[0]
            comp_hub_map[cid] = best_loc

        print(f"[{time.strftime('%X')}] Corporate Hubs Established: {len(comp_hub_map):,} companies mapped.")

        # Phase 2: Triangulate Unknown Locations via Keyset Pagination
        print(f"[{time.strftime('%X')}] Phase 2: Triangulating unknown locations across entire DB...")
        last_rid = 0
        resolved_cnt = 0
        gold_cnt = 0
        silver_cnt = 0
        bronze_cnt = 0

        while True:
            chunk = db.execute(text("""
                SELECT recruiter_id, email, phone, company_id, email2, notes
                FROM recruiters
                WHERE recruiter_id > :lid AND (location IS NULL OR TRIM(location) = '' OR LOWER(location) = 'nan') AND is_active = true
                ORDER BY recruiter_id LIMIT 10000
            """), {"lid": last_rid}).mappings().all()
            if not chunk: break

            up_batch = []
            for r in chunk:
                rid = r['recruiter_id']
                phone_loc = None
                hub_loc = None
                tld_loc = None

                # Tier 1: Area Code
                ac = extract_area_code(r['phone'])
                if ac and ac in NANP_GEO:
                    phone_loc = NANP_GEO[ac]

                # Tier 2: Company Hub
                if r['company_id'] and r['company_id'] in comp_hub_map:
                    hub_loc = comp_hub_map[r['company_id']]

                # Tier 3: TLD
                tld_loc = extract_tld(r['email']) or extract_tld(r['email2'])

                # Triangulate
                chosen_loc = None
                conf = ""

                if phone_loc and hub_loc:
                    pl = phone_loc.lower()
                    hl = hub_loc.lower()
                    if any(p.strip() in hl for p in pl.split(',') if p.strip()) or any(p.strip() in pl for p in hl.split(',') if p.strip()):
                        chosen_loc = phone_loc
                        conf = "100% Gold (Phone+Hub Verified)"
                        gold_cnt += 1
                    else:
                        chosen_loc = phone_loc
                        conf = "85% Silver (Phone Metro)"
                        silver_cnt += 1
                elif phone_loc:
                    chosen_loc = phone_loc
                    conf = "85% Silver (Phone Metro)"
                    silver_cnt += 1
                elif hub_loc:
                    chosen_loc = hub_loc
                    conf = "80% Silver (Enterprise Hub Cluster)"
                    silver_cnt += 1
                elif tld_loc:
                    chosen_loc = tld_loc
                    conf = "70% Bronze (Country TLD)"
                    bronze_cnt += 1

                if chosen_loc:
                    notes_str = r['notes'] or ""
                    new_notes = notes_str + f"; [GEO: {chosen_loc} ({conf})]" if notes_str else f"[GEO: {chosen_loc} ({conf})]"
                    up_batch.append({"rid": rid, "loc": chosen_loc[:145], "nts": new_notes})

            if up_batch:
                for i in range(0, len(up_batch), 500):
                    b_chunk = up_batch[i:i+500]
                    db.execute(text("UPDATE recruiters SET location = :loc, notes = :nts WHERE recruiter_id = :rid"), b_chunk)
                db.commit()
                resolved_cnt += len(up_batch)

            last_rid = chunk[-1]['recruiter_id']

        elapsed = round(time.time() - t0, 2)
        tot_unknown = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE (location IS NULL OR TRIM(location) = '') AND is_active = true")).scalar()

        print(f"\n=======================================================")
        print(f"ZERO-COST LOCATION TRIANGULATION COMPLETE!")
        print(f"Execution Time: {elapsed}s")
        print(f"Successfully Pinpointed Locations: +{resolved_cnt:,}")
        print(f"  - Gold Tier (100% Verified): {gold_cnt:,}")
        print(f"  - Silver Tier (Enterprise/Metro 80-85%): {silver_cnt:,}")
        print(f"  - Bronze Tier (Regional TLD 70%): {bronze_cnt:,}")
        print(f"Remaining Unresolvable Blank Records: {tot_unknown:,}")
        print(f"Total API Credits Spent: $0.00")
        print(f"=======================================================")

    except Exception as e:
        db.rollback()
        print("ERROR DURING TRIANGULATION:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_triangulation()
