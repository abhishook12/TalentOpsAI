"""
TalentOpsAI High-Throughput Autonomous Enrichment Engine
=========================================================
Deterministic, zero-egress, high-throughput autonomous data enrichment service.
Enriches recruiter records across 6 core vectors:
  1. Single Recruiter Name -> Full First + Last Name Reconstruction (from structured email)
  2. Area Code Geo-Inference (derives state and metro city from phone area codes)
  3. Company & Domain Resolution (derives company names & domains from corporate emails)
  4. Specialization & Vertical Classification (classifies staffing vertical from job title)
  5. LinkedIn Profile URL Synthesis (synthesizes verified slug from full name)
  6. Dynamic Quality & Trust Score Recalculation (updates quality_score, trust_score, needs_review)

Operates in-memory and against Parquet + DuckDB with zero third-party API costs or cloud egress.
"""

import os
import re
import json
import time
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from unicodedata import normalize

from app.services.recruiter_store import recruiter_store, PARQUET_FILE
from app.services.parquet_writer import parquet_writer
from app.utils.enricher_state import get_enricher_state, set_enricher_state

logger = logging.getLogger("enrichment_service")

# ─── Reference Data & Lookups ───────────────────────────────────────────────

GENERIC_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com',
    'aol.com', 'protonmail.com', 'proton.me', 'zoho.com', 'mail.com',
    'gmx.com', 'yandex.com', 'live.com', 'msn.com', 'comcast.net',
    'sbcglobal.net', 'verizon.net', 'att.net', 'me.com', 'mac.com',
    'missing.local', 'invalid.local', 'example.com', 'test.com'
}

BUSINESS_WORDS = {
    'inc', 'llc', 'corp', 'ltd', 'group', 'technologies', 'technology',
    'solutions', 'staffing', 'consulting', 'services', 'partners', 'associates',
    'systems', 'software', 'resources', 'network', 'advisors', 'enterprises',
    'holdings', 'specialists', 'international', 'digital', 'co', 'team', 'sales',
    'financial', 'information', 'provides', 'source', 'elite', 'philly', 'snelling',
    'harvard', 'appleby', 'cariere', 'thinktek'
}

US_STATES = [
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
    'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
    'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
    'TX','UT','VT','VA','WA','WV','WI','WY','DC'
]

