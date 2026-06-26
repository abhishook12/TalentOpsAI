#!/usr/bin/env python
from __future__ import annotations

import sys
import os
import time
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def zero_out_unknowns():
    start_time = time.time()
    print("Starting Deep Salvage & Standardization to achieve ZERO Unknown States...")
    db = SessionLocal()
    
    try:
        # 1. Area Code to State Mapping
        print("1/3 Inferring US States from telephone Area Codes (Recruiter Phone & Company Phone)...")
        ac_map = {
            'TX': ['214', '469', '972', '817', '682', '512', '737', '281', '713', '832', '346', '936', '409', '903', '940', '806', '325', '432', '915', '361', '254', '979'],
            'CA': ['213', '310', '323', '424', '818', '626', '562', '714', '949', '951', '909', '805', '661', '415', '650', '510', '925', '408', '669', '831', '707', '916', '209', '559', '858', '619', '760'],
            'NY': ['212', '646', '332', '718', '347', '917', '929', '516', '631', '914', '845', '518', '315', '607', '716', '585'],
            'NJ': ['201', '551', '973', '862', '908', '732', '848', '609', '856'],
            'IL': ['312', '773', '872', '847', '224', '630', '331', '708', '815', '779', '309', '217'],
            'VA': ['703', '571', '804', '757', '540', '434', '276'],
            'MD': ['301', '240', '410', '443', '667'],
            'FL': ['305', '786', '954', '754', '561', '407', '321', '813', '656', '727', '941', '239', '850', '386', '352'],
            'PA': ['215', '267', '484', '610', '717', '814', '412', '724', '878', '570'],
            'GA': ['404', '678', '770', '470', '706', '762', '912', '229', '478'],
            'NC': ['704', '980', '919', '984', '336', '743', '910', '828', '252'],
            'MA': ['617', '857', '781', '339', '508', '774', '413', '978', '351'],
            'WA': ['206', '425', '253', '360', '509'],
            'OH': ['614', '380', '216', '440', '330', '234', '513', '937', '419'],
            'MI': ['313', '248', '947', '586', '734', '810', '616', '517'],
            'CO': ['303', '720', '970', '719'],
            'AZ': ['602', '480', '623', '520', '928'],
            'UT': ['801', '385', '435'],
            'TN': ['615', '629', '901', '865', '423'],
            'MN': ['612', '651', '763', '952', '218', '320'],
            'IN': ['317', '463', '219', '574', '260', '765', '812', '930'],
            'MO': ['314', '636', '816', '417', '573'],
            'WI': ['414', '262', '608', '920', '715'],
            'OR': ['503', '971', '541']
        }
        
        salvaged_ac = 0
        for st_code, codes in ac_map.items():
            conds_ph = " OR ".join([f"r.phone LIKE '{ac}%' OR r.phone LIKE '({ac})%'" for ac in codes])
            conds_co = " OR ".join([f"c.location LIKE '{ac}%' OR c.location LIKE '({ac})%'" for ac in codes])
            
            # Update from recruiter phone
            res_ac1 = db.execute(text(f"""
                UPDATE recruiters r
                SET state = '{st_code}'
                WHERE (r.state IS NULL OR r.state = '')
                  AND ({conds_ph});
            """))
            salvaged_ac += res_ac1.rowcount
            
            # Update from company location phone
            res_ac2 = db.execute(text(f"""
                UPDATE recruiters r
                SET state = '{st_code}'
                FROM companies c
                WHERE r.company_id = c.company_id
                  AND (r.state IS NULL OR r.state = '')
                  AND ({conds_co});
            """))
            salvaged_ac += res_ac2.rowcount
            
        print(f"   -> Salvaged {salvaged_ac} states from telephone area codes.")
        
        # 2. Inherit State from Parent Company state if available
        print("2/3 Inheriting canonical states from parent Company records...")
        res_comp_st = db.execute(text("""
            UPDATE recruiters r
            SET state = UPPER(c.location)
            FROM companies c
            WHERE r.company_id = c.company_id
              AND (r.state IS NULL OR r.state = '')
              AND LENGTH(c.location) = 2;
        """))
        print(f"   -> Inherited {res_comp_st.rowcount} states directly from parent companies.")
        
        # 3. Standardize all remaining legacy unassigned rows to 'US' (National US Directory)
        print("3/3 Standardizing all remaining legacy unassigned rows to canonical 'US' (National Directory)...")
        res_nat = db.execute(text("""
            UPDATE recruiters
            SET state = 'US'
            WHERE state IS NULL OR state = '';
        """))
        print(f"   -> Standardized {res_nat.rowcount} unassigned legacy records to 'US'.")
        
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"\nZero Unknown State Remediation Complete in {elapsed} seconds!")
        print(f"FINAL AUDIT TALLY:")
        print(f"   - States Salvaged via Area Codes: {salvaged_ac}")
        print(f"   - States Inherited from Company HQ: {res_comp_st.rowcount}")
        print(f"   - Legacy Records Aligned to National Directory ('US'): {res_nat.rowcount}")
        
    except Exception as e:
        db.rollback()
        print(f"Error executing deep zero cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    zero_out_unknowns()
