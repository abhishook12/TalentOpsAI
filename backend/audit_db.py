import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy import func
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def run_audit(db: Session):
    print("=== Database Quality Audit ===")
    
    # 1. Total Counts
    total_recruiters = db.query(Recruiter).count()
    total_companies = db.query(Company).count()
    print(f"Total Recruiters: {total_recruiters}")
    print(f"Total Companies: {total_companies}")
    
    # 2. Duplicate Companies
    # Companies with the exact same normalized_company_name
    dup_companies = db.query(
        Company.normalized_company_name, 
        func.count(Company.company_id).label('c')
    ).group_by(Company.normalized_company_name).having(func.count(Company.company_id) > 1).all()
    print(f"\nCompanies with identical normalized names: {len(dup_companies)}")
    
    # 3. Duplicate Recruiters (by Email)
    dup_rec_emails = db.query(
        Recruiter.email,
        func.count(Recruiter.recruiter_id).label('c')
    ).filter(Recruiter.email.isnot(None), Recruiter.email != "").group_by(Recruiter.email).having(func.count(Recruiter.recruiter_id) > 1).all()
    print(f"Recruiters sharing identical emails: {len(dup_rec_emails)}")
    
    # 4. Duplicate Recruiters (by Name + Company)
    dup_rec_names = db.query(
        func.lower(Recruiter.recruiter_name),
        Recruiter.company_id,
        func.count(Recruiter.recruiter_id).label('c')
    ).filter(Recruiter.recruiter_name.isnot(None), Recruiter.recruiter_name != "", Recruiter.company_id.isnot(None)).group_by(func.lower(Recruiter.recruiter_name), Recruiter.company_id).having(func.count(Recruiter.recruiter_id) > 1).all()
    print(f"Recruiters sharing identical Name + Company: {len(dup_rec_names)}")
    
    # 5. Invalid Emails
    # Emails that don't match basic format
    all_emails = db.query(Recruiter.recruiter_id, Recruiter.email).filter(Recruiter.email.isnot(None)).all()
    invalid_emails = [r for r in all_emails if r.email and ('@' not in r.email or ' ' in r.email or '..' in r.email)]
    print(f"\nStructurally invalid emails (missing @, spaces, etc): {len(invalid_emails)}")
    
    # 6. Invalid States
    invalid_states = db.query(Recruiter).filter(func.length(Recruiter.state) > 2).count()
    print(f"Recruiters with invalid state (length > 2): {invalid_states}")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        run_audit(db)
    finally:
        db.close()
