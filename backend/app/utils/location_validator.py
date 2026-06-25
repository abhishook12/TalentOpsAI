import re

US_STATES = {
    'ALABAMA', 'ALASKA', 'ARIZONA', 'ARKANSAS', 'CALIFORNIA', 'COLORADO', 'CONNECTICUT', 'DELAWARE', 'FLORIDA',
    'GEORGIA', 'HAWAII', 'IDAHO', 'ILLINOIS', 'INDIANA', 'IOWA', 'KANSAS', 'KENTUCKY', 'LOUISIANA', 'MAINE',
    'MARYLAND', 'MASSACHUSETTS', 'MICHIGAN', 'MINNESOTA', 'MISSISSIPPI', 'MISSOURI', 'MONTANA', 'NEBRASKA',
    'NEVADA', 'NEW HAMPSHIRE', 'NEW JERSEY', 'NEW MEXICO', 'NEW YORK', 'NORTH CAROLINA', 'NORTH DAKOTA', 'OHIO',
    'OKLAHOMA', 'OREGON', 'PENNSYLVANIA', 'RHODE ISLAND', 'SOUTH CAROLINA', 'SOUTH DAKOTA', 'TENNESSEE', 'TEXAS',
    'UTAH', 'VERMONT', 'VIRGINIA', 'WASHINGTON', 'WEST VIRGINIA', 'WISCONSIN', 'WYOMING',
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA',
    'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC', 'D.C.'
}

CANADIAN_PROVINCES = {
    'ONTARIO', 'QUEBEC', 'NOVA SCOTIA', 'NEW BRUNSWICK', 'MANITOBA', 'BRITISH COLUMBIA', 'PRINCE EDWARD ISLAND',
    'SASKATCHEWAN', 'ALBERTA', 'NEWFOUNDLAND AND LABRADOR', 'NEWFOUNDLAND', 'LABRADOR', 'NORTHWEST TERRITORIES',
    'YUKON', 'NUNAVUT',
    'ON', 'QC', 'NS', 'NB', 'MB', 'BC', 'PE', 'SK', 'AB', 'NL', 'NT', 'YT', 'NU'
}

NON_NA_COUNTRIES = {
    'INDIA', 'UNITED KINGDOM', 'U.K.', 'GREAT BRITAIN', 'GERMANY', 'FRANCE', 'AUSTRALIA', 'BRAZIL', 'PHILIPPINES',
    'POLAND', 'ROMANIA', 'UKRAINE', 'NETHERLANDS', 'SPAIN', 'ITALY', 'SINGAPORE', 'JAPAN', 'CHINA', 'VIETNAM',
    'MALAYSIA', 'INDONESIA', 'PAKISTAN', 'BANGLADESH', 'RUSSIA', 'EUROPE', 'APAC', 'EMEA', 'LATAM', 'AFRICA', 'ASIA',
    'LONDON', 'ENGLAND', 'SCOTLAND', 'WALES', 'IRELAND', 'ARGENTINA', 'UKRAINE'
}

