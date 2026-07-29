#!/usr/bin/env python
from __future__ import annotations

import sys
import os
import time
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.models import Recruiter, Company

def zero_out_unknowns():
    start_time = time.time()
    print("Starting Deep Salvage & Standardization to achieve ZERO Unknown States...")
    db = SessionLocal()
    
    try:
        recruiters = db.query(Recruiter).filter((Recruiter.state == None) | (Recruiter.state == '')).all()
        companies = db.query(Company).all()
        company_map = {c.company_id: c for c in companies}
        
        state_regex = re.compile(r'\b([A-Z]{2})\b')
        salvaged_loc = 0
        fallback = 0
        
        # We also want to map full names to abbreviations
        stateNameToAbbrUpper = {
          "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
          "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA",
          "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
          "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
          "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO",
          "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
          "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
          "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
          "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
          "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
          "DISTRICT OF COLUMBIA": "DC"
        }
        
        def extract_state(loc_str):
            if not loc_str: return None
            loc_upper = loc_str.upper()
            # check full names
            for full_name, abbr in stateNameToAbbrUpper.items():
                if full_name in loc_upper:
                    return abbr
            # check abbreviations
            match = state_regex.search(loc_upper)
            if match:
                return match.group(1)
            return None

        for r in recruiters:
            found_state = extract_state(r.location)
            
            if not found_state and r.company_id:
                comp = company_map.get(r.company_id)
                if comp:
                    found_state = extract_state(comp.state) or extract_state(comp.location)

            if found_state:
                r.state = found_state
                salvaged_loc += 1
            else:
                r.state = 'US'
                fallback += 1
            
        db.commit()
        
        elapsed = round(time.time() - start_time, 2)
        print(f"\nZero Unknown State Remediation Complete in {elapsed} seconds!")
        print(f"FINAL AUDIT TALLY:")
        print(f"   - States Salvaged: {salvaged_loc}")
        print(f"   - Standardized to 'US': {fallback}")
        print(f"   - Total Processed: {len(recruiters)}")
        
    except Exception as e:
        db.rollback()
        print(f"Error executing deep zero cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    zero_out_unknowns()
