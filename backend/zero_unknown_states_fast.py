#!/usr/bin/env python
from __future__ import annotations
import sys
import os
import time
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.models import Recruiter, Company
from sqlalchemy import text

def zero_out_unknowns_fast():
    start_time = time.time()
    db = SessionLocal()
    
    try:
        # Pull raw data as tuples to avoid ORM overhead
        raw_recruiters = db.execute(text("SELECT recruiter_id, location, company_id FROM recruiters WHERE state IS NULL OR state = ''")).fetchall()
        raw_companies = db.execute(text("SELECT company_id, state, location FROM companies")).fetchall()
        
        comp_map = {row[0]: {'state': row[1], 'location': row[2]} for row in raw_companies}
        
        state_regex = re.compile(r'\b([A-Z]{2})\b')
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
            loc_upper = str(loc_str).upper()
            for full_name, abbr in stateNameToAbbrUpper.items():
                if full_name in loc_upper: return abbr
            match = state_regex.search(loc_upper)
            if match: return match.group(1)
            return None

        updates = []
        for r in raw_recruiters:
            r_id, r_loc, r_cid = r
            found_state = extract_state(r_loc)
            
            if not found_state and r_cid:
                comp = comp_map.get(r_cid)
                if comp:
                    found_state = extract_state(comp['state']) or extract_state(comp['location'])

            if not found_state:
                found_state = 'US'
                
            updates.append({'r_id': r_id, 'st': found_state})

        # Batch update!
        db.execute(
            text("UPDATE recruiters SET state = :st WHERE recruiter_id = :r_id"),
            updates
        )
        db.commit()
        
        elapsed = round(time.time() - start_time, 2)
        print(f"Fast Migration Complete in {elapsed} seconds!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    zero_out_unknowns_fast()
