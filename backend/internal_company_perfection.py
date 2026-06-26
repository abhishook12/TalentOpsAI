#!/usr/bin/env python
"""Deterministic Internal Company Industry Normalization Engine - TalentOpsAI"""
import sys, os, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def run_company_perfection():
    start_time = time.time()
    print("STARTING DETERMINISTIC INTERNAL COMPANY INDUSTRY NORMALIZATION...")
    db = SessionLocal()
    try:
        r = db.execute(text("""
            UPDATE companies
            SET industry = CASE
                WHEN company_name ILIKE '%staffing%' OR company_name ILIKE '%recruiting%' OR company_name ILIKE '%talent%' OR company_name ILIKE '%search%' OR company_name ILIKE '%partners%' THEN 'Staffing & Recruiting'
                WHEN company_name ILIKE '%consulting%' OR company_name ILIKE '%advisors%' OR company_name ILIKE '%group%' THEN 'Management Consulting'
                WHEN company_name ILIKE '%tech%' OR company_name ILIKE '%software%' OR company_name ILIKE '%systems%' OR company_name ILIKE '%cloud%' OR company_name ILIKE '%ai%' THEN 'Information Technology & Software'
                WHEN company_name ILIKE '%health%' OR company_name ILIKE '%medical%' OR company_name ILIKE '%pharma%' OR company_name ILIKE '%bio%' THEN 'Healthcare & Life Sciences'
                WHEN company_name ILIKE '%finance%' OR company_name ILIKE '%capital%' OR company_name ILIKE '%invest%' OR company_name ILIKE '%bank%' THEN 'Financial Services'
                ELSE COALESCE(industry, 'Corporate Services & Enterprise')
            END
            WHERE industry IS NULL OR industry = '' OR industry = 'Unknown' OR industry ILIKE '%generic%';
        """))
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"Normalised industry classifications for {r.rowcount} parent corporate groups in {elapsed}s!")
    except Exception as e:
        db.rollback()
        print(f"Company normalization error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_company_perfection()
