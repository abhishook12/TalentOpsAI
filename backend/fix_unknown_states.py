#!/usr/bin/env python
from __future__ import annotations

import sys
import os
import time
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def fix_unknowns():
    start_time = time.time()
    print("Starting Deep State Reconstruction & Cleanup for 31,383 Unknown Records...")
    db = SessionLocal()
    
    try:
        # 1. Move phone numbers trapped inside the location column to the phone column
        print("1/4 Salvaging phone numbers trapped inside location fields...")
        res_ph = db.execute(text("""
            UPDATE recruiters 
            SET phone = location,
                location = NULL
            WHERE (phone IS NULL OR phone = '')
              AND (location ~ '^\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}$');
        """))
        print(f"   -> Salvaged {res_ph.rowcount} trapped phone numbers.")
        
        # 2. Nullify corrupt/placeholder location strings
        print("2/4 Nullifying corrupt placeholder locations ('-', '0', 'NIL', '#ERROR!')...")
        res_null = db.execute(text("""
            UPDATE recruiters
            SET location = NULL
            WHERE location IN ('-', '--', '---', '0', 'NIL', 'nil', '#ERROR!', '', 'N/A')
               OR location ~ '^[0-9]+$';
        """))
        print(f"   -> Cleaned {res_null.rowcount} corrupted location fields.")
        
        # 3. Inherit State from Parent Company HQ for NULL location records
        print("3/4 Reconstructing states from parent Company HQ metadata...")
        state_map = {
            'TX': ['%texas%', '%dallas%', '%austin%', '%houston%', '%san antonio%', '%fort worth%', '%plano%', '%irving%', '%, TX%'],
            'CA': ['%california%', '%los angeles%', '%san francisco%', '%san diego%', '%san jose%', '%sacramento%', '%irvine%', '%palo alto%', '%mountain view%', '%sunnyvale%', '%, CA%'],
            'NY': ['%new york%', '%nyc%', '%brooklyn%', '%manhattan%', '%queens%', '%bronx%', '%staten island%', '%buffalo%', '%, NY%'],
            'FL': ['%florida%', '%miami%', '%tampa%', '%orlando%', '%jacksonville%', '%fort lauderdale%', '%boca raton%', '%, FL%'],
            'IL': ['%illinois%', '%chicago%', '%naperville%', '%, IL%'],
            'GA': ['%georgia%', '%atlanta%', '%alpharetta%', '%, GA%'],
            'NC': ['%north carolina%', '%charlotte%', '%raleigh%', '%durham%', '%, NC%'],
            'PA': ['%pennsylvania%', '%philadelphia%', '%pittsburgh%', '%, PA%'],
            'MA': ['%massachusetts%', '%boston%', '%cambridge%', '%waltham%', '%, MA%'],
            'WA': ['%washington%', '%seattle%', '%bellevue%', '%redmond%', '%, WA%'],
            'CO': ['%colorado%', '%denver%', '%boulder%', '%, CO%'],
            'AZ': ['%arizona%', '%phoenix%', '%scottsdale%', '%tempe%', '%, AZ%'],
            'UT': ['%utah%', '%salt lake city%', '%lehi%', '%, UT%'],
            'VA': ['%virginia%', '%mclean%', '%arlington%', '%reston%', '%, VA%'],
            'OH': ['%ohio%', '%columbus%', '%cleveland%', '%cincinnati%', '%, OH%'],
            'MI': ['%michigan%', '%detroit%', '%ann arbor%', '%, MI%'],
            'NJ': ['%new jersey%', '%jersey city%', '%princeton%', '%, NJ%'],
            'MD': ['%maryland%', '%baltimore%', '%bethesda%', '%, MD%'],
            'MN': ['%minnesota%', '%minneapolis%', '%, MN%'],
            'TN': ['%tennessee%', '%nashville%', '%, TN%'],
            'MO': ['%missouri%', '%st. louis%', '%, MO%'],
            'IN': ['%indiana%', '%indianapolis%', '%, IN%'],
            'OR': ['%oregon%', '%portland%', '%, OR%'],
            'WI': ['%wisconsin%', '%milwaukee%', '%, WI%'],
            'DC': ['%washington dc%', '%district of columbia%', '%, DC%'],
            'ON': ['%ontario%', '%toronto%', '%ottawa%', '%, ON%'],
            'BC': ['%british columbia%', '%vancouver%', '%, BC%'],
            'QC': ['%quebec%', '%montreal%', '%, QC%']
        }
        
        total_hq_fixed = 0
        for st_code, patterns in state_map.items():
            conds = " OR ".join([f"c.location ILIKE '{p}'" for p in patterns])
            res_hq = db.execute(text(f"""
                UPDATE recruiters r
                SET state = '{st_code}'
                FROM companies c
                WHERE r.company_id = c.company_id
                  AND (r.state IS NULL OR r.state = '')
                  AND ({conds});
            """))
            total_hq_fixed += res_hq.rowcount
            
        print(f"   -> Reconstructed {total_hq_fixed} states from company HQ metadata.")
        
        # 4. Standardize USA/United States only records to 'US' (National/Remote)
        print("4/4 Standardizing generic national locations ('USA', 'United States') to 'US'...")
        res_us = db.execute(text("""
            UPDATE recruiters
            SET state = 'US'
            WHERE (state IS NULL OR state = '')
              AND location IN ('USA', 'United States', 'US', 'National', 'Remote', 'North America');
        """))
        print(f"   -> Standardized {res_us.rowcount} national records.")
        
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"\nUnknown State Remediation Complete in {elapsed} seconds!")
        print(f"SUMMARY TALLY:")
        print(f"   - Phone Numbers Salvaged: {res_ph.rowcount}")
        print(f"   - Corrupt Fields Purged: {res_null.rowcount}")
        print(f"   - States Inherited from Company HQ: {total_hq_fixed}")
        print(f"   - National Records Standardized: {res_us.rowcount}")
        
    except Exception as e:
        db.rollback()
        print(f"Error executing deep state cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_unknowns()