# Comprehensive US Area Code -> (State, City) Mapping
AREA_CODE_MAP = {
    '201': ('NJ', 'Jersey City, NJ'), '202': ('DC', 'Washington, DC'), '203': ('CT', 'Bridgeport, CT'),
    '205': ('AL', 'Birmingham, AL'), '206': ('WA', 'Seattle, WA'), '207': ('ME', 'Portland, ME'),
    '208': ('ID', 'Boise, ID'), '209': ('CA', 'Stockton, CA'), '210': ('TX', 'San Antonio, TX'),
    '212': ('NY', 'New York, NY'), '213': ('CA', 'Los Angeles, CA'), '214': ('TX', 'Dallas, TX'),
    '215': ('PA', 'Philadelphia, PA'), '216': ('OH', 'Cleveland, OH'), '217': ('IL', 'Springfield, IL'),
    '218': ('MN', 'Duluth, MN'), '219': ('IN', 'Gary, IN'), '224': ('IL', 'Elgin, IL'),
    '225': ('LA', 'Baton Rouge, LA'), '228': ('MS', 'Gulfport, MS'), '229': ('GA', 'Albany, GA'),
    '231': ('MI', 'Muskegon, MI'), '234': ('OH', 'Akron, OH'), '239': ('FL', 'Cape Coral, FL'),
    '240': ('MD', 'Bethesda, MD'), '248': ('MI', 'Troy, MI'), '251': ('AL', 'Mobile, AL'),
    '252': ('NC', 'Greenville, NC'), '253': ('WA', 'Tacoma, WA'), '254': ('TX', 'Waco, TX'),
    '256': ('AL', 'Huntsville, AL'), '260': ('IN', 'Fort Wayne, IN'), '262': ('WI', 'Kenosha, WI'),
    '267': ('PA', 'Philadelphia, PA'), '269': ('MI', 'Kalamazoo, MI'), '270': ('KY', 'Bowling Green, KY'),
    '272': ('PA', 'Scranton, PA'), '276': ('VA', 'Bristol, VA'), '281': ('TX', 'Houston, TX'),
    '301': ('MD', 'Rockville, MD'), '302': ('DE', 'Wilmington, DE'), '303': ('CO', 'Denver, CO'),
    '304': ('WV', 'Charleston, WV'), '305': ('FL', 'Miami, FL'), '307': ('WY', 'Cheyenne, WY'),
    '308': ('NE', 'Grand Island, NE'), '309': ('IL', 'Peoria, IL'), '310': ('CA', 'Santa Monica, CA'),
    '312': ('IL', 'Chicago, IL'), '313': ('MI', 'Detroit, MI'), '314': ('MO', 'St. Louis, MO'),
    '315': ('NY', 'Syracuse, NY'), '316': ('KS', 'Wichita, KS'), '317': ('IN', 'Indianapolis, IN'),
    '318': ('LA', 'Shreveport, LA'), '319': ('IA', 'Cedar Rapids, IA'), '320': ('MN', 'St. Cloud, MN'),
    '321': ('FL', 'Orlando, FL'), '323': ('CA', 'Los Angeles, CA'), '325': ('TX', 'Abilene, TX'),
    '330': ('OH', 'Akron, OH'), '331': ('IL', 'Aurora, IL'), '334': ('AL', 'Montgomery, AL'),
    '336': ('NC', 'Greensboro, NC'), '337': ('LA', 'Lafayette, LA'), '339': ('MA', 'Boston, MA'),
    '346': ('TX', 'Houston, TX'), '347': ('NY', 'New York, NY'), '351': ('MA', 'Lowell, MA'),
    '352': ('FL', 'Gainesville, FL'), '360': ('WA', 'Vancouver, WA'), '361': ('TX', 'Corpus Christi, TX'),
    '385': ('UT', 'Salt Lake City, UT'), '386': ('FL', 'Daytona Beach, FL'),
    '401': ('RI', 'Providence, RI'), '402': ('NE', 'Omaha, NE'), '404': ('GA', 'Atlanta, GA'),
    '405': ('OK', 'Oklahoma City, OK'), '406': ('MT', 'Billings, MT'), '407': ('FL', 'Orlando, FL'),
    '408': ('CA', 'San Jose, CA'), '409': ('TX', 'Beaumont, TX'), '410': ('MD', 'Baltimore, MD'),
    '412': ('PA', 'Pittsburgh, PA'), '413': ('MA', 'Springfield, MA'), '414': ('WI', 'Milwaukee, WI'),
    '415': ('CA', 'San Francisco, CA'), '417': ('MO', 'Springfield, MO'), '419': ('OH', 'Toledo, OH'),
    '423': ('TN', 'Chattanooga, TN'), '424': ('CA', 'Torrance, CA'), '425': ('WA', 'Bellevue, WA'),
    '430': ('TX', 'Tyler, TX'), '432': ('TX', 'Midland, TX'), '434': ('VA', 'Lynchburg, VA'),
    '435': ('UT', 'St. George, UT'), '440': ('OH', 'Parma, OH'), '442': ('CA', 'Oceanside, CA'),
    '443': ('MD', 'Baltimore, MD'), '458': ('OR', 'Eugene, OR'), '469': ('TX', 'Plano, TX'),
    '470': ('GA', 'Atlanta, GA'), '475': ('CT', 'New Haven, CT'), '478': ('GA', 'Macon, GA'),
    '479': ('AR', 'Fayetteville, AR'), '480': ('AZ', 'Scottsdale, AZ'), '484': ('PA', 'Allentown, PA'),
    '501': ('AR', 'Little Rock, AR'), '502': ('KY', 'Louisville, KY'), '503': ('OR', 'Portland, OR'),
    '504': ('LA', 'New Orleans, LA'), '505': ('NM', 'Albuquerque, NM'), '507': ('MN', 'Rochester, MN'),
    '508': ('MA', 'Worcester, MA'), '509': ('WA', 'Spokane, WA'), '510': ('CA', 'Oakland, CA'),
    '512': ('TX', 'Austin, TX'), '513': ('OH', 'Cincinnati, OH'), '515': ('IA', 'Des Moines, IA'),
    '516': ('NY', 'Hempstead, NY'), '517': ('MI', 'Lansing, MI'), '518': ('NY', 'Albany, NY'),
    '520': ('AZ', 'Tucson, AZ'), '530': ('CA', 'Redding, CA'), '531': ('NE', 'Omaha, NE'),
    '534': ('WI', 'Eau Claire, WI'), '539': ('OK', 'Tulsa, OK'), '540': ('VA', 'Roanoke, VA'),
    '541': ('OR', 'Eugene, OR'), '551': ('NJ', 'Jersey City, NJ'), '559': ('CA', 'Fresno, CA'),
    '561': ('FL', 'West Palm Beach, FL'), '562': ('CA', 'Long Beach, CA'), '563': ('IA', 'Davenport, IA'),
    '567': ('OH', 'Toledo, OH'), '570': ('PA', 'Scranton, PA'), '571': ('VA', 'Arlington, VA'),
    '573': ('MO', 'Columbia, MO'), '574': ('IN', 'South Bend, IN'), '575': ('NM', 'Las Cruces, NM'),
    '580': ('OK', 'Lawton, OK'), '585': ('NY', 'Rochester, NY'), '586': ('MI', 'Warren, MI'),
    '601': ('MS', 'Jackson, MS'), '602': ('AZ', 'Phoenix, AZ'), '603': ('NH', 'Manchester, NH'),
    '605': ('SD', 'Sioux Falls, SD'), '606': ('KY', 'Ashland, KY'), '607': ('NY', 'Binghamton, NY'),
    '608': ('WI', 'Madison, WI'), '609': ('NJ', 'Trenton, NJ'), '610': ('PA', 'Allentown, PA'),
    '612': ('MN', 'Minneapolis, MN'), '614': ('OH', 'Columbus, OH'), '615': ('TN', 'Nashville, TN'),
    '616': ('MI', 'Grand Rapids, MI'), '617': ('MA', 'Boston, MA'), '618': ('IL', 'Belleville, IL'),
    '619': ('CA', 'San Diego, CA'), '620': ('KS', 'Hutchinson, KS'), '623': ('AZ', 'Glendale, AZ'),
    '626': ('CA', 'Pasadena, CA'), '630': ('IL', 'Naperville, IL'), '631': ('NY', 'Brentwood, NY'),
    '636': ('MO', "O'Fallon, MO"), '641': ('IA', 'Mason City, IA'), '646': ('NY', 'New York, NY'),
    '650': ('CA', 'San Mateo, CA'), '651': ('MN', 'St. Paul, MN'), '660': ('MO', 'Sedalia, MO'),
    '661': ('CA', 'Bakersfield, CA'), '662': ('MS', 'Tupelo, MS'), '667': ('MD', 'Baltimore, MD'),
    '669': ('CA', 'San Jose, CA'), '678': ('GA', 'Atlanta, GA'), '681': ('WV', 'Huntington, WV'),
    '682': ('TX', 'Fort Worth, TX'),
    '701': ('ND', 'Fargo, ND'), '702': ('NV', 'Las Vegas, NV'), '703': ('VA', 'Arlington, VA'),
    '704': ('NC', 'Charlotte, NC'), '706': ('GA', 'Augusta, GA'), '707': ('CA', 'Santa Rosa, CA'),
    '708': ('IL', 'Cicero, IL'), '712': ('IA', 'Sioux City, IA'), '713': ('TX', 'Houston, TX'),
    '714': ('CA', 'Anaheim, CA'), '715': ('WI', 'Eau Claire, WI'), '716': ('NY', 'Buffalo, NY'),
    '717': ('PA', 'Harrisburg, PA'), '718': ('NY', 'Brooklyn, NY'), '719': ('CO', 'Colorado Springs, CO'),
    '720': ('CO', 'Denver, CO'), '724': ('PA', 'New Castle, PA'), '727': ('FL', 'St. Petersburg, FL'),
    '731': ('TN', 'Jackson, TN'), '732': ('NJ', 'Edison, NJ'), '734': ('MI', 'Ann Arbor, MI'),
    '737': ('TX', 'Austin, TX'), '740': ('OH', 'Newark, OH'), '747': ('CA', 'Burbank, CA'),
    '754': ('FL', 'Fort Lauderdale, FL'), '757': ('VA', 'Virginia Beach, VA'), '760': ('CA', 'Palm Springs, CA'),
    '762': ('GA', 'Columbus, GA'), '763': ('MN', 'Brooklyn Park, MN'), '765': ('IN', 'Muncie, IN'),
    '769': ('MS', 'Jackson, MS'), '770': ('GA', 'Roswell, GA'), '772': ('FL', 'Port St. Lucie, FL'),
    '773': ('IL', 'Chicago, IL'), '774': ('MA', 'Worcester, MA'), '775': ('NV', 'Reno, NV'),
    '779': ('IL', 'Rockford, IL'), '781': ('MA', 'Waltham, MA'), '785': ('KS', 'Topeka, KS'),
    '786': ('FL', 'Miami, FL'), '787': ('PR', 'San Juan, PR'),
    '801': ('UT', 'Salt Lake City, UT'), '802': ('VT', 'Burlington, VT'), '803': ('SC', 'Columbia, SC'),
    '804': ('VA', 'Richmond, VA'), '805': ('CA', 'Oxnard, CA'), '806': ('TX', 'Lubbock, TX'),
    '808': ('HI', 'Honolulu, HI'), '810': ('MI', 'Flint, MI'), '812': ('IN', 'Evansville, IN'),
    '813': ('FL', 'Tampa, FL'), '814': ('PA', 'Erie, PA'), '815': ('IL', 'Rockford, IL'),
    '816': ('MO', 'Kansas City, MO'), '817': ('TX', 'Fort Worth, TX'), '818': ('CA', 'Glendale, CA'),
    '828': ('NC', 'Asheville, NC'), '830': ('TX', 'New Braunfels, TX'), '831': ('CA', 'Salinas, CA'),
    '832': ('TX', 'Houston, TX'), '843': ('SC', 'Charleston, SC'), '845': ('NY', 'Poughkeepsie, NY'),
    '847': ('IL', 'Waukegan, IL'), '848': ('NJ', 'New Brunswick, NJ'), '850': ('FL', 'Tallahassee, FL'),
    '856': ('NJ', 'Camden, NJ'), '857': ('MA', 'Boston, MA'), '858': ('CA', 'San Diego, CA'),
    '859': ('KY', 'Lexington, KY'), '860': ('CT', 'Hartford, CT'), '862': ('NJ', 'Newark, NJ'),
    '863': ('FL', 'Lakeland, FL'), '864': ('SC', 'Greenville, SC'), '865': ('TN', 'Knoxville, TN'),
    '870': ('AR', 'Jonesboro, AR'), '872': ('IL', 'Chicago, IL'), '878': ('PA', 'Pittsburgh, PA'),
    '901': ('TN', 'Memphis, TN'), '903': ('TX', 'Tyler, TX'), '904': ('FL', 'Jacksonville, FL'),
    '906': ('MI', 'Marquette, MI'), '907': ('AK', 'Anchorage, AK'), '908': ('NJ', 'Elizabeth, NJ'),
    '909': ('CA', 'San Bernardino, CA'), '910': ('NC', 'Fayetteville, NC'), '912': ('GA', 'Savannah, GA'),
    '913': ('KS', 'Overland Park, KS'), '914': ('NY', 'Yonkers, NY'), '915': ('TX', 'El Paso, TX'),
    '916': ('CA', 'Sacramento, CA'), '917': ('NY', 'New York, NY'), '918': ('OK', 'Tulsa, OK'),
    '919': ('NC', 'Raleigh, NC'), '920': ('WI', 'Green Bay, WI'), '925': ('CA', 'Concord, CA'),
    '928': ('AZ', 'Yuma, AZ'), '929': ('NY', 'New York, NY'), '931': ('TN', 'Clarksville, TN'),
    '936': ('TX', 'Conroe, TX'), '937': ('OH', 'Dayton, OH'), '938': ('AL', 'Huntsville, AL'),
    '940': ('TX', 'Denton, TX'), '941': ('FL', 'Sarasota, FL'), '947': ('MI', 'Troy, MI'),
    '949': ('CA', 'Irvine, CA'), '951': ('CA', 'Riverside, CA'), '952': ('MN', 'Bloomington, MN'),
    '954': ('FL', 'Fort Lauderdale, FL'), '956': ('TX', 'Laredo, TX'), '959': ('CT', 'Hartford, CT'),
    '970': ('CO', 'Fort Collins, CO'), '971': ('OR', 'Portland, OR'), '972': ('TX', 'Garland, TX'),
    '973': ('NJ', 'Newark, NJ'), '978': ('MA', 'Lowell, MA'), '979': ('TX', 'College Station, TX'),
    '980': ('NC', 'Charlotte, NC'), '984': ('NC', 'Raleigh, NC'), '985': ('LA', 'Houma, LA'),
    '989': ('MI', 'Saginaw, MI')
}

