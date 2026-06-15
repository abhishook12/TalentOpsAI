import re

STATE_MAP = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
    'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
    'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
    'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS', 'MISSOURI': 'MO',
    'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ',
    'NEW MEXICO': 'NM', 'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH',
    'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
    'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT',
    'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY'
}

ABBR_TO_NAME = {v: k for k, v in STATE_MAP.items()}

# Mapping well-known cities to their state abbreviations
CITY_TO_STATE = {
    'ATLANTA': 'GA', 'AUSTIN': 'TX', 'BALTIMORE': 'MD', 'BOSTON': 'MA', 'CHARLOTTE': 'NC',
    'CHICAGO': 'IL', 'CLEVELAND': 'OH', 'COLUMBUS': 'OH', 'DALLAS': 'TX', 'DENVER': 'CO',
    'DETROIT': 'MI', 'TROY': 'MI', 'LIVONIA': 'MI', 'HOUSTON': 'TX', 'INDIANAPOLIS': 'IN', 'JACKSONVILLE': 'FL',
    'LOS ANGELES': 'CA', 'MIAMI': 'FL', 'MINNEAPOLIS': 'MN', 'NASHVILLE': 'TN',
    'NEW YORK': 'NY', 'NYC': 'NY', 'ORLANDO': 'FL', 'PHILADELPHIA': 'PA', 'PHOENIX': 'AZ',
    'PITTSBURGH': 'PA', 'PORTLAND': 'OR', 'RALEIGH': 'NC', 'RICHMOND': 'VA',
    'SACRAMENTO': 'CA', 'SAN ANTONIO': 'TX', 'SAN DIEGO': 'CA', 'SAN FRANCISCO': 'CA',
    'SAN JOSE': 'CA', 'SEATTLE': 'WA', 'ST. LOUIS': 'MO', 'TAMPA': 'FL',
    'WASHINGTON D.C.': 'DC', 'WASHINGTON DC': 'DC', 'LAS VEGAS': 'NV',
    'SALT LAKE CITY': 'UT', 'MILWAUKEE': 'WI', 'CINCINNATI': 'OH', 'KANSAS CITY': 'MO',
    'OMAHA': 'NE', 'NOIDA': 'UP', 'BANGALORE': 'KA', 'HYDERABAD': 'TG', 'PUNE': 'MH', 'CHENNAI': 'TN',
    'IRVING': 'TX', 'PLANO': 'TX', 'FRISCO': 'TX', 'FORT WORTH': 'TX', 'THE WOODLANDS': 'TX',
    'ALEXANDRIA': 'VA', 'ARLINGTON': 'VA', 'MCLEAN': 'VA', 'RESTON': 'VA', 'TYSONS': 'VA',
    'RALEIGH': 'NC', 'CARY': 'NC', 'DURHAM': 'NC', 'CHARLOTTE': 'NC', 'WILMINGTON': 'NC',
    'TAMPA BAY': 'FL', 'SOUTH FLORIDA': 'FL', 'CENTRAL FLORIDA': 'FL', 'ORLANDO AREA': 'FL',
    'BAY AREA': 'CA', 'SILICON VALLEY': 'CA', 'LOS ANGELES COUNTY': 'CA', 'ORANGE COUNTY': 'CA',
    'TWIN CITIES': 'MN', 'MINNEAPOLIS ST. PAUL': 'MN', 'GREATER DETROIT': 'MI', 'SOUTH JERSEY': 'NJ',
    'NORTH JERSEY': 'NJ', 'NORTH TEXAS': 'TX', 'CENTRAL TEXAS': 'TX', 'WEST TEXAS': 'TX',
    'PHOENIX METRO': 'AZ', 'SEATTLE METRO': 'WA', 'HOUSTON METRO': 'TX', 'DALLAS METRO': 'TX',
    'ATLANTA METRO': 'GA', 'CHARLOTTE METRO': 'NC', 'NYC METRO': 'NY', 'NEW YORK CITY': 'NY',
    'GREATER PHILADELPHIA': 'PA', 'PHILADELPHIA METRO': 'PA', 'RESEARCH TRIANGLE': 'NC', 'RTP': 'NC',
    'GREATER DALLAS': 'TX', 'DALLAS-FORT WORTH': 'TX', 'DFW': 'TX', 'TRI-STATE AREA': 'NY',
    'GREATER NEW YORK': 'NY', 'NEW YORK METRO': 'NY', 'WASHINGTON METRO': 'DC', 'DMV': 'DC',
}

LOCATION_PHRASE_TO_STATE = {
    'GREATER DALLAS': 'TX',
    'DALLAS-FORT WORTH': 'TX',
    'DFW': 'TX',
    'AUSTIN METRO': 'TX',
    'ATLANTA METRO': 'GA',
    'BAY AREA': 'CA',
    'GREATER CHICAGO': 'IL',
    'NYC METRO': 'NY',
    'GREATER NEW YORK': 'NY',
    'GREATER PHILADELPHIA': 'PA',
    'CHARLOTTE METRO': 'NC',
    'RESEARCH TRIANGLE': 'NC',
    'RTP': 'NC',
    'DETROIT METRO': 'MI',
    'BAY AREA': 'CA',
    'SILICON VALLEY': 'CA',
    'NORTH TEXAS': 'TX',
    'SOUTH FLORIDA': 'FL',
    'CENTRAL FLORIDA': 'FL',
    'TAMPA BAY': 'FL',
    'TRI-STATE AREA': 'NY',
    'NEW YORK METRO': 'NY',
    'WASHINGTON METRO': 'DC',
}

def extract_state_detailed(location: str, strict: bool = False):
    """
    Returns (state_abbreviation, source_reason)
    """
    if not location:
        return None, None
    
    loc_upper = str(location).upper()
    
    # 1. Exact match for state abbreviation
    clean_abbr = re.sub(r'[^A-Z]', '', loc_upper)
    if len(clean_abbr) == 2 and clean_abbr in ABBR_TO_NAME:
        return clean_abbr, 'abbreviation_exact_match'

    # 2. Match location phrases
    for phrase, abbr in LOCATION_PHRASE_TO_STATE.items():
        if phrase in loc_upper:
            return abbr, 'location_phrase_match'
            
    # 3. Look for 2-letter word boundaries that match state abbreviations
    if not strict:
        tokens = re.findall(r'\b[A-Z]{2}\b', loc_upper)
        for token in tokens:
            if token in ABBR_TO_NAME:
                return token, 'abbreviation_word_boundary'
            
    # 4. Fallback: Split by commas or spaces, check reversed
    if not strict:
        parts = [p.strip() for p in re.split(r'[,\s]+', loc_upper) if p.strip()]
        for p in reversed(parts):
            clean_p = p.replace('.', '')
            if clean_p in ABBR_TO_NAME:
                return clean_p, 'abbreviation_comma_split'

    # 5. City match
    for city, abbr in CITY_TO_STATE.items():
        if re.search(r'\b' + re.escape(city) + r'\b', loc_upper):
            if abbr in ABBR_TO_NAME:
                return abbr, 'city_match'

    # 6. Match full state names
    for state_name, abbr in STATE_MAP.items():
        if re.search(r'\b' + re.escape(state_name) + r'\b', loc_upper):
            return abbr, 'full_state_name_match'

    return None, None

def normalize_state(location: str) -> str:
    """
    Returns the 2-letter state abbreviation if a valid US state is found in the location string.
    Returns None otherwise.
    """
    state, _ = extract_state_detailed(location)
    return state
