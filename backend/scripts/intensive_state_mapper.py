import duckdb
import os
import sys
import time
import shutil
import re
import pandas as pd

os.chdir('C:/TalentOpsAI/backend')

PARQUET_FILE = 'data/recruiters_full.parquet'
TMP_FILE = 'data/recruiters_mapped.parquet'

print("Initializing Intensive State Mapping Engine...")

# US States mapping
STATE_MAP = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'district of columbia': 'DC', 'puerto rico': 'PR', 'remote': 'REMOTE'
}

# Major US Cities mapping to State
CITY_MAP = {
    'new york': 'NY', 'los angeles': 'CA', 'chicago': 'IL', 'houston': 'TX', 'phoenix': 'AZ',
    'philadelphia': 'PA', 'san antonio': 'TX', 'san diego': 'CA', 'dallas': 'TX', 'san jose': 'CA',
    'austin': 'TX', 'jacksonville': 'FL', 'fort worth': 'TX', 'columbus': 'OH', 'charlotte': 'NC',
    'san francisco': 'CA', 'indianapolis': 'IN', 'seattle': 'WA', 'denver': 'CO', 'washington': 'DC',
    'boston': 'MA', 'el paso': 'TX', 'nashville': 'TN', 'detroit': 'MI', 'oklahoma city': 'OK',
    'portland': 'OR', 'las vegas': 'NV', 'memphis': 'TN', 'louisville': 'KY', 'baltimore': 'MD',
    'milwaukee': 'WI', 'albuquerque': 'NM', 'tucson': 'AZ', 'fresno': 'CA', 'mesa': 'AZ',
    'sacramento': 'CA', 'atlanta': 'GA', 'kansas city': 'MO', 'colorado springs': 'CO', 'miami': 'FL',
    'raleigh': 'NC', 'omaha': 'NE', 'long beach': 'CA', 'virginia beach': 'VA', 'oakland': 'CA',
    'minneapolis': 'MN', 'tulsa': 'OK', 'arlington': 'TX', 'tampa': 'FL', 'new orleans': 'LA',
    'wichita': 'KS', 'bakersfield': 'CA', 'cleveland': 'OH', 'aurora': 'CO', 'anaheim': 'CA',
    'honolulu': 'HI', 'santa ana': 'CA', 'riverside': 'CA', 'corpus christi': 'TX', 'lexington': 'KY',
    'henderson': 'NV', 'stockton': 'CA', 'st. paul': 'MN', 'cincinnati': 'OH', 'st. louis': 'MO',
    'pittsburgh': 'PA', 'greensboro': 'NC', 'lincoln': 'NE', 'anchorage': 'AK', 'plano': 'TX',
    'orlando': 'FL', 'irvine': 'CA', 'newark': 'NJ', 'durham': 'NC', 'chula vista': 'CA',
    'toledo': 'OH', 'fort wayne': 'IN', 'st. petersburg': 'FL', 'laredo': 'TX', 'jersey city': 'NJ',
    'chandler': 'AZ', 'madison': 'WI', 'lubbock': 'TX', 'scottsdale': 'AZ', 'reno': 'NV',
    'buffalo': 'NY', 'gilbert': 'AZ', 'glendale': 'AZ', 'north las vegas': 'NV', 'winston-salem': 'NC',
    'chesapeake': 'VA', 'norfolk': 'VA', 'fremont': 'CA', 'garland': 'TX', 'irving': 'TX',
    'hialeah': 'FL', 'arlington': 'VA', 'richmond': 'VA', 'boise': 'ID', 'baton rouge': 'LA'
}

