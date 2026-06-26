#!/usr/bin/env python
"""Personal Alternate Email Hoisting Engine - TalentOpsAI"""
import sys, os, time, re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def hoist_emails():
    start_time = time.time()
    print("STARTING PERSONAL ALTERNATE EMAIL HOISTING...")
    db = SessionLocal()
    try:
        # If email2 is blank but alternate_emails has an email, hoist first email from alternate_emails to email2
        res1 = db.execute(text("""
            UPDATE recruiters
            SET email2 = TRIM(SPLIT_PART(alternate_emails, ',', 1))
            WHERE (email2 IS NULL OR email2 = '')
              AND alternate_emails IS NOT NULL 
              AND alternate_emails LIKE '%@%.%'
              AND TRIM(SPLIT_PART(alternate_emails, ',', 1)) NOT LIKE '%@missing.local%';
        """))
        print(f"   -> Hoisted {res1.rowcount} secondary personal emails into dedicated email2 field.")

        # If primary email is @missing.local but email2 is a valid real email, promote email2 to primary email
        res2 = db.execute(text("""
            UPDATE recruiters
            SET email = email2,
                email_status = 'verified_hoisted_from_alt'
            WHERE email LIKE '%@missing.local%'
              AND email2 IS NOT NULL 
              AND email2 LIKE '%@%.%'
              AND email2 NOT LIKE '%@missing.local%'
              AND NOT EXISTS (SELECT 1 FROM recruiters r2 WHERE r2.email = recruiters.email2);
        """))
        print(f"   -> Promoted {res2.rowcount} secondary emails to replace missing primary emails.")

        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"\nPersonal Alternate Email Hoisting Complete in {elapsed}s!")
    except Exception as e:
        db.rollback()
        print(f"Email hoisting error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    hoist_emails()
