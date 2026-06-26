import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.sql import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def merge_recruiters(db: Session):
    print("\n--- Merging Duplicate Recruiters ---", flush=True)
    dup_groups = db.query(
        func.lower(Recruiter.recruiter_name),
        Recruiter.company_id
    ).filter(
        Recruiter.recruiter_name.isnot(None), 
        Recruiter.recruiter_name != "", 
        Recruiter.company_id.isnot(None)
    ).group_by(func.lower(Recruiter.recruiter_name), Recruiter.company_id).having(func.count(Recruiter.recruiter_id) > 1).all()

    total_merged = 0
    for name_lower, company_id in dup_groups:
        recruiters = db.query(Recruiter).filter(
            func.lower(Recruiter.recruiter_name) == name_lower,
            Recruiter.company_id == company_id
        ).order_by(Recruiter.created_at).all()
        
        if len(recruiters) <= 1:
            continue
            
        primary = recruiters[0]
        duplicates = recruiters[1:]
        
        for dup in duplicates:
            if not dup.is_active: continue
            
            if not primary.email and dup.email:
                primary.email = dup.email
            if not primary.phone and dup.phone:
                primary.phone = dup.phone
            if not primary.linkedin and dup.linkedin:
                primary.linkedin = dup.linkedin
            if not primary.specialization and dup.specialization:
                primary.specialization = dup.specialization
            
            dup.is_active = False
            dup.notes = f"(Merged into {primary.recruiter_id}) " + (dup.notes or "")
            if dup.email and "@missing.local" not in dup.email:
                dup.email = f"merged_dup_{dup.recruiter_id}@missing.local"
            total_merged += 1
            
        db.commit()
    print(f"Merged {total_merged} duplicate recruiters.", flush=True)

def clean_invalid_emails(db: Session):
    print("\n--- Cleaning Invalid Emails ---", flush=True)
    sql = text("""
        UPDATE recruiters 
        SET raw_email_value = email, 
            email = 'invalid_' || recruiter_id || '@missing.local',
            email_status = 'unknown',
            email_confidence = 0,
            repair_reason = 'Removed structurally invalid email'
        WHERE email IS NOT NULL AND email NOT LIKE '%@missing.local' AND (email NOT LIKE '%@%' OR email LIKE '% %' OR email LIKE '%..%' OR length(email) < 5);
    """)
    result = db.execute(sql)
    db.commit()
    print(f"Cleaned {result.rowcount} structurally invalid emails.", flush=True)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        merge_recruiters(db)
        clean_invalid_emails(db)
        print("\nCleanup Complete!", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        db.rollback()
    finally:
        db.close()