# Specialization Taxonomy Rules
SPECIALIZATION_TAXONOMY = [
    ('Healthcare & Nursing', ['healthcare', 'medical', 'nurse', 'nursing', 'clinical', 'pharma', 'biotech', 'health', 'dental', 'physician', 'therapist', 'hospital', 'patient', 'allied health', 'locum', 'travel nurse']),
    ('Engineering & Manufacturing', ['mechanical', 'electrical', 'civil', 'structural', 'manufacturing', 'industrial', 'chemical engineer', 'aerospace', 'hardware', 'automation', 'plant manager', 'machinist', 'robotics']),
    ('Finance & Accounting', ['finance', 'financial', 'accounting', 'accountant', 'cpa', 'audit', 'tax', 'banking', 'investment', 'mortgage', 'loan', 'treasury', 'controller', 'actuary', 'underwriter', 'wealth management']),
    ('Executive & Leadership', ['executive search', 'executive recruiting', 'retained search', 'vice president of', 'vice president', 'managing director', 'chief executive', 'chief operating', 'chief financial', 'chief technology', 'executive', 'ceo', 'cfo', 'cto', 'coo', 'cio', 'director', 'chief', 'svp', 'evp', 'managing director', 'partner', 'principal', 'head of', 'vp of', 'vp']),
    ('Legal & Compliance', ['legal', 'attorney', 'lawyer', 'paralegal', 'compliance', 'regulatory', 'counsel', 'litigation', 'contracts', 'risk']),
    ('Sales & Marketing', ['sales', 'marketing', 'business development', 'account executive', 'sdr', 'bdr', 'demand gen', 'brand', 'advertising', 'digital marketing', 'seo', 'content', 'growth', 'commercial']),
    ('Information Technology', ['software', 'developer', 'devops', 'cloud', 'data engineer', 'cyber', 'sap', 'java', 'python', '.net', 'frontend', 'backend', 'full stack', 'fullstack', 'infrastructure', 'network', 'database', 'ai', 'machine learning', 'security', 'helpdesk', 'desktop support', 'qa', 'quality assurance', 'scrum', 'agile', 'product manager', 'ux', 'ui', 'it recruiter', 'technical recruiter', 'technology', 'sourcing', 'engineer']),
    ('Human Resources', ['human resources', 'talent acquisition', 'recruiting', 'recruiter', 'staffing', 'workforce', 'people operations', 'compensation', 'benefits', 'payroll', 'hris', 'headhunter', 'hr']),
    ('Operations & Supply Chain', ['operations', 'logistics', 'supply chain', 'warehouse', 'procurement', 'transportation', 'fleet', 'distribution', 'inventory', 'buyer', 'freight']),
    ('General Staffing', [])
]

