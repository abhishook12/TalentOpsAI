import os
import sys
import time
import re
import urllib.request
import csv
from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.state_mapper import STATE_MAP
from app.utils.state_recovery import build_company_domain_state_index, infer_state_from_domain

ABBR_TO_NAME = {v: k for k, v in STATE_MAP.items()}
STATE_NAME_TO_ABBR = {k.lower(): v for k, v in STATE_MAP.items()}

# Map of major cities to states for fallback
CITY_STATE_RULES = [
    ('atlanta', 'GA'), ('georgia', 'GA'), ('savannah', 'GA'),
    ('dallas', 'TX'), ('austin', 'TX'), ('houston', 'TX'), ('san antonio', 'TX'), ('texas', 'TX'),
    ('new york', 'NY'), ('nyc', 'NY'), ('brooklyn', 'NY'), ('manhattan', 'NY'),
    ('chicago', 'IL'), ('illinois', 'IL'),
    ('los angeles', 'CA'), ('san francisco', 'CA'), ('san diego', 'CA'), ('bay area', 'CA'), ('california', 'CA'),
    ('miami', 'FL'), ('tampa', 'FL'), ('orlando', 'FL'), ('jacksonville', 'FL'), ('florida', 'FL'),
    ('seattle', 'WA'), ('washington', 'WA'),
    ('boston', 'MA'), ('massachusetts', 'MA'),
    ('charlotte', 'NC'), ('raleigh', 'NC'), ('north carolina', 'NC'),
    ('denver', 'CO'), ('colorado', 'CO'),
    ('phoenix', 'AZ'), ('scottsdale', 'AZ'), ('arizona', 'AZ'),
    ('philadelphia', 'PA'), ('pittsburgh', 'PA'), ('pennsylvania', 'PA'),
    ('detroit', 'MI'), ('michigan', 'MI'),
    ('minneapolis', 'MN'), ('minnesota', 'MN'),
    ('columbus', 'OH'), ('cleveland', 'OH'), ('cincinnati', 'OH'), ('ohio', 'OH'),
    ('nashville', 'TN'), ('tennessee', 'TN'),
    ('st. louis', 'MO'), ('kansas city', 'MO'), ('missouri', 'MO'),
    ('indianapolis', 'IN'), ('indiana', 'IN'),
    ('salt lake city', 'UT'), ('utah', 'UT'),
    ('richmond', 'VA'), ('virginia', 'VA'),
    ('baltimore', 'MD'), ('maryland', 'MD'),
    ('portland', 'OR'), ('oregon', 'OR'),
    ('las vegas', 'NV'), ('nevada', 'NV')
]

AREA_CODE_MAP = {}

def load_area_codes():
    print("Downloading area codes...")
    try:
        response = urllib.request.urlopen('https://raw.githubusercontent.com/ravisorg/Area-Code-Geolocation-Database/master/us-area-code-cities.csv')
        lines = response.read().decode('utf-8').splitlines()
        reader = csv.reader(lines)
        for row in reader:
            if len(row) >= 3:
                ac = row[0].strip()
                state_name = row[2].strip().lower()
                if state_name in STATE_NAME_TO_ABBR:
                    AREA_CODE_MAP[ac] = STATE_NAME_TO_ABBR[state_name]
        print(f"Loaded {len(AREA_CODE_MAP)} area codes.")
    except Exception as e:
        print("Failed to download area codes:", e)

def extract_state_from_location(location: str):
    if not location:
        return None
    match = re.search(r'\b([A-Z]{2})\b', location)
    if match and match.group(1).upper() in ABBR_TO_NAME:
        return match.group(1).upper()
        
    loc_lower = location.lower()
    for city, st in CITY_STATE_RULES:
        if city in loc_lower:
            return st
    return None

def extract_state_from_phone(phone: str):
    if not phone:
        return None
    # Extract first 3 consecutive digits
    match = re.search(r'\(?(\d{3})\)?', phone)
    if match:
        ac = match.group(1)
        return AREA_CODE_MAP.get(ac)
    return None

def resolve_states_in_bulk():
    print("=== STARTING LOCAL STATE CONQUEST V3 (DOMAIN INFERENCE) ===", flush=True)
    t0 = time.time()
    db = SessionLocal()
    
    load_area_codes()
    
    try:
        print("Building Company Domain State Index...", flush=True)
        companies = db.query(Company).all()
        domain_index = build_company_domain_state_index(companies)
        print(f"Domain Index built. {len(domain_index)} unique corporate domains.")
        
        print("Querying recruiters with unknown states...", flush=True)
        recruiters = db.query(Recruiter).options(joinedload(Recruiter.company)).filter(
            (Recruiter.state == None) | (Recruiter.state == '') | (Recruiter.state == 'US')
        ).all()
        
        initial_unknown = len(recruiters)
        print(f"Found {initial_unknown:,} recruiters needing state resolution.")
        
        mappings = []
        
        for r in recruiters:
            new_state = None
            
            # 1. Try recruiter location string
            new_state = extract_state_from_location(r.location)
            
            # 2. Try company state or location string
            if not new_state and r.company:
                if r.company.state and r.company.state != 'US' and len(r.company.state.strip()) == 2:
                    new_state = r.company.state.strip().upper()
                else:
                    new_state = extract_state_from_location(r.company.location)
                    
            # 3. Try Phone Area Code
            if not new_state:
                new_state = extract_state_from_phone(r.phone)
                
            # 4. Try Email Domain Inference
            if not new_state and r.email and "missing.local" not in r.email:
                inferred_state, _, _ = infer_state_from_domain(r.email, domain_index)
                if inferred_state:
                    new_state = inferred_state
                
            if new_state:
                mappings.append({'recruiter_id': r.recruiter_id, 'state': new_state})
                
        resolved_count = len(mappings)
        print(f"Successfully resolved states for {resolved_count:,} recruiters locally. Saving...", flush=True)
        
        if mappings:
            chunk_size = 5000
            for i in range(0, resolved_count, chunk_size):
                chunk = mappings[i:i + chunk_size]
                db.bulk_update_mappings(Recruiter, chunk)
                db.commit()
                print(f" -> Saved chunk {i} to {i + len(chunk)}", flush=True)
                
        print(f"\n=== STATE CONQUEST COMPLETE ===")
        print(f"Time Elapsed: {time.time() - t0:.2f}s")
        print(f"Remaining Unknown: {initial_unknown - resolved_count:,}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    resolve_states_in_bulk()
