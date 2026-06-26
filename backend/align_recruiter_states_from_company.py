#!/usr/bin/env python
"""Align Recruiter States from Company HQ - TalentOpsAI"""
import sys, os, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def align_states():
    start_time = time.time()
    print("STARTING RECRUITER STATE DERIVATION FROM COMPANY HQ...")
    db = SessionLocal()
    try:
        res = db.execute(text("""
            UPDATE recruiters r
            SET state = c.state,
                state_source = 'derived_from_company_hq'
            FROM companies c
            WHERE r.company_id = c.company_id
              AND (r.state IS NULL OR r.state = '' OR r.state = 'Unknown' OR r.state = 'US')
              AND c.state IS NOT NULL 
              AND c.state != '' 
              AND c.state != 'US'
              AND LENGTH(c.state) = 2;
        """))
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"Derived exact 2-letter US State codes for {res.rowcount} recruiters in {elapsed}s!")
    except Exception as e:
        db.rollback()
        print(f"State derivation error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    align_states()