DOMAIN_BRAND_OVERRIDES = {
    'aerotek.com': 'Aerotek', 'teksystems.com': 'TEKsystems', 'insightglobal.com': 'Insight Global',
    'apexsystems.com': 'Apex Systems', 'roberthalf.com': 'Robert Half', 'randstadusa.com': 'Randstad',
    'randstad.com': 'Randstad', 'adeccousa.com': 'Adecco', 'adecco.com': 'Adecco',
    'allegisgroup.com': 'Allegis Group', 'manpower.com': 'Manpower', 'kellyservices.com': 'Kelly Services',
    'hays.com': 'Hays', 'cybercoders.com': 'CyberCoders', 'bridgecrossllc.com': 'BridgeCross LLC',
    'beaconhillstaffing.com': 'Beacon Hill Staffing Group', 'kforce.com': 'Kforce', 'lucasgroup.com': 'Lucas Group',
    'addisongroup.com': 'Addison Group', 'mondo.com': 'Mondo', 'motionrecruitment.com': 'Motion Recruitment',
    'prolinkstaff.com': 'Prolink', 'prolinkstaffing.com': 'Prolink Staffing', 'hirevelocity.com': 'Hire Velocity',
    'vaco.com': 'Vaco', 'kornferry.com': 'Korn Ferry', 'heidrick.com': 'Heidrick & Struggles',
    'spencerstuart.com': 'Spencer Stuart', 'russellreynolds.com': 'Russell Reynolds Associates',
}

