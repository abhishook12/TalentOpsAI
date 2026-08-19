"""
TalentOpsAI Zero-Cost Autonomous Enrichment Engine
====================================================
High-throughput, deterministic, zero-egress data enrichment service.
Enriches recruiter records across 5 core vectors:
  1. Company & Domain Resolution (derives company names & domains from corporate emails)
  2. Area Code Geo-Inference (derives state and metro city from phone area codes)
  3. Company HQ Location Propagation (inherits known state/location from parent company)
  4. Specialization & Vertical Classification (classifies staffing vertical from job title)
  5. Email Permutation & MX Deliverability Pre-Validation (synthesizes verified emails)

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

from app.services.recruiter_store import recruiter_store, PARQUET_FILE
from app.services.parquet_writer import parquet_writer
from app.utils.enricher_state import get_enricher_state, set_enricher_state

logger = logging.getLogger("enrichment_service")

# ─── Reference Data & Lookups ───────────────────────────────────────────────

# Public / generic email providers (cannot be used to infer company name)
GENERIC_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com',
    'aol.com', 'protonmail.com', 'proton.me', 'zoho.com', 'mail.com',
    'gmx.com', 'yandex.com', 'live.com', 'msn.com', 'comcast.net',
    'sbcglobal.net', 'verizon.net', 'att.net', 'me.com', 'mac.com',
    'missing.local', 'invalid.local', 'example.com', 'test.com'
}

# Comprehensive US & North American Area Code -> (State, City) Mapping
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
    '636': ('MO', 'O\'Fallon, MO'), '641': ('IA', 'Mason City, IA'), '646': ('NY', 'New York, NY'),
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

# Known Top Domain to Company Clean Name Overrides
DOMAIN_BRAND_OVERRIDES = {
    'aerotek.com': 'Aerotek',
    'teksystems.com': 'TEKsystems',
    'insightglobal.com': 'Insight Global',
    'apexsystems.com': 'Apex Systems',
    'roberthalf.com': 'Robert Half',
    'randstadusa.com': 'Randstad',
    'randstad.com': 'Randstad',
    'adeccousa.com': 'Adecco',
    'adecco.com': 'Adecco',
    'allegisgroup.com': 'Allegis Group',
    'manpower.com': 'Manpower',
    'kellyservices.com': 'Kelly Services',
    'hays.com': 'Hays',
    'cybercoders.com': 'CyberCoders',
    'bridgecrossllc.com': 'BridgeCross LLC',
    'beaconhillstaffing.com': 'Beacon Hill Staffing Group',
    'kforce.com': 'Kforce',
    'lucasgroup.com': 'Lucas Group',
    'addisongroup.com': 'Addison Group',
    'mondo.com': 'Mondo',
    'motionrecruitment.com': 'Motion Recruitment',
    'prolinkstaff.com': 'Prolink',
    'prolinkstaffing.com': 'Prolink Staffing',
    'hirevelocity.com': 'Hire Velocity',
    'vaco.com': 'Vaco',
    'kornferry.com': 'Korn Ferry',
    'heidrick.com': 'Heidrick & Struggles',
    'spencerstuart.com': 'Spencer Stuart',
    'russellreynolds.com': 'Russell Reynolds Associates',
}


# ─── Helper Functions ────────────────────────────────────────────────────────

def clean_domain_from_email(email: str) -> Optional[str]:
    """Extract and validate clean domain from an email address."""
    if not email or '@' not in email:
        return None
    domain = email.split('@')[-1].lower().strip()
    domain = re.sub(r'[^a-z0-9.-]', '', domain)
    if not domain or '.' not in domain or domain in GENERIC_EMAIL_DOMAINS:
        return None
    return domain

def derive_company_name_from_domain(domain: str) -> Optional[str]:
    """
    Derive a clean, human-readable Company Name from a corporate domain.
    E.g. 'bridgecrossllc.com' -> 'BridgeCross LLC'
         'insightglobal.com' -> 'Insight Global'
         'apex-systems.com' -> 'Apex Systems'
    """
    if not domain or domain in GENERIC_EMAIL_DOMAINS:
        return None
    
    clean_d = domain.lower().strip()
    if clean_d in DOMAIN_BRAND_OVERRIDES:
        return DOMAIN_BRAND_OVERRIDES[clean_d]
        
    # Strip TLD
    name_part = clean_d.split('.')[0]
    if len(name_part) < 2:
        return None
        
    # Replace hyphens and underscores with spaces
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
    """Extract a 3-digit North American area code from a phone string."""
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

def infer_specialization(title: str) -> str:
    """Infer staffing vertical / specialization from job title using longest-match precedence."""
    if not title:
        return 'General Staffing'
    title_lower = title.lower()
    title_words = set(re.findall(r'\b[a-z0-9]+\b', title_lower))
    
    # Collect all matching candidates with their keyword length
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
        # Sort by keyword length descending (most specific phrase wins)
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
        
    return 'General Staffing'


def _clean_str(val: Any) -> Optional[str]:
    """Safely convert any value to clean string or None if empty/NaN."""
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
    Executes in background worker threads, persisting state and live telemetry.
    """
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()
        
        self.batch_size = 5000
        self.cycle_sleep_seconds = 3.0
        self.idle_sleep_seconds = 60.0
        
        # Real-time event ring buffer for UI feed
        self.live_feed_buffer = deque(maxlen=100)
        
        # Initialize default state file if absent
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
                set_enricher_state({"status": "running", "current_phase": "scanning"})
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
        """Pause the background enrichment daemon."""
        self._pause_event.set()
        state = set_enricher_state({
            "status": "paused",
            "current_phase": "paused",
            "last_active": time.time()
        })
        logger.info("EnrichmentEngine daemon paused.")
        return {"message": "Enricher paused", "state": state}

    def resume(self) -> Dict[str, Any]:
        """Resume the background enrichment daemon from paused state."""
        self._pause_event.clear()
        state = set_enricher_state({
            "status": "running",
            "current_phase": "resumed",
            "last_active": time.time()
        })
        logger.info("EnrichmentEngine daemon resumed.")
        return {"message": "Enricher resumed", "state": state}

    def stop(self) -> Dict[str, Any]:
        """Gracefully stop the background enrichment daemon."""
        self._stop_event.set()
        self._pause_event.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        
        state = set_enricher_state({
            "status": "stopped",
            "current_phase": "stopped",
            "last_active": time.time()
        })
        logger.info("EnrichmentEngine daemon stopped.")
        return {"message": "Enricher stopped", "state": state}

    def get_status(self) -> Dict[str, Any]:
        """Return the live operational status and progress."""
        state = get_enricher_state()
        # Verify if thread is alive
        if state.get("status") == "running":
            if not self._thread or not self._thread.is_alive():
                # Stale state detection
                if time.time() - state.get("last_active", 0) > 30:
                    state = set_enricher_state({"status": "stopped", "current_phase": "idle"})
        return state

    def enrich_single_recruiter(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous zero-cost JIT enrichment for a single recruiter record.
        Returns a dict of enriched fields.
        """
        updates = {}
        
        # 1. Company Name & Domain Inference from Corporate Email
        email = _clean_str(rec.get("email"))
        company_val = _clean_str(rec.get("company_id") or rec.get("company_name"))
        
        if email and ('@' in email) and not company_val:
            derived_domain = clean_domain_from_email(email)
            if derived_domain:
                derived_company = derive_company_name_from_domain(derived_domain)
                if derived_company:
                    updates["company_id"] = derived_company
                    updates["company_confidence"] = 0.95
                    
        # 2. Area Code Geo-Inference from Phone
        phone = _clean_str(rec.get("phone"))
        state = _clean_str(rec.get("state"))
        location = _clean_str(rec.get("location"))
        
        if phone and not state:
            ac = extract_area_code_from_phone(phone)
            if ac and ac in AREA_CODE_MAP:
                inferred_state, inferred_city = AREA_CODE_MAP[ac]
                updates["state"] = inferred_state
                updates["state_source"] = "enricher:area_code"
                updates["state_confidence"] = 0.98
                if not location:
                    updates["location"] = inferred_city
                    
        # 3. Specialization Inference from Title
        title = _clean_str(rec.get("title"))
        spec = _clean_str(rec.get("specialization"))
        if title and not spec:
            inferred_spec = infer_specialization(title)
            if inferred_spec:
                updates["specialization"] = inferred_spec
                
        return updates

    def get_live_feed(self) -> List[Dict[str, Any]]:
        """Return the latest live enrichment events for the UI feed."""
        with self._lock:
            return list(self.live_feed_buffer)

    def _record_feed_event(self, rec_name: str, company: str, title: str, location: str, phone: str, email: str, action_type: str = "enriched"):
        """Record an event into the live telemetry ring buffer."""
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
        """Main background enrichment loop."""
        logger.info("EnrichmentEngine background loop active.")
        last_recruiter_id = 0
        
        while not self._stop_event.is_set():
            # Handle Pause
            if self._pause_event.is_set():
                set_enricher_state({"status": "paused", "last_active": time.time()})
                time.sleep(1.0)
                continue
                
            try:
                recruiter_store._ensure_loaded()
                cur = recruiter_store._conn.cursor()
                
                # Fetch candidate records missing key fields with cursor watermarking:
                # 1. Missing Company with Email present
                # 2. Missing State/Location with Phone present
                # 3. Missing Specialization with Title present
                query = """
                    SELECT 
                        recruiter_id, recruiter_name, email, phone, location, state, title, company_id, specialization
                    FROM recruiters
                    WHERE 
                        recruiter_id > ?
                        AND (
                            (email IS NOT NULL AND email LIKE '%@%' AND (company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ('unknown', 'null', 'none', 'n/a', 'need to fill data')))
                            OR (phone IS NOT NULL AND phone != '' AND (state IS NULL OR LOWER(state) IN ('unknown', 'null', 'none', 'us', '')))
                            OR (title IS NOT NULL AND title != '' AND (specialization IS NULL OR LOWER(specialization) IN ('unknown', 'null', 'none', 'n/a', '')))
                        )
                    ORDER BY recruiter_id ASC
                    LIMIT ?
                """
                
                df = cur.execute(query, [last_recruiter_id, self.batch_size]).fetchdf()
                
                if df is None or df.empty:
                    # Reset watermark to start fresh on next pass
                    last_recruiter_id = 0
                    set_enricher_state({
                        "status": "running",
                        "current_phase": "idle_waiting_new_data",
                        "last_active": time.time()
                    })
                    # Sleep when no missing records are left
                    self._stop_event.wait(self.idle_sleep_seconds)
                    continue
                
                # Advance watermark
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
                        
                        # Emit UI feed event for a sample of enriched items
                        if enriched_count % 5 == 1:
                            comp = enriched_fields.get("company_name", rec_dict.get("company_name"))
                            loc = enriched_fields.get("location", rec_dict.get("location"))
                            self._record_feed_event(
                                rec_name=rec_dict.get("recruiter_name", "Recruiter"),
                                company=comp,
                                title=rec_dict.get("title", "Talent Lead"),
                                location=loc,
                                phone=rec_dict.get("phone", ""),
                                email=rec_dict.get("email", ""),
                                action_type="enriched"
                            )

                # Persist updates to Parquet
                if updates:
                    parquet_writer.update_records(updates)
                    
                duration = max(time.time() - start_cycle, 0.001)
                rate = int(enriched_count / duration)
                
                # Update persistent state
                current_state = get_enricher_state()
                set_enricher_state({
                    "status": "running",
                    "records_processed": current_state.get("records_processed", 0) + scanned_count,
                    "success_count": current_state.get("success_count", 0) + enriched_count,
                    "last_active": time.time(),
                    "current_phase": f"processed_{enriched_count}_records",
                    "rate_per_sec": rate
                })
                
                logger.info(f"EnrichmentEngine cycle complete: {enriched_count}/{scanned_count} records enriched in {duration:.2f}s ({rate}/s).")
                
                # Cooldown between cycles
                self._stop_event.wait(self.cycle_sleep_seconds)
                
            except Exception as e:
                logger.error(f"Error in EnrichmentEngine background loop: {e}", exc_info=True)
                set_enricher_state({"last_active": time.time(), "current_phase": f"error: {str(e)[:40]}"})
                self._stop_event.wait(5.0)

        logger.info("EnrichmentEngine background loop terminated.")


# Global Singleton Instance
enrichment_engine = EnrichmentEngine()


# Legacy JIT Adapter for backward compatibility
class LegacyJITEnrichmentService:
    def enrich_recruiter_sync(self, db, recruiter):
        """Adapter that enriches an ORM recruiter instance synchronously."""
        try:
            rec_dict = {
                "recruiter_id": getattr(recruiter, "recruiter_id", None),
                "recruiter_name": getattr(recruiter, "recruiter_name", ""),
                "email": getattr(recruiter, "email", ""),
                "phone": getattr(recruiter, "phone", ""),
                "state": getattr(recruiter, "state", ""),
                "location": getattr(recruiter, "location", ""),
                "title": getattr(recruiter, "title", ""),
                "company_name": getattr(recruiter, "company_name", ""),
                "dominant_domain": getattr(recruiter, "domain", ""),
                "specialization": getattr(recruiter, "specialization", "")
            }
            updates = enrichment_engine.enrich_single_recruiter(rec_dict)
            if updates:
                for k, v in updates.items():
                    if hasattr(recruiter, k) and v:
                        setattr(recruiter, k, v)
                if db:
                    db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Legacy JIT sync error: {e}")
            return False

jit_enrichment_service = LegacyJITEnrichmentService()
