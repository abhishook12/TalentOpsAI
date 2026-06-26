#!/usr/bin/env python
from __future__ import annotations

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def run_fast_repair():
    start_time = time.time()
    print("Starting Ultra-Fast Full Throttle SQL Database Repair Engine...")
    db = SessionLocal()
    
    try:
        # 1. Dummy Email Quarantine
        print("1/4 Quarantining dummy and corrupted email records...")
        res1 = db.execute(text("""
            UPDATE recruiters 
            SET email_status = 'invalid',
                needs_review = true,
                review_reason = CASE 
                    WHEN review_reason IS NULL OR review_reason = '' THEN 'Quarantined: Dummy/placeholder email'
                    WHEN review_reason NOT LIKE '%Dummy/placeholder email%' THEN review_reason || ' | Quarantined: Dummy/placeholder email'
                    ELSE review_reason 
                END
            WHERE (email ILIKE '%@missing.local%' OR email ILIKE '%tavily_discovery%' OR email ILIKE '%unknown%')
              AND (email_status IS DISTINCT FROM 'invalid');
        """))
        print(f"   -> Quarantined {res1.rowcount} dummy email rows.")
        
        # 2. Corporate Entities Masquerading as Humans
        print("2/4 Auditing entity misclassifications (companies saved as recruiters)...")
        res2 = db.execute(text("""
            UPDATE recruiters
            SET needs_review = true,
                review_reason = CASE 
                    WHEN review_reason IS NULL OR review_reason = '' THEN 'Entity Misclassification: Name appears to be a corporate entity'
                    WHEN review_reason NOT LIKE '%corporate entity%' THEN review_reason || ' | Entity Misclassification: Name appears to be a corporate entity'
                    ELSE review_reason 
                END
            WHERE (recruiter_name ILIKE '% Inc' OR recruiter_name ILIKE '% LLC' OR recruiter_name ILIKE '% Solutions' OR recruiter_name ILIKE '% Group' OR recruiter_name ILIKE '% Global' OR recruiter_name ILIKE '% Services' OR recruiter_name ILIKE '% Staffing' OR recruiter_name ILIKE '% Technologies' OR recruiter_name ILIKE '% Consulting' OR recruiter_name ILIKE '% Agency' OR recruiter_name ILIKE '% Corporation' OR recruiter_name ILIKE '% Corp' OR recruiter_name ILIKE '% Partners')
              AND (needs_review IS DISTINCT FROM true);
        """))
        print(f"   -> Flagged {res2.rowcount} corporate entity rows.")
        
        # 3. Offshore Location Quarantine
        print("3/4 Quarantining offshore / non-North America recruiter profiles...")
        res3 = db.execute(text("""
            UPDATE recruiters
            SET is_active = false,
                needs_review = true,
                review_reason = CASE 
                    WHEN review_reason IS NULL OR review_reason = '' THEN 'Offshore Location Detected'
                    WHEN review_reason NOT LIKE '%Offshore Location%' THEN review_reason || ' | Offshore Location Detected'
                    ELSE review_reason 
                END
            WHERE (location ILIKE '%india%' OR location ILIKE '%united kingdom%' OR location ILIKE '%england%' OR location ILIKE '%london%' OR location ILIKE '%philippines%' OR location ILIKE '%europe%' OR location ILIKE '%australia%' OR location ILIKE '%pakistan%' OR location ILIKE '%bengaluru%' OR location ILIKE '%hyderabad%' OR location ILIKE '%pune%' OR location ILIKE '%manila%' OR location ILIKE '%bracknell%' OR location ILIKE '%germany%' OR location ILIKE '%france%')
              AND (is_active = true OR needs_review IS DISTINCT FROM true);
        """))
        print(f"   -> Quarantined {res3.rowcount} offshore rows.")
        
        # 4. Instant State Reconstruction for Major Tech Hubs
        print("4/4 Reconstructing missing US States from city/location strings...")
        state_map = {
            'TX': ['%texas%', '%dallas%', '%austin%', '%houston%', '%san antonio%', '%fort worth%', '%plano%', '%irving%'],
            'CA': ['%california%', '%los angeles%', '%san francisco%', '%san diego%', '%san jose%', '%sacramento%', '%irvine%', '%palo alto%', '%mountain view%', '%sunnyvale%', '%oakland%'],
            'NY': ['%new york%', '%nyc%', '%brooklyn%', '%manhattan%', '%queens%', '%bronx%', '%staten island%', '%buffalo%', '%albany%'],
            'FL': ['%florida%', '%miami%', '%tampa%', '%orlando%', '%jacksonville%', '%fort lauderdale%', '%boca raton%', '%st. petersburg%'],
            'IL': ['%illinois%', '%chicago%', '%naperville%', '%evanston%'],
            'GA': ['%georgia%', '%atlanta%', '%alpharetta%', '%marietta%'],
            'NC': ['%north carolina%', '%charlotte%', '%raleigh%', '%durham%', '%cary%', '%wilmington%'],
            'PA': ['%pennsylvania%', '%philadelphia%', '%pittsburgh%', '%king of prussia%'],
            'MA': ['%massachusetts%', '%boston%', '%cambridge%', '%waltham%'],
            'WA': ['%washington%', '%seattle%', '%bellevue%', '%redmond%', '%kirkland%'],
            'CO': ['%colorado%', '%denver%', '%boulder%', '%colorado springs%'],
            'AZ': ['%arizona%', '%phoenix%', '%scottsdale%', '%tempe%', '%mesa%'],
            'UT': ['%utah%', '%salt lake city%', '%lehi%', '%provo%'],
            'VA': ['%virginia%', '%mclean%', '%arlington%', '%reston%', '%herndon%', '%alexandria%', '%richmond%'],
            'OH': ['%ohio%', '%columbus%', '%cleveland%', '%cincinnati%'],
            'MI': ['%michigan%', '%detroit%', '%ann arbor%', '%grand rapids%'],
            'NJ': ['%new jersey%', '%jersey city%', '%hoboken%', '%newark%', '%princeton%'],
            'MD': ['%maryland%', '%baltimore%', '%bethesda%', '%rockville%'],
            'MN': ['%minnesota%', '%minneapolis%', '%st. paul%'],
            'TN': ['%tennessee%', '%nashville%', '%memphis%', '%knoxville%'],
            'MO': ['%missouri%', '%st. louis%', '%kansas city%'],
            'IN': ['%indiana%', '%indianapolis%'],
            'OR': ['%oregon%', '%portland%'],
            'WI': ['%wisconsin%', '%milwaukee%', '%madison%'],
            'DC': ['%washington dc%', '%district of columbia%', '%washington, d.c.%']
        }
        
        total_states_fixed = 0
        for st_code, patterns in state_map.items():
            conds = " OR ".join([f"location ILIKE '{p}'" for p in patterns])
            res_st = db.execute(text(f"""
                UPDATE recruiters 
                SET state = '{st_code}'
                WHERE (state IS NULL OR state = '') 
                  AND ({conds});
            """))
            total_states_fixed += res_st.rowcount
            
        print(f"   -> Reconstructed {total_states_fixed} missing US state codes.")
        
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"\nFull Throttle Database Optimization Complete in {elapsed} seconds!")
        print(f"EXECUTIVE AUDIT TALLY:")
        print(f"   - Dummy Emails Quarantined: {res1.rowcount}")
        print(f"   - Corporate Entities Flagged: {res2.rowcount}")
        print(f"   - Offshore Profiles Disabled: {res3.rowcount}")
        print(f"   - Missing States Reconstructed: {total_states_fixed}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error executing fast SQL repairs: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_fast_repair()