# Simplified Area Code to State mapping (covering most major areas)
AREA_CODES = {
    '201': 'NJ', '202': 'DC', '203': 'CT', '205': 'AL', '206': 'WA', '207': 'ME', '208': 'ID', '209': 'CA',
    '210': 'TX', '212': 'NY', '213': 'CA', '214': 'TX', '215': 'PA', '216': 'OH', '217': 'IL', '218': 'MN',
    '219': 'IN', '224': 'IL', '225': 'LA', '228': 'MS', '229': 'GA', '231': 'MI', '234': 'OH', '239': 'FL',
    '240': 'MD', '248': 'MI', '251': 'AL', '252': 'NC', '253': 'WA', '254': 'TX', '256': 'AL', '260': 'IN',
    '262': 'WI', '267': 'PA', '269': 'MI', '270': 'KY', '276': 'VA', '281': 'TX', '301': 'MD', '302': 'DE',
    '303': 'CO', '304': 'WV', '305': 'FL', '307': 'WY', '308': 'NE', '309': 'IL', '310': 'CA', '312': 'IL',
    '313': 'MI', '314': 'MO', '315': 'NY', '316': 'KS', '317': 'IN', '318': 'LA', '319': 'IA', '320': 'MN',
    '321': 'FL', '323': 'CA', '325': 'TX', '330': 'OH', '334': 'AL', '336': 'NC', '337': 'LA', '339': 'MA',
    '347': 'NY', '351': 'MA', '352': 'FL', '360': 'WA', '361': 'TX', '386': 'FL', '401': 'RI', '402': 'NE',
    '404': 'GA', '405': 'OK', '406': 'MT', '407': 'FL', '408': 'CA', '409': 'TX', '410': 'MD', '412': 'PA',
    '413': 'MA', '414': 'WI', '415': 'CA', '417': 'MO', '419': 'OH', '423': 'TN', '424': 'CA', '425': 'WA',
    '430': 'TX', '432': 'TX', '434': 'VA', '435': 'UT', '440': 'OH', '443': 'MD', '469': 'TX', '478': 'GA',
    '479': 'AR', '480': 'AZ', '484': 'PA', '501': 'AR', '502': 'KY', '503': 'OR', '504': 'LA', '505': 'NM',
    '507': 'MN', '508': 'MA', '509': 'WA', '510': 'CA', '512': 'TX', '513': 'OH', '515': 'IA', '516': 'NY',
    '517': 'MI', '518': 'NY', '520': 'AZ', '530': 'CA', '540': 'VA', '541': 'OR', '551': 'NJ', '559': 'CA',
    '561': 'FL', '562': 'CA', '563': 'IA', '570': 'PA', '571': 'VA', '573': 'MO', '574': 'IN', '580': 'OK',
    '585': 'NY', '586': 'MI', '601': 'MS', '602': 'AZ', '603': 'NH', '605': 'SD', '606': 'KY', '607': 'NY',
    '608': 'WI', '609': 'NJ', '610': 'PA', '612': 'MN', '614': 'OH', '615': 'TN', '616': 'MI', '617': 'MA',
    '618': 'IL', '619': 'CA', '620': 'KS', '623': 'AZ', '626': 'CA', '630': 'IL', '631': 'NY', '636': 'MO',
    '646': 'NY', '650': 'CA', '651': 'MN', '661': 'CA', '662': 'MS', '678': 'GA', '682': 'TX', '701': 'ND',
    '702': 'NV', '703': 'VA', '704': 'NC', '706': 'GA', '707': 'CA', '708': 'IL', '712': 'IA', '713': 'TX',
    '714': 'CA', '715': 'WI', '716': 'NY', '717': 'PA', '718': 'NY', '719': 'CO', '720': 'CO', '724': 'PA',
    '727': 'FL', '732': 'NJ', '734': 'MI', '740': 'OH', '757': 'VA', '760': 'CA', '765': 'IN', '770': 'GA',
    '772': 'FL', '773': 'IL', '774': 'MA', '775': 'NV', '781': 'MA', '785': 'KS', '786': 'FL', '787': 'PR',
    '801': 'UT', '802': 'VT', '803': 'SC', '804': 'VA', '805': 'CA', '806': 'TX', '808': 'HI', '810': 'MI',
    '812': 'IN', '813': 'FL', '814': 'PA', '815': 'IL', '816': 'MO', '817': 'TX', '818': 'CA', '828': 'NC',
    '831': 'CA', '832': 'TX', '843': 'SC', '845': 'NY', '847': 'IL', '850': 'FL', '856': 'NJ', '858': 'CA',
    '859': 'KY', '860': 'CT', '862': 'NJ', '863': 'FL', '864': 'SC', '865': 'TN', '870': 'AR', '901': 'TN',
    '903': 'TX', '904': 'FL', '906': 'MI', '907': 'AK', '908': 'NJ', '909': 'CA', '910': 'NC', '912': 'GA',
    '913': 'KS', '914': 'NY', '915': 'TX', '916': 'CA', '917': 'NY', '918': 'OK', '919': 'NC', '920': 'WI',
    '925': 'CA', '928': 'AZ', '931': 'TN', '936': 'TX', '937': 'OH', '940': 'TX', '941': 'FL', '947': 'MI',
    '949': 'CA', '951': 'CA', '952': 'MN', '954': 'FL', '956': 'TX', '970': 'CO', '971': 'OR', '972': 'TX',
    '973': 'NJ', '978': 'MA', '979': 'TX', '980': 'NC', '985': 'LA', '989': 'MI'
}