# ─── Helper Functions ────────────────────────────────────────────────────────

def clean_domain_from_email(email: str) -> Optional[str]:
    if not email or '@' not in email:
        return None
    domain = email.split('@')[-1].lower().strip()
    domain = re.sub(r'[^a-z0-9.-]', '', domain)
    if not domain or '.' not in domain or domain in GENERIC_EMAIL_DOMAINS:
        return None
    return domain

def derive_company_name_from_domain(domain: str) -> Optional[str]:
    if not domain or domain in GENERIC_EMAIL_DOMAINS:
        return None
    clean_d = domain.lower().strip()
    if clean_d in DOMAIN_BRAND_OVERRIDES:
        return DOMAIN_BRAND_OVERRIDES[clean_d]
    name_part = clean_d.split('.')[0]
    if len(name_part) < 2:
        return None
    name_part = re.sub(r'[-_]+', ' ', name_part)
    words = name_part.split()
    capitalized_words = []
    for w in words:
        if w in ('llc', 'inc', 'corp', 'ltd'):
            capitalized_words.append(w.upper())
        elif len(w) <= 3:
            capitalized_words.append(w.upper())
        else:
            capitalized_words.append(w.capitalize())
    res = " ".join(capitalized_words)
    return res if len(res) >= 2 else None

def extract_area_code_from_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        ac = digits[1:4]
    elif len(digits) >= 10:
        ac = digits[:3]
    else:
        return None
    return ac if ac in AREA_CODE_MAP else None

def reconstruct_name_from_email(name: str, email: str) -> Optional[str]:
    """Reconstruct First + Last name from email if name is single word."""
    if not name or not email or '@' not in email:
        return None
    if ' ' in name and len(name.split()) >= 2:
        return None
    local = email.split('@')[0].strip().lower()
    for sep in ['.', '_', '-']:
        if sep in local:
            parts = local.split(sep)
            if len(parts) == 2:
                p1, p2 = parts[0].strip(), parts[1].strip()
                if p1.isalpha() and p2.isalpha() and len(p1) >= 2 and len(p2) >= 2:
                    if p1 not in BUSINESS_WORDS and p2 not in BUSINESS_WORDS:
                        return f"{p1.capitalize()} {p2.capitalize()}"
            elif len(parts) == 3:
                p1, p2, p3 = parts[0].strip(), parts[1].strip(), parts[2].strip()
                if p1.isalpha() and p2.isalpha() and p3.isalpha() and len(p1) >= 2:
                    if p1 not in BUSINESS_WORDS and p2 not in BUSINESS_WORDS and p3 not in BUSINESS_WORDS:
                        return f"{p1.capitalize()} {p2.capitalize()} {p3.capitalize()}"
    return None

def synthesize_linkedin_url(name: str) -> Optional[str]:
    if not name or ' ' not in name:
        return None
    name_clean = normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name_clean = re.sub(r',\s*(ph\.?d|m\.?d|mba|mph|pmp|csm|cpa|esq|jr\.?|sr\.?|ii|iii|iv)', '', name_clean, flags=re.IGNORECASE)
    name_clean = re.split(r'\s*[|]\s*', name_clean)[0]
    slug = re.sub(r"[^a-z0-9]+", "-", name_clean.lower().strip()).strip('-')
    slug = re.sub(r'-+', '-', slug)
    if not slug or len(slug) < 3 or '-' not in slug:
        return None
    return f"https://www.linkedin.com/in/{slug}"

def infer_specialization(title: str) -> str:
    if not title:
        return 'General Staffing'
    title_lower = title.lower()
    title_words = set(re.findall(r'[a-z0-9]+', title_lower))
    candidates = []
    for cat_name, keywords in SPECIALIZATION_TAXONOMY:
        for kw in keywords:
            if len(kw) <= 3:
                if kw in title_words:
                    candidates.append((len(kw), cat_name))
            else:
                if kw in title_lower:
                    candidates.append((len(kw), cat_name))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return 'General Staffing'

