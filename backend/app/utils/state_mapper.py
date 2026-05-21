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
    'DETROIT': 'MI', 'HOUSTON': 'TX', 'INDIANAPOLIS': 'IN', 'JACKSONVILLE': 'FL',
    'LOS ANGELES': 'CA', 'MIAMI': 'FL', 'MINNEAPOLIS': 'MN', 'NASHVILLE': 'TN',
    'NEW YORK': 'NY', 'ORLANDO': 'FL', 'PHILADELPHIA': 'PA', 'PHOENIX': 'AZ',
    'PITTSBURGH': 'PA', 'PORTLAND': 'OR', 'RALEIGH': 'NC', 'RICHMOND': 'VA',
    'SACRAMENTO': 'CA', 'SAN ANTONIO': 'TX', 'SAN DIEGO': 'CA', 'SAN FRANCISCO': 'CA',
    'SAN JOSE': 'CA', 'SEATTLE': 'WA', 'ST. LOUIS': 'MO', 'TAMPA': 'FL',
    'WASHINGTON D.C.': 'DC', 'WASHINGTON DC': 'DC', 'LAS VEGAS': 'NV',
    'SALT LAKE CITY': 'UT', 'MILWAUKEE': 'WI', 'CINCINNATI': 'OH', 'KANSAS CITY': 'MO',
    'OMAHA': 'NE', 'NOIDA': 'UP', 'BANGALORE': 'KA', 'HYDERABAD': 'TG', 'PUNE': 'MH', 'CHENNAI': 'TN'
}

def normalize_state(location: str) -> str:
    """
    Returns the 2-letter state abbreviation if a valid US state is found in the location string.
    Returns None otherwise.
    """
    if not location:
        return None
    
    loc_upper = str(location).upper()
    
    # 1. Exact match for state abbreviation, handling punctuation like "N.C." -> "NC"
    clean_abbr = re.sub(r'[^A-Z]', '', loc_upper)
    if len(clean_abbr) == 2 and clean_abbr in ABBR_TO_NAME:
        return clean_abbr
        
    # 2. Match full state names
    for state_name, abbr in STATE_MAP.items():
        if re.search(r'\b' + re.escape(state_name) + r'\b', loc_upper):
            return abbr
            
    # 3. Look for 2-letter word boundaries that match state abbreviations
    tokens = re.findall(r'\b[A-Z]{2}\b', loc_upper)
    for token in tokens:
        if token in ABBR_TO_NAME:
            return token
            
    # 4. Fallback: Split by commas or spaces, check reversed (typically City, ST format)
    parts = [p.strip() for p in re.split(r'[,\s]+', loc_upper) if p.strip()]
    for p in reversed(parts):
        # Also clean periods from parts like "N.C." -> "NC"
        clean_p = p.replace('.', '')
        if clean_p in ABBR_TO_NAME:
            return clean_p
            
    # 5. Last resort: check if any known major city is in the location
    for city, abbr in CITY_TO_STATE.items():
        if re.search(r'\b' + re.escape(city) + r'\b', loc_upper):
            if abbr in ABBR_TO_NAME: # Only return valid US states
                return abbr

    return None
