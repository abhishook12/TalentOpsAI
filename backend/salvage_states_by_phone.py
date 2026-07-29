#!/usr/bin/env python
from __future__ import annotations
import sys
import os
import time
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def salvage_states():
    start_time = time.time()
    db = SessionLocal()
    
    # Massive Area Code Mapping
    ac_map = {
        'AL': ['205', '251', '256', '334', '938'],
        'AK': ['907'],
        'AZ': ['480', '520', '602', '623', '928'],
        'AR': ['479', '501', '870'],
        'CA': ['209', '213', '310', '323', '408', '415', '424', '442', '510', '530', '559', '562', '619', '626', '650', '657', '661', '669', '707', '714', '747', '760', '805', '818', '831', '858', '909', '916', '925', '949', '951'],
        'CO': ['303', '719', '720', '970'],
        'CT': ['203', '475', '860', '959'],
        'DE': ['302'],
        'FL': ['239', '305', '321', '352', '386', '407', '561', '727', '754', '772', '786', '813', '850', '863', '904', '941', '954'],
        'GA': ['229', '404', '470', '478', '678', '706', '762', '770', '912'],
        'HI': ['808'],
        'ID': ['208', '986'],
        'IL': ['217', '224', '309', '312', '331', '618', '630', '708', '773', '779', '815', '847', '872'],
        'IN': ['219', '260', '317', '463', '574', '765', '812', '930'],
        'IA': ['319', '515', '563', '641', '712'],
        'KS': ['316', '620', '785', '913'],
        'KY': ['270', '364', '502', '606', '859'],
        'LA': ['225', '318', '337', '504', '985'],
        'ME': ['207'],
        'MD': ['240', '301', '410', '443', '667'],
        'MA': ['339', '351', '413', '508', '617', '774', '781', '857', '978'],
        'MI': ['231', '248', '269', '313', '517', '586', '616', '734', '810', '906', '947', '989'],
        'MN': ['218', '320', '507', '612', '651', '763', '952'],
        'MS': ['228', '662', '601', '769'],
        'MO': ['314', '417', '573', '636', '660', '816'],
        'MT': ['406'],
        'NE': ['308', '402', '531'],
        'NV': ['702', '725', '775'],
        'NH': ['603'],
        'NJ': ['201', '551', '609', '732', '848', '856', '862', '908', '973'],
        'NM': ['505', '575'],
        'NY': ['212', '315', '332', '347', '516', '518', '585', '607', '631', '646', '716', '718', '845', '914', '917', '929'],
        'NC': ['252', '336', '704', '743', '828', '910', '919', '980', '984'],
        'ND': ['701'],
        'OH': ['216', '234', '330', '380', '419', '440', '513', '567', '614', '740', '937'],
        'OK': ['405', '539', '580', '918'],
        'OR': ['458', '503', '541', '971'],
        'PA': ['215', '267', '412', '484', '570', '610', '717', '724', '814', '878'],
        'RI': ['401'],
        'SC': ['843', '864', '803'],
        'SD': ['605'],
        'TN': ['423', '615', '629', '731', '865', '901'],
        'TX': ['210', '214', '254', '281', '325', '346', '361', '409', '432', '469', '512', '682', '713', '737', '806', '817', '832', '903', '915', '936', '940', '972', '979'],
        'UT': ['385', '435', '801'],
        'VT': ['802'],
        'VA': ['276', '434', '540', '571', '703', '757', '804'],
        'WA': ['206', '253', '360', '425', '509'],
        'WV': ['304', '681'],
        'WI': ['262', '414', '534', '608', '715', '920'],
        'WY': ['307']
    }
    
    # Reverse lookup map: area_code -> State
    ac_to_state = {}
    for state, codes in ac_map.items():
        for code in codes:
            ac_to_state[code] = state

    try:
        raw_recruiters = db.execute(text("SELECT recruiter_id, phone, location FROM recruiters WHERE state = 'US'")).fetchall()
        updates = []
        salvaged = 0

        # Pattern to grab first 3 digits that form the area code
        phone_regex = re.compile(r'^\D*1?\D*(\d{3})')
        
        for r_id, phone, loc in raw_recruiters:
            new_st = None
            if phone:
                m = phone_regex.search(str(phone))
                if m:
                    ac = m.group(1)
                    if ac in ac_to_state:
                        new_st = ac_to_state[ac]
            
            # City logic fallback if phone didn't help (Very crude fallback for major cities)
            if not new_st and loc:
                loc_up = str(loc).upper()
                if 'CHICAGO' in loc_up: new_st = 'IL'
                elif 'NEW YORK' in loc_up: new_st = 'NY'
                elif 'LOS ANGELES' in loc_up: new_st = 'CA'
                elif 'HOUSTON' in loc_up: new_st = 'TX'
                elif 'PHOENIX' in loc_up: new_st = 'AZ'
                elif 'PHILADELPHIA' in loc_up: new_st = 'PA'
                elif 'SAN ANTONIO' in loc_up: new_st = 'TX'
                elif 'SAN DIEGO' in loc_up: new_st = 'CA'
                elif 'DALLAS' in loc_up: new_st = 'TX'
                elif 'SAN JOSE' in loc_up: new_st = 'CA'
                elif 'AUSTIN' in loc_up: new_st = 'TX'
                elif 'JACKSONVILLE' in loc_up: new_st = 'FL'
                elif 'FORT WORTH' in loc_up: new_st = 'TX'
                elif 'COLUMBUS' in loc_up: new_st = 'OH'
                elif 'CHARLOTTE' in loc_up: new_st = 'NC'
                elif 'SAN FRANCISCO' in loc_up: new_st = 'CA'
                elif 'INDIANAPOLIS' in loc_up: new_st = 'IN'
                elif 'SEATTLE' in loc_up: new_st = 'WA'
                elif 'DENVER' in loc_up: new_st = 'CO'
                elif 'WASHINGTON' in loc_up: new_st = 'DC'
                elif 'BOSTON' in loc_up: new_st = 'MA'
                elif 'EL PASO' in loc_up: new_st = 'TX'
                elif 'NASHVILLE' in loc_up: new_st = 'TN'
                elif 'DETROIT' in loc_up: new_st = 'MI'
                elif 'OKLAHOMA CITY' in loc_up: new_st = 'OK'
                elif 'PORTLAND' in loc_up: new_st = 'OR'
                elif 'LAS VEGAS' in loc_up: new_st = 'NV'
                elif 'MEMPHIS' in loc_up: new_st = 'TN'
                elif 'LOUISVILLE' in loc_up: new_st = 'KY'
                elif 'BALTIMORE' in loc_up: new_st = 'MD'
                elif 'MILWAUKEE' in loc_up: new_st = 'WI'
                elif 'ALBUQUERQUE' in loc_up: new_st = 'NM'
                elif 'TUCSON' in loc_up: new_st = 'AZ'
                elif 'FRESNO' in loc_up: new_st = 'CA'
                elif 'MESA' in loc_up: new_st = 'AZ'
                elif 'SACRAMENTO' in loc_up: new_st = 'CA'
                elif 'ATLANTA' in loc_up: new_st = 'GA'
                elif 'KANSAS CITY' in loc_up: new_st = 'MO'
                elif 'COLORADO SPRINGS' in loc_up: new_st = 'CO'
                elif 'MIAMI' in loc_up: new_st = 'FL'
                elif 'RALEIGH' in loc_up: new_st = 'NC'
                elif 'OMAHA' in loc_up: new_st = 'NE'
                elif 'LONG BEACH' in loc_up: new_st = 'CA'
                elif 'VIRGINIA BEACH' in loc_up: new_st = 'VA'

            if new_st:
                updates.append({'r_id': r_id, 'st': new_st})
                salvaged += 1

        if updates:
            db.execute(
                text("UPDATE recruiters SET state = :st WHERE recruiter_id = :r_id"),
                updates
            )
            db.commit()

        elapsed = round(time.time() - start_time, 2)
        print(f"Phone/City Salvage Migration Complete in {elapsed} seconds!")
        print(f"Total Salvaged: {salvaged}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    salvage_states()