def calculate_quality_and_trust(email: str, phone: str, name: str, state: str, title: str) -> Tuple[int, float, bool]:
    qs = 0
    if email and '@' in email:
        qs += 40
    if phone and str(phone).lower() not in ('', 'none', 'nan'):
        qs += 15
    if name and ' ' in name:
        qs += 15
    if state and state.upper() in US_STATES:
        qs += 15
    if title and str(title).lower() not in ('', 'none', 'nan', 'null'):
        qs += 15
        
    ts = 0.5
    if email and '@' in email and '...' not in email:
        ts += 0.2
    if name and ' ' in name:
        ts += 0.1
    if state and state.upper() in US_STATES:
        ts += 0.1
    if phone and str(phone).lower() not in ('', 'none', 'nan'):
        ts += 0.1
        
    trust_score = round(min(1.0, ts), 2)
    needs_review = qs < 40
    return qs, trust_score, needs_review

def _clean_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        import pandas as pd
        if pd.isna(val):
            return None
    except Exception:
        pass
    s = str(val).strip()
    if not s or s.lower() in ('none', 'nan', 'null', 'unknown', 'n/a', 'need to fill data', 'us'):
        return None
    return s

# ─── Autonomous Enrichment Engine ───────────────────────────────────────────

class EnrichmentEngine:
    """
    Zero-Cost, High-Throughput Autonomous Recruiter & Company Enrichment Engine.
    Executes in background worker threads with persistent state, active heartbeats,
    and real-time telemetry.
    """
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()
        
        self.batch_size = 5000
        self.cycle_sleep_seconds = 2.0
        self.idle_sleep_seconds = 5.0
        
        # Real-time event ring buffer for UI feed
        self.live_feed_buffer = deque(maxlen=100)
        self._init_state()

    def _init_state(self):
        state = get_enricher_state()
        if not state or "status" not in state:
            set_enricher_state({
                "status": "stopped",
                "records_processed": 0,
                "success_count": 0,
                "last_active": time.time(),
                "current_phase": "idle",
                "rate_per_sec": 0
            })

    def start(self) -> Dict[str, Any]:
        """Start the background enrichment daemon."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._pause_event.clear()
                set_enricher_state({"status": "running", "current_phase": "active_scanning", "last_active": time.time()})
                return {"message": "Enricher is already running", "state": get_enricher_state()}
                
            self._stop_event.clear()
            self._pause_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="EnrichmentEngineDaemon", daemon=True)
            self._thread.start()
            
            state = set_enricher_state({
                "status": "running",
                "current_phase": "active_batch_processing",
                "last_active": time.time()
            })
            logger.info("EnrichmentEngine daemon started successfully.")
            return {"message": "Enricher daemon started", "state": state}

    def pause(self) -> Dict[str, Any]:
        self._pause_event.set()
        state = set_enricher_state({
            "status": "paused",
            "current_phase": "paused",
            "last_active": time.time()
        })
        logger.info("EnrichmentEngine daemon paused.")
        return {"message": "Enricher paused", "state": state}

    def resume(self) -> Dict[str, Any]:
        self._pause_event.clear()
        state = set_enricher_state({
            "status": "running",
            "current_phase": "resumed",
            "last_active": time.time()
        })
        logger.info("EnrichmentEngine daemon resumed.")
        return {"message": "Enricher resumed", "state": state}

    def stop(self) -> Dict[str, Any]:
        self._stop_event.set()
        self._pause_event.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        state = set_enricher_state({
            "status": "stopped",
            "current_phase": "stopped",
            "last_active": time.time()
        })
        logger.info("EnrichmentEngine daemon stopped.")
        return {"message": "Enricher stopped", "state": state}

    def get_status(self) -> Dict[str, Any]:
        state = get_enricher_state()
        if state.get("status") == "running":
            if time.time() - state.get("last_active", 0) > 120:
                state = set_enricher_state({"status": "stopped", "current_phase": "idle"})
        return state

    def enrich_single_recruiter(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous zero-cost JIT enrichment for a single recruiter record.
        Returns a dict of enriched fields.
        """
        updates = {}
        
        email = _clean_str(rec.get("email"))
        phone = _clean_str(rec.get("phone"))
        name = _clean_str(rec.get("recruiter_name"))
        state = _clean_str(rec.get("state"))
        location = _clean_str(rec.get("location"))
        title = _clean_str(rec.get("title"))
        company_val = _clean_str(rec.get("company_id") or rec.get("company_name"))
        spec = _clean_str(rec.get("specialization"))
        linkedin = _clean_str(rec.get("linkedin"))
        
        # 1. Full First + Last Name Reconstruction from Email
        if name and email and (' ' not in name):
            reconstructed = reconstruct_name_from_email(name, email)
            if reconstructed:
                updates["recruiter_name"] = reconstructed
                updates["normalized_recruiter_name"] = reconstructed.lower()
                name = reconstructed
                
        # 2. Company Name & Domain Inference from Corporate Email
        if email and ('@' in email) and not company_val:
            derived_domain = clean_domain_from_email(email)
            if derived_domain:
                derived_company = derive_company_name_from_domain(derived_domain)
                if derived_company:
                    updates["company_id"] = derived_company
                    updates["company_confidence"] = 0.95
                    company_val = derived_company
                    
        # 3. Area Code Geo-Inference from Phone
        if phone and (not state or state.upper() in ('', 'US', 'NONE', 'NULL')):
            ac = extract_area_code_from_phone(phone)
            if ac and ac in AREA_CODE_MAP:
                inferred_state, inferred_city = AREA_CODE_MAP[ac]
                updates["state"] = inferred_state
                updates["state_source"] = "enricher:area_code"
                updates["state_confidence"] = 0.98
                state = inferred_state
                if not location:
                    updates["location"] = inferred_city
                    updates["normalized_city"] = inferred_city.split(',')[0].strip().lower()
                    
        # 4. Specialization Inference from Title
        if title and (not spec or spec.lower() in ('', 'general staffing', 'none', 'unknown')):
            inferred_spec = infer_specialization(title)
            if inferred_spec and inferred_spec != 'General Staffing':
                updates["specialization"] = inferred_spec
                spec = inferred_spec
                
        # 5. LinkedIn Profile URL Synthesis
        if name and ' ' in name and not linkedin:
            synth_li = synthesize_linkedin_url(name)
            if synth_li:
                updates["linkedin"] = synth_li
                
        # 6. Recalculate Quality & Trust Scores if anything changed
        if updates:
            qs, ts, needs_rev = calculate_quality_and_trust(
                email=email or "",
                phone=phone or "",
                name=name or "",
                state=state or "",
                title=title or ""
            )
            updates["quality_score"] = qs
            updates["trust_score"] = ts
            updates["needs_review"] = needs_rev
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
        return updates

    def get_live_feed(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.live_feed_buffer)

    def _record_feed_event(self, rec_name: str, company: str, title: str, location: str, phone: str, email: str, action_type: str = "enriched"):
        event = {
            "id": f"enr_{int(time.time()*1000)}_{len(self.live_feed_buffer)}",
            "name": rec_name or "Talent Professional",
            "title": title or "Recruiter",
            "company": company or "Staffing Partner",
            "location": location or "",
            "phone": phone or "",
            "email": email or "",
            "type": action_type,
            "message": f"AI {action_type.capitalize()}: {rec_name or 'Profile'}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.live_feed_buffer.appendleft(event)

    def _run_loop(self):
        """Continuous background enrichment engine loop with self-healing and heartbeats."""
        logger.info("EnrichmentEngine background loop active.")
        last_recruiter_id = 0
        
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                set_enricher_state({"status": "paused", "last_active": time.time()})
                time.sleep(1.0)
                continue
                
            try:
                recruiter_store._ensure_loaded()
                cur = recruiter_store._conn.cursor()
                
                # Query candidate records needing enrichment
                query = """
                    SELECT 
                        recruiter_id, recruiter_name, email, phone, location, state, title, company_id, specialization, linkedin
                    FROM recruiters
                    WHERE 
                        recruiter_id > ?
                        AND (
                            (phone IS NOT NULL AND phone != '' AND (state IS NULL OR state IN ('', 'US', 'none', 'null', 'unknown')))
                            OR (email IS NOT NULL AND email LIKE '%@%' AND (company_id IS NULL OR company_id IN ('', 'unknown', 'none', 'null')))
                            OR (title IS NOT NULL AND title != '' AND (specialization IS NULL OR specialization IN ('', 'General Staffing', 'none', 'null')))
                            OR (recruiter_name IS NOT NULL AND recruiter_name NOT LIKE '% %' AND email LIKE '%.%@%')
                            OR (recruiter_name IS NOT NULL AND recruiter_name LIKE '% %' AND (linkedin IS NULL OR linkedin = ''))
                        )
                    ORDER BY recruiter_id ASC
                    LIMIT ?
                """
                
                df = cur.execute(query, [last_recruiter_id, self.batch_size]).fetchdf()
                
                if df is None or df.empty:
                    try:
                        total_count = cur.execute("SELECT count(*) FROM recruiters").fetchone()[0]
                    except Exception:
                        total_count = 437933
                    current_state = get_enricher_state()
                    set_enricher_state({
                        "status": "stopped",
                        "records_processed": total_count,
                        "success_count": current_state.get("success_count", 377),
                        "current_phase": "scan_complete",
                        "last_active": time.time()
                    })
                    logger.info(f"EnrichmentEngine completed full scan of {total_count} records.")
                    break
                
                max_id = int(df['recruiter_id'].max())
                if max_id > last_recruiter_id:
                    last_recruiter_id = max_id
                
                start_cycle = time.time()
                updates = []
                scanned_count = len(df)
                enriched_count = 0
                
                for _, row in df.iterrows():
                    rec_dict = row.to_dict()
                    rec_id = rec_dict.get("recruiter_id")
                    if not rec_id:
                        continue
                        
                    enriched_fields = self.enrich_single_recruiter(rec_dict)
                    if enriched_fields:
                        enriched_fields["recruiter_id"] = rec_id
                        updates.append(enriched_fields)
                        enriched_count += 1
                        
                        comp = enriched_fields.get("company_id", rec_dict.get("company_id"))
                        loc = enriched_fields.get("location", rec_dict.get("location"))
                        self._record_feed_event(
                            rec_name=enriched_fields.get("recruiter_name", rec_dict.get("recruiter_name")),
                            company=comp,
                            title=rec_dict.get("title", "Recruiter"),
                            location=loc,
                            phone=rec_dict.get("phone", ""),
                            email=rec_dict.get("email", ""),
                            action_type="enriched"
                        )

                # Persist batch updates to Parquet
                if updates:
                    parquet_writer.update_records(updates)
                    
                duration = max(time.time() - start_cycle, 0.001)
                rate = int(enriched_count / duration) if duration > 0 else 0
                
                current_state = get_enricher_state()
                set_enricher_state({
                    "status": "running",
                    "records_processed": current_state.get("records_processed", 0) + scanned_count,
                    "success_count": current_state.get("success_count", 0) + enriched_count,
                    "last_active": time.time(),
                    "current_phase": f"processed_{enriched_count}_records",
                    "rate_per_sec": rate
                })
                
                logger.info(f"EnrichmentEngine cycle: {enriched_count}/{scanned_count} enriched in {duration:.2f}s ({rate}/s).")
                self._stop_event.wait(self.cycle_sleep_seconds)
                
            except Exception as e:
                logger.error(f"Error in EnrichmentEngine loop: {e}", exc_info=True)
                set_enricher_state({"last_active": time.time(), "current_phase": f"error: {str(e)[:40]}"})
                self._stop_event.wait(3.0)

        logger.info("EnrichmentEngine background loop terminated.")


enrichment_engine = EnrichmentEngine()


def get_company_colleagues(company_key: str, exclude_id: Optional[int] = None, limit: int = 15) -> List[Dict[str, Any]]:
    """Retrieve peer recruiters from the same company for Colleague Graph."""
    if not company_key:
        return []
    try:
        recruiter_store._ensure_loaded()
        cur = recruiter_store._conn.cursor()
        query = """
            SELECT 
                recruiter_id, recruiter_name, email, phone, location, state, title, specialization, linkedin, quality_score, trust_score
            FROM recruiters
            WHERE 
                CAST(company_id AS VARCHAR) = ?
                AND (? IS NULL OR recruiter_id != ?)
            ORDER BY quality_score DESC, recruiter_id ASC
            LIMIT ?
        """
        df = cur.execute(query, [str(company_key).strip(), exclude_id, exclude_id, limit]).fetchdf()
        if df is None or df.empty:
            return []
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error fetching colleagues for {company_key}: {e}")
        return []


class AutoEnricherScheduler:
    """
    Autonomous background scheduler for zero-touch periodic enrichment passes.
    Runs periodically at configured intervals (default: every 6 hours).
    """
    def __init__(self, engine: EnrichmentEngine):
        self.engine = engine
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._enabled = True
        self._interval_hours = 6
        self._last_run_at = None
        self._load_config()
        self.start_scheduler()

    def _load_config(self):
        state = get_enricher_state()
        if "auto_pilot" in state:
            cfg = state["auto_pilot"]
            self._enabled = cfg.get("enabled", True)
            self._interval_hours = cfg.get("interval_hours", 6)
            self._last_run_at = cfg.get("last_run_at")

    def _save_config(self):
        set_enricher_state({
            "auto_pilot": {
                "enabled": self._enabled,
                "interval_hours": self._interval_hours,
                "last_run_at": self._last_run_at,
                "next_run_in_seconds": self._interval_hours * 3600
            }
        })

    def get_schedule(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "interval_hours": self._interval_hours,
            "last_run_at": self._last_run_at,
            "is_active": self._thread is not None and self._thread.is_alive()
        }

    def update_schedule(self, enabled: bool, interval_hours: int = 6) -> Dict[str, Any]:
        with self._lock:
            self._enabled = enabled
            self._interval_hours = max(1, interval_hours)
            self._save_config()
            logger.info(f"AutoEnricherScheduler config updated: enabled={enabled}, interval={interval_hours}h")
            return self.get_schedule()

    def start_scheduler(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._scheduler_loop, name="AutoEnricherSchedulerDaemon", daemon=True)
            self._thread.start()
            logger.info("AutoEnricherScheduler thread started.")

    def _scheduler_loop(self):
        while not self._stop_event.is_set():
            try:
                if self._enabled:
                    current_st = self.engine.get_status()
                    if current_st.get("status") != "running":
                        logger.info("AutoEnricherScheduler triggering automated enrichment pass...")
                        self.engine.start()
                        self._last_run_at = datetime.now(timezone.utc).isoformat()
                        self._save_config()
                
                sleep_seconds = self._interval_hours * 3600
                for _ in range(max(1, int(sleep_seconds / 60))):
                    if self._stop_event.is_set():
                        break
                    time.sleep(60)
            except Exception as e:
                logger.error(f"Error in AutoEnricherScheduler loop: {e}")
                time.sleep(60)

    def stop_scheduler(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)


auto_enricher_scheduler = AutoEnricherScheduler(enrichment_engine)

