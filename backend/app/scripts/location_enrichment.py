"""
Location Enrichment v2 — ACCURACY-FIRST approach.

Rules:
  1. NEVER guess. Only write data we are confident about.
  2. Detect and skip garbage (phone numbers, company names, person names).
  3. Fix wrong state assignments where the location string clearly contradicts them.
  4. Handle international locations properly (skip US-state assignment).
  5. Properly normalize city names (title case, no state/zip appended).
  6. Only fill missing locations from company peers when there's strong consensus (>= 60% of peers share the same location).
"""

import os, sys, re, unicodedata
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import engine
from sqlalchemy import text


# ─── REFERENCE DATA ─────────────────────────────────────────────────────

US_STATES = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
}

# Misspellings map
STATE_MISSPELLINGS = {
    'massachuttes': 'MA', 'massachusets': 'MA', 'massachuesetts': 'MA',
    'massachussetts': 'MA', 'pensylvania': 'PA', 'pennsylania': 'PA',
    'pensilvania': 'PA', 'conneticut': 'CT', 'connecticutt': 'CT',
    'tenessee': 'TN', 'tennesse': 'TN', 'tennessie': 'TN',
    'mississipi': 'MS', 'mississippi': 'MS', 'californa': 'CA',
    'californai': 'CA', 'colordao': 'CO', 'colorodo': 'CO',
    'virgina': 'VA', 'viginia': 'VA', 'minesota': 'MN',
    'winsconsin': 'WI', 'wisconson': 'WI', 'louisianna': 'LA',
    'illiniois': 'IL', 'ilinois': 'IL', 'illinios': 'IL',
}

ABBREV_SET = set(US_STATES.values())

# Two-letter abbreviations that are also common non-state words (skip these in ambiguous contexts)
AMBIGUOUS_ABBREVS = {'IN', 'OR', 'ME', 'OK', 'HI'}

COUNTRIES = {
    'united kingdom', 'uk', 'england', 'scotland', 'wales', 'ireland',
    'canada', 'australia', 'germany', 'france', 'india', 'china', 'japan',
    'brazil', 'mexico', 'spain', 'italy', 'netherlands', 'sweden', 'norway',
    'denmark', 'finland', 'switzerland', 'austria', 'belgium', 'portugal',
    'singapore', 'hong kong', 'south korea', 'israel', 'uae',
    'united arab emirates', 'new zealand', 'philippines', 'poland',
    'czech republic', 'romania', 'hungary', 'south africa', 'nigeria',
    'colombia', 'argentina', 'chile', 'peru', 'egypt', 'turkey', 'greece',
    'thailand', 'vietnam', 'indonesia', 'malaysia', 'pakistan', 'bangladesh',
    'sri lanka', 'kenya', 'ghana', 'taiwan', 'costa rica',
}

# Common abbreviations for states (lowercase variations)
STATE_ABBREV_LOWER = {
    'pa': 'PA', 'ca': 'CA', 'ny': 'NY', 'tx': 'TX', 'fl': 'FL',
    'il': 'IL', 'oh': 'OH', 'ga': 'GA', 'nc': 'NC', 'nj': 'NJ',
    'va': 'VA', 'wa': 'WA', 'ma': 'MA', 'az': 'AZ', 'co': 'CO',
    'mn': 'MN', 'wi': 'WI', 'mo': 'MO', 'md': 'MD', 'sc': 'SC',
    'al': 'AL', 'la': 'LA', 'ky': 'KY', 'ct': 'CT', 'ia': 'IA',
    'ms': 'MS', 'ar': 'AR', 'ut': 'UT', 'nv': 'NV', 'ks': 'KS',
    'ne': 'NE', 'nm': 'NM', 'wv': 'WV', 'id': 'ID', 'nh': 'NH',
    'ri': 'RI', 'mt': 'MT', 'de': 'DE', 'sd': 'SD', 'nd': 'ND',
    'ak': 'AK', 'vt': 'VT', 'wy': 'WY', 'dc': 'DC', 'tn': 'TN',
    'hi': 'HI', 'me': 'ME', 'or': 'OR', 'ok': 'OK', 'in': 'IN',
}


