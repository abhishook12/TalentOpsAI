#!/usr/bin/env python
from __future__ import annotations

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def fix_company_states():
    start_time = time.time()
    print("Starting Alignment of Companies Directory States...")
    db = SessionLocal()
    
    try:
        # 1. Update company state from 2-letter exact location strings
        res1 = db.execute(text("""
            UPDATE companies
            SET state = UPPER(location)
            WHERE (state IS NULL OR state = '')
              AND LENGTH(location) = 2;
        """))
        
        # 2. Update company state from majority state of linked recruiters
        res2 = db.execute(text("""
            UPDATE companies c
            SET state = sub.top_state
            FROM (
                SELECT company_id, MODE() WITHIN GROUP (ORDER BY state) as top_state
                FROM recruiters
                WHERE state IS NOT NULL AND state != ''
                GROUP BY company_id
            ) sub
            WHERE c.company_id = sub.company_id
              AND (c.state IS NULL OR c.state = '');
        """))
        
        # 3. Standardize remaining blank company states to 'US'
        res3 = db.execute(text("""
            UPDATE companies
            SET state = 'US'
            WHERE state IS NULL OR state = '';
        """))
        
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"Companies Directory Alignment Complete in {elapsed}s!")
        print(f"   - From 2-letter locations: {res1.rowcount}")
        print(f"   - From Recruiter Majority: {res2.rowcount}")
        print(f"   - Standardized to 'US':    {res3.rowcount}")
        
    except Exception as e:
        db.rollback()
        print(f"Error fixing company states: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_company_states()
