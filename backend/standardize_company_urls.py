#!/usr/bin/env python
"""Standardize Company URLs Engine - TalentOpsAI"""
import sys, os, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def clean_urls():
    start_time = time.time()
    print("STARTING COMPANY WEBSITE PROTOCOL STANDARDIZATION...")
    db = SessionLocal()
    try:
        # Prepend https:// if missing protocol
        res = db.execute(text("""
            UPDATE companies
            SET website = 'https://' || website
            WHERE website IS NOT NULL 
              AND website != ''
              AND website NOT LIKE 'http://%'
              AND website NOT LIKE 'https://%';
        """))
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"Standardized {res.rowcount} company website URLs in {elapsed}s!")
    except Exception as e:
        db.rollback()
        print(f"URL cleanup error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_urls()