# ─── DETECTION FUNCTIONS ─────────────────────────────────────────────────

def is_phone_number(s):
    """Detect if a string is actually a phone number."""
    digits = re.sub(r'[^0-9]', '', s)
    if len(digits) >= 7:
        return True
    if re.match(r'^[\+\d\s\(\)\-\.]+$', s.strip()) and len(digits) >= 7:
        return True
    return False


def is_garbage(s):
    """Detect garbage data that isn't a real location."""
    if not s or not s.strip():
        return True
    s = s.strip()
    
    # Phone numbers
    if is_phone_number(s):
        return True
    
    # Single character or dash
    if len(s) <= 2 and s not in ABBREV_SET:
        return True
    if s in ('-', '--', '...', 'N/A', 'n/a', 'na', 'NA', 'TBD', 'Unknown', 'unknown', 'UNKNOWN'):
        return True
    
    # Starts with a number followed by a period (like "33.�")
    if re.match(r'^\d+\.', s):
        return True
    
    # Email addresses
    if '@' in s:
        return True
    
    # URLs
    if s.startswith('http') or s.startswith('www.'):
        return True
    
    return False


def is_company_or_title(s):
    """Detect if the string looks like a company name or job title rather than a location."""
    lower = s.lower().strip()
    
    # Job title indicators
    title_keywords = [
        'director', 'manager', 'president', 'vp ', 'vice president',
        'recruiter', 'partner', 'consultant', 'specialist', 'analyst',
        'coordinator', 'operations', 'services', 'solutions', 'global',
        'lead', 'head of', 'chief', 'officer', 'founder', 'ceo', 'cto',
        'senior', 'junior', 'principal', 'associate',
    ]
    for kw in title_keywords:
        if kw in lower:
            return True
    
    # Company suffixes
    company_suffixes = [
        'inc', 'llc', 'corp', 'ltd', 'group', 'partners', 'consulting',
        'staffing', 'technologies', 'tech', 'search', 'worldwide',
        'international', 'associates', 'agency',
    ]
    words = lower.split()
    if words and words[-1] in company_suffixes:
        return True
    
    return False


def is_international(s):
    """Check if location is international (non-US)."""
    lower = s.lower().strip()
    
    # Direct country match
    if lower in COUNTRIES:
        return True
    
    # Contains country name (e.g., "London, United Kingdom")
    for country in COUNTRIES:
        if country in lower:
            return True
    
    return False


# ─── PARSING ─────────────────────────────────────────────────────────────