print("Loading data into Pandas to apply mapping functions...")
con = duckdb.connect()
df = con.execute(f"SELECT * FROM read_parquet('{PARQUET_FILE}')").df()

valid_states = set(STATE_MAP.values())

def map_state(row):
    # Tier 1: Explicit state column
    if row.get('state') and str(row['state']).upper() in valid_states:
        return str(row['state']).upper(), 'existing_state'
    
    # Tier 2: Location string parsing
    loc = str(row.get('location', '')).lower() if row.get('location') else ''
    if loc and loc != 'nan':
        # Check explicit state abbreviation matching ', TX' or ', NY'
        match = re.search(r',\s*([a-z]{2})\b', loc)
        if match:
            st = match.group(1).upper()
            if st in valid_states:
                return st, 'location_regex'
        
        # Check full state name
        for state_name, state_abbr in STATE_MAP.items():
            if state_name in loc:
                return state_abbr, 'location_state_name'
                
        # Check major city
        for city_name, state_abbr in CITY_MAP.items():
            if city_name in loc:
                return state_abbr, 'location_city_name'

    # Tier 3: Phone area code
    phone = str(row.get('phone', '')) if row.get('phone') else ''
    if phone and phone != 'nan':
        # extract first 3 digits that are not 1
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('1') and len(digits) > 10:
            digits = digits[1:]
        if len(digits) >= 10:
            area_code = digits[:3]
            if area_code in AREA_CODES:
                return AREA_CODES[area_code], 'phone_area_code'

    return None, None

print(f"Total rows to map: {len(df)}")
start_time = time.time()

# Apply mapping
def apply_mapping(row):
    state, source = map_state(row)
    if state:
        return state, source
    existing = str(row.get('state')).upper().strip() if row.get('state') else None
    if existing and existing in valid_states:
        return existing, row.get('state_source')
    return None, None

mapped = df.apply(apply_mapping, axis=1)
df['state'] = [x[0] for x in mapped]
df['state_source'] = [x[1] for x in mapped]

print(f"Mapping logic completed in {time.time() - start_time:.2f} seconds.")

# Now for Tier 4: Company HQ Fallback
# Connect to PostgreSQL to get company states
print("Connecting to PostgreSQL to fetch company HQs...")
from sqlalchemy import create_engine, text
DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL)
with engine.connect() as pg_conn:
    company_states = {}
    rows = pg_conn.execute(text("SELECT company_id, state FROM companies WHERE state IS NOT NULL AND state != ''")).fetchall()
    for row in rows:
        company_states[row[0]] = row[1].upper()

print(f"Fetched {len(company_states)} company states.")

def apply_hq_fallback(row):
    if not row.get('state') or str(row.get('state')).lower() == 'nan':
        cid = row.get('company_id')
        if not pd.isna(cid):
            try:
                cid = int(cid)
                if cid in company_states:
                    st = company_states[cid]
                    if st in valid_states:
                        return st, 'company_hq_fallback'
            except (ValueError, TypeError):
                pass
    
    existing = str(row.get('state')).upper().strip() if row.get('state') else None
    if existing and existing in valid_states:
        return existing, row.get('state_source')
    return None, None

start_time = time.time()
mapped_hq = df.apply(apply_hq_fallback, axis=1)
df['state'] = [x[0] for x in mapped_hq]
df['state_source'] = [x[1] for x in mapped_hq]

print(f"HQ Fallback completed in {time.time() - start_time:.2f} seconds.")

# Clean up states (ensure they are only 2 letters or null if invalid)
def clean_state(s):
    if pd.isna(s): return None
    s = str(s).strip().upper()
    if s in valid_states: return s
    return None

df['state'] = df['state'].apply(clean_state)

print("Writing mapped dataset to new Parquet file...")
print(df['state_source'].value_counts())
import pyarrow as pa
import pyarrow.parquet as pq

# Drop the duckdb connection just to be safe
con.close()
df.to_parquet(TMP_FILE, engine='pyarrow', compression='zstd')

# Replace original
shutil.move(TMP_FILE, PARQUET_FILE)
print("Mapping Complete! Reloading store...")

import sys
sys.path.append('C:/TalentOpsAI/backend')
from app.services.recruiter_store import recruiter_store
recruiter_store.reload()

print("Triggering upload to Supabase...")
import subprocess
subprocess.run([sys.executable, 'scripts/upload_real_parquet.py'])
print("Upload complete!")