def extract_clean_location_line(snippet: str) -> str:
    if not snippet:
        return ""
    if '\n' not in snippet:
        return snippet
        
    lines = [line.strip() for line in snippet.split('\n') if line.strip()]
    
    countries = {
        "UNITED STATES", "USA", "CANADA", "INDIA", "UNITED KINGDOM", "UK", "GERMANY", "FRANCE",
        "AUSTRALIA", "BRAZIL", "PHILIPPINES", "POLAND", "ROMANIA", "UKRAINE", "NETHERLANDS",
        "SPAIN", "ITALY", "SINGAPORE", "MEXICO", "PUERTO RICO", "ARGENTINA"
    }
    
    # 1. Look for a line containing a known country
    for line in lines:
        line_upper = line.upper()
        if any(x in line_upper for x in ["CONNECTIONS", "FOLLOWERS", "ABOUT", "EXPERIENCE", "EDUCATION", "PRESENTS"]):
            continue
        for country in countries:
            if re.search(r'\b' + re.escape(country) + r'\b', line_upper):
                return line
                
    # 2. Look for a line with "Area" or "Metro"
    for line in lines:
        line_upper = line.upper()
        if any(x in line_upper for x in ["CONNECTIONS", "FOLLOWERS", "ABOUT", "EXPERIENCE", "EDUCATION"]):
            continue
        if "AREA" in line_upper or "METRO" in line_upper:
            return line
            
    # 3. Fallback to non-meta lines
    non_meta_lines = []
    for line in lines:
        line_upper = line.upper()
        if any(x in line_upper for x in ["CONNECTIONS", "FOLLOWERS", "ABOUT", "EXPERIENCE", "EDUCATION", "N/A"]):
            continue
        non_meta_lines.append(line)
        
    if len(non_meta_lines) > 2:
        return non_meta_lines[2]
    elif len(non_meta_lines) > 1:
        return non_meta_lines[1]
        
    return lines[0] if lines else ""

def is_location_north_america(location: str) -> bool:
    if not location:
        return False
        
    clean_loc = extract_clean_location_line(location)
    loc_upper = clean_loc.upper().strip()
    
    if not loc_upper:
        return False
        
    # 1. Check explicit non-NA country/region indicators
    for country in NON_NA_COUNTRIES:
        if re.search(r'\b' + re.escape(country) + r'\b', loc_upper):
            return False
            
    # 2. Check explicit NA country indicators
    na_countries = {'UNITED STATES', 'USA', 'U.S.A.', 'U.S.', 'CANADA', 'MEXICO', 'PUERTO RICO'}
    for country in na_countries:
        if re.search(r'\b' + re.escape(country) + r'\b', loc_upper):
            return True
            
    # 3. Check tokens (words) against US state abbreviations and Canadian province abbreviations
    tokens = set(re.split(r'[^A-Z]+', loc_upper))
    
    for token in tokens:
        if token in US_STATES or token in CANADIAN_PROVINCES:
            # Special check to exclude Indian state abbreviation/city collision
            if token in {'UP', 'KA', 'TG', 'MH'}:
                if any(x in loc_upper for x in ['INDIA', 'NOIDA', 'BANGALORE', 'HYDERABAD', 'PUNE']):
                    return False
            return True
            
    # 4. Check multi-word state/province names
    for name in US_STATES.union(CANADIAN_PROVINCES):
        if len(name) > 2 and re.search(r'\b' + re.escape(name) + r'\b', loc_upper):
            return True
            
    # 5. Check well-known US/Canada cities/metro terms
    us_cities = {
        'ATLANTA', 'AUSTIN', 'BALTIMORE', 'BOSTON', 'CHARLOTTE', 'CHICAGO', 'CLEVELAND', 'COLUMBUS', 'DALLAS',
        'DENVER', 'DETROIT', 'HOUSTON', 'INDIANAPOLIS', 'JACKSONVILLE', 'LOS ANGELES', 'MIAMI', 'MINNEAPOLIS',
        'NASHVILLE', 'NEW YORK', 'NYC', 'ORLANDO', 'PHILADELPHIA', 'PHOENIX', 'PITTSBURGH', 'PORTLAND',
        'RALEIGH', 'RICHMOND', 'SACRAMENTO', 'SAN ANTONIO', 'SAN DIEGO', 'SAN FRANCISCO', 'SAN JOSE',
        'SEATTLE', 'ST. LOUIS', 'TAMPA', 'LAS VEGAS', 'SALT LAKE CITY', 'MILWAUKEE', 'CINCINNATI', 'KANSAS CITY',
        'OMAHA', 'TORONTO', 'VANCOUVER', 'MONTREAL', 'CALGARY', 'OTTAWA', 'EDMONTON', 'HALIFAX', 'QUEBEC CITY'
    }
    for city in us_cities:
        if re.search(r'\b' + re.escape(city) + r'\b', loc_upper):
            return True
            
    return False