def clean_location_string(loc):
    """Clean a raw location string for parsing."""
    if not loc:
        return None
    
    s = loc.strip()
    
    # Remove leading numbers with dots/special chars (e.g., "33.� Inceed")
    s = re.sub(r'^[\d]+\.[\S]*\s*', '', s)
    
    # Remove common company-name prefixes that sometimes prepend locations
    # e.g., "33.� Inceed Tulsa, Oklahoma" -> try to extract "Tulsa, Oklahoma"
    # Look for a known "City, State" pattern anywhere in the string
    city_state_match = re.search(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s*,\s*([A-Za-z\s]+)', s)
    if city_state_match:
        potential = city_state_match.group(0).strip()
        # Verify the state part is valid
        state_part = city_state_match.group(2).strip()
        if (state_part.upper() in ABBREV_SET or 
            state_part.lower() in US_STATES or 
            state_part.lower() in STATE_MISSPELLINGS):
            s = potential
    
    # Remove zip codes
    s = re.sub(r'\b\d{5}(-\d{4})?\b', '', s).strip().rstrip(',').strip()
    
    # Remove country suffixes
    for suffix in [', United States', ', USA', ', US', ', U.S.', ', U.S.A.', ', United States of America']:
        if s.lower().endswith(suffix.lower()):
            s = s[:-len(suffix)].strip()
    
    # Clean up extra whitespace and tabs
    s = re.sub(r'[\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s if s else None


def parse_location(loc_str):
    """
    Parse a location string into (city, state_abbrev, confidence).
    
    Returns (city, state, confidence) where:
        city: Properly title-cased city name, or None
        state: 2-letter state abbreviation, or None
        confidence: 'high', 'medium', 'low', or None (skip this record)
    """
    if not loc_str:
        return None, None, None
    
    # Garbage detection
    if is_garbage(loc_str):
        return None, None, None
    
    if is_company_or_title(loc_str):
        return None, None, None
    
    if is_international(loc_str):
        return None, None, None
    
    cleaned = clean_location_string(loc_str)
    if not cleaned or is_garbage(cleaned):
        return None, None, None
    
    # Remove "Remote - " prefix but keep what follows
    for prefix in ['Remote - ', 'Remote- ', 'Remote -', 'Remote-']:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    if cleaned.lower() in ('remote', 'hybrid', 'onsite', 'on-site'):
        return None, None, None
    
    # Remove "Greater " and "Metropolitan" and "Area"
    cleaned = re.sub(r'^Greater\s+', '', cleaned)
    cleaned = re.sub(r'\s+Metropolitan\s+Area$', '', cleaned)
    cleaned = re.sub(r'\s+Metro\s+Area$', '', cleaned)
    cleaned = re.sub(r'\s+Area$', '', cleaned)
    
    # ─── Pattern 1: "City, ST" (highest confidence) ───
    m = re.match(r'^(.+?)\s*,\s*([A-Za-z]{2})\s*$', cleaned)
    if m:
        city_part = m.group(1).strip()
        state_part = m.group(2).strip().upper()
        if state_part in ABBREV_SET:
            city_clean = city_part.title()
            return city_clean, state_part, 'high'
    
    # ─── Pattern 2: "City,ST" (no space, like "Houston,Texas" or "Raleigh,NC") ───
    m = re.match(r'^(.+?),\s*(.+)$', cleaned)
    if m:
        city_part = m.group(1).strip()
        state_part = m.group(2).strip()
        
        # State as abbreviation
        if state_part.upper() in ABBREV_SET:
            return city_part.title(), state_part.upper(), 'high'
        
        # State as full name
        if state_part.lower() in US_STATES:
            return city_part.title(), US_STATES[state_part.lower()], 'high'
        
        # State as misspelling
        if state_part.lower() in STATE_MISSPELLINGS:
            return city_part.title(), STATE_MISSPELLINGS[state_part.lower()], 'medium'
    
    # ─── Pattern 3: Single word that's a full state name ───
    if cleaned.lower() in US_STATES:
        return None, US_STATES[cleaned.lower()], 'medium'
    
    # ─── Pattern 4: Single word that's a state misspelling ───
    if cleaned.lower() in STATE_MISSPELLINGS:
        return None, STATE_MISSPELLINGS[cleaned.lower()], 'low'
    
    # ─── Pattern 5: Just a 2-letter state abbreviation ───
    if len(cleaned) == 2 and cleaned.upper() in ABBREV_SET:
        return None, cleaned.upper(), 'medium'
    
    # ─── Pattern 6: "City State" without comma (e.g., "San Francisco California") ───
    for state_name, abbrev in sorted(US_STATES.items(), key=lambda x: -len(x[0])):
        if cleaned.lower().endswith(' ' + state_name):
            city_part = cleaned[:-(len(state_name)+1)].strip()
            if city_part and not is_garbage(city_part):
                return city_part.title(), abbrev, 'medium'
    
    # If we can't parse it confidently, return None — don't guess
    return None, None, None


# ─── MAIN ENRICHMENT LOGIC ──────────────────────────────────────────────

def run_phase1(conn, dry_run=False, batch_size=5000):
    """
    Phase 1: Parse existing location strings into proper state + normalized_city.
    Also FIX records where state is clearly wrong (e.g., loc='New York, NY' but state='TX').
    """
    print("\n" + "="*60)
    print("PHASE 1: Parse & fix state/city from existing location strings")
    print("="*60)
    
    # Get ALL records with location (to fix bad state assignments too)
    rows = conn.execute(text("""
        SELECT recruiter_id, location, state, normalized_city 
        FROM recruiters 
        WHERE is_active = true 
          AND location IS NOT NULL AND location != ''
    """)).fetchall()
    
    print(f"Total records with location: {len(rows)}")
    
    updates = []
    stats = {'skipped_garbage': 0, 'skipped_international': 0, 
             'skipped_company': 0, 'skipped_unparseable': 0,
             'fixed_state': 0, 'fixed_city': 0, 'already_correct': 0,
             'high_conf': 0, 'medium_conf': 0, 'low_conf': 0}
    
    for row in rows:
        rid = row[0]
        loc = row[1]
        current_state = row[2]
        current_city = row[3]
        
        city, state, confidence = parse_location(loc)
        
        if confidence is None:
            if is_garbage(loc):
                stats['skipped_garbage'] += 1
            elif is_international(loc):
                stats['skipped_international'] += 1
            elif is_company_or_title(loc):
                stats['skipped_company'] += 1
            else:
                stats['skipped_unparseable'] += 1
            continue
        
        stats[f'{confidence}_conf'] += 1
        
        needs_update = False
        new_state = current_state
        new_city = current_city
        
        # Fix state if it's wrong or missing
        if state:
            if not current_state or current_state == '':
                new_state = state
                needs_update = True
            elif current_state != state and confidence == 'high':
                # Only override existing state if we have HIGH confidence
                new_state = state
                needs_update = True
                stats['fixed_state'] += 1
        
        # Fix normalized_city if it's wrong or missing
        if city:
            proper_city = city.strip()
            
            def city_needs_fixing(current):
                """Check if the current city value is bad and needs replacement."""
                if not current or current == '':
                    return True
                if is_garbage(current) or is_phone_number(current):
                    return True
                # City contains state abbreviation (e.g., "dallas, tx" or "new york, ny")
                c = current.strip()
                m = re.match(r'^(.+?)\s*,\s*([A-Za-z]{2})\s*$', c)
                if m and m.group(2).upper() in ABBREV_SET:
                    return True
                # City is just a state name or abbreviation stored in city field
                if c.upper() in ABBREV_SET or c.lower() in US_STATES:
                    return True
                return False
            
            if city_needs_fixing(current_city):
                new_city = proper_city
                needs_update = True
                stats['fixed_city'] += 1
        
        if needs_update:
            updates.append({"rid": rid, "state": new_state, "city": new_city})
        else:
            stats['already_correct'] += 1
    
    print(f"\nParsing Results:")
    print(f"  High confidence:    {stats['high_conf']}")
    print(f"  Medium confidence:  {stats['medium_conf']}")
    print(f"  Low confidence:     {stats['low_conf']}")
    print(f"  Skipped garbage:    {stats['skipped_garbage']}")
    print(f"  Skipped intl:       {stats['skipped_international']}")
    print(f"  Skipped company:    {stats['skipped_company']}")
    print(f"  Skipped unparseable:{stats['skipped_unparseable']}")
    print(f"  Already correct:    {stats['already_correct']}")
    print(f"  States fixed:       {stats['fixed_state']}")
    print(f"  Cities fixed:       {stats['fixed_city']}")
    print(f"  Total to update:    {len(updates)}")
    
    if dry_run:
        print(f"\n[DRY RUN] Samples:")
        for u in updates[:15]:
            print(f"  ID {u['rid']}: state={u['state']}, city={u['city']}")
        return
    
    # Execute in batches
    total = 0
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        conn.execute(
            text("""
                UPDATE recruiters 
                SET state = :state,
                    normalized_city = :city,
                    last_scan_at = now()
                WHERE recruiter_id = :rid
            """),
            batch
        )
        conn.commit()
        total += len(batch)
        print(f"  Batch done: {len(batch)} | Running total: {total}")
    
    print(f"Phase 1 complete: {total} records updated")


def run_phase2(conn, dry_run=False, batch_size=5000):
    """
    Phase 2: Fill missing location from company peers.
    Only when >= 60% of same-company peers share the same location (strong consensus).
    """
    print("\n" + "="*60)
    print("PHASE 2: Fill missing location from company peer consensus")
    print("="*60)
    
    # Get companies with strong location consensus
    consensus = conn.execute(text("""
        WITH company_locs AS (
            SELECT company_id, location, COUNT(*) as cnt,
                   SUM(COUNT(*)) OVER (PARTITION BY company_id) as total_with_loc
            FROM recruiters 
            WHERE is_active = true 
              AND location IS NOT NULL AND location != ''
              AND company_id IS NOT NULL
            GROUP BY company_id, location
        )
        SELECT company_id, location, cnt, total_with_loc,
               ROUND(cnt::numeric / total_with_loc * 100, 1) as pct
        FROM company_locs
        WHERE cnt::numeric / total_with_loc >= 0.6  -- 60% consensus threshold
          AND total_with_loc >= 3                     -- At least 3 peers have location
        ORDER BY company_id, cnt DESC
    """)).fetchall()
    
    # Keep only the top location per company
    company_loc = {}
    for row in consensus:
        cid, loc, cnt, total, pct = row
        if cid not in company_loc:
            company_loc[cid] = (loc, float(pct))
    
    print(f"Companies with strong location consensus: {len(company_loc)}")
    
    # Get recruiters missing location in those companies
    missing = conn.execute(text("""
        SELECT recruiter_id, company_id
        FROM recruiters 
        WHERE is_active = true 
          AND (location IS NULL OR location = '')
          AND company_id IS NOT NULL
    """)).fetchall()
    
    print(f"Recruiters missing location: {len(missing)}")
    
    updates = []
    for row in missing:
        rid, cid = row
        if cid in company_loc:
            loc, pct = company_loc[cid]
            city, state, conf = parse_location(loc)
            if conf:  # Only if parseable
                updates.append({
                    "rid": rid, "loc": loc,
                    "city": city, "state": state,
                    "confidence": f"peer-{pct}%"
                })
    
    print(f"Can fill from peer consensus: {len(updates)}")
    
    if dry_run:
        print(f"\n[DRY RUN] Samples:")
        for u in updates[:15]:
            print(f"  ID {u['rid']}: loc={u['loc']}, city={u['city']}, state={u['state']} ({u['confidence']})")
        return
    
    total = 0
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        conn.execute(
            text("""
                UPDATE recruiters 
                SET location = :loc,
                    state = COALESCE(:state, state),
                    normalized_city = COALESCE(:city, normalized_city),
                    location_confidence = :confidence,
                    last_scan_at = now()
                WHERE recruiter_id = :rid
            """),
            batch
        )
        conn.commit()
        total += len(batch)
        print(f"  Batch done: {len(batch)} | Running total: {total}")
    
    print(f"Phase 2 complete: {total} records updated")


def run_phase3(conn, dry_run=False):
    """
    Phase 3: Clean garbage from location/city/state fields.
    Remove phone numbers, dashes, etc. that were incorrectly stored.
    """
    print("\n" + "="*60)
    print("PHASE 3: Clean garbage data from location fields")
    print("="*60)
    
    # Find records where normalized_city is a phone number
    garbage_cities = conn.execute(text("""
        SELECT recruiter_id, normalized_city 
        FROM recruiters 
        WHERE is_active = true
          AND normalized_city IS NOT NULL
          AND (
              normalized_city ~ '^[\\d\\-\\+\\(\\)\\s]+$'
              OR normalized_city IN ('-', '--', '.', 'N/A', 'n/a', 'Unknown')
              OR LENGTH(normalized_city) < 2
          )
    """)).fetchall()
    
    print(f"Records with garbage in normalized_city: {len(garbage_cities)}")
    
    if not dry_run and garbage_cities:
        ids = [r[0] for r in garbage_cities]
        for i in range(0, len(ids), 5000):
            batch = ids[i:i+5000]
            id_list = ','.join(str(x) for x in batch)
            conn.execute(text(f"""
                UPDATE recruiters 
                SET normalized_city = NULL 
                WHERE recruiter_id IN ({id_list})
            """))
            conn.commit()
            print(f"  Cleaned {len(batch)} garbage city values")
    
    # Find records where location is a phone number
    garbage_locs = conn.execute(text(r"""
        SELECT recruiter_id, location 
        FROM recruiters 
        WHERE is_active = true
          AND location IS NOT NULL
          AND location ~ '^[\+]?[\d\s\-\(\)\.]+$'
          AND LENGTH(REGEXP_REPLACE(location, '[^0-9]', '', 'g')) >= 7
    """)).fetchall()
    
    print(f"Records with phone numbers in location: {len(garbage_locs)}")
    
    if not dry_run and garbage_locs:
        ids = [r[0] for r in garbage_locs]
        for i in range(0, len(ids), 5000):
            batch = ids[i:i+5000]
            id_list = ','.join(str(x) for x in batch)
            conn.execute(text(f"""
                UPDATE recruiters 
                SET location = NULL, normalized_city = NULL
                WHERE recruiter_id IN ({id_list})
            """))
            conn.commit()
            print(f"  Cleaned {len(batch)} phone-in-location values")


def final_stats(conn):
    """Print final field completeness."""
    print("\n" + "="*60)
    print("FINAL STATS")
    print("="*60)
    
    r = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE location IS NOT NULL AND location != '') as loc,
            COUNT(*) FILTER (WHERE state IS NOT NULL AND state != '') as st,
            COUNT(*) FILTER (WHERE normalized_city IS NOT NULL AND normalized_city != '') as city
        FROM recruiters WHERE is_active = true
    """)).fetchone()
    
    db_size = conn.execute(text(
        "SELECT pg_database_size(current_database()) / (1024 * 1024)"
    )).fetchone()[0]
    
    print(f"Total Active: {r[0]}")
    print(f"Location:     {r[1]} / {r[0]} ({round(r[1]/r[0]*100,1)}%)")
    print(f"State:        {r[2]} / {r[0]} ({round(r[2]/r[0]*100,1)}%)")
    print(f"Norm. City:   {r[3]} / {r[0]} ({round(r[3]/r[0]*100,1)}%)")
    print(f"DB Size:      {db_size} MB (limit: 450 MB)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Run specific phase only")
    parser.add_argument("--batch-size", type=int, default=5000)
    args = parser.parse_args()
    
    with engine.connect() as conn:
        db_size = conn.execute(text(
            "SELECT pg_database_size(current_database()) / (1024 * 1024)"
        )).fetchone()[0]
        print(f"DB Size: {db_size} MB (limit: 450 MB)")
        if db_size > 440:
            print("DATABASE TOO CLOSE TO LIMIT. Aborting.")
            sys.exit(1)
        
        if args.phase == 1 or not args.phase:
            run_phase1(conn, dry_run=args.dry_run, batch_size=args.batch_size)
        if args.phase == 2 or not args.phase:
            run_phase2(conn, dry_run=args.dry_run, batch_size=args.batch_size)
        if args.phase == 3 or not args.phase:
            run_phase3(conn, dry_run=args.dry_run)
        
        final_stats(conn)
