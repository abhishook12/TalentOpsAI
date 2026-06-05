import os
import json
from dotenv import load_dotenv
from backend.app.database import SessionLocal
from backend.app.models.models import SmartImportJob, SmartImportRow, Recruiter

load_dotenv("backend/.env")
db = SessionLocal()

job_id = "38f88277-0968-4b47-8efa-1aaea6fc2377"

try:
    rows = db.query(SmartImportRow).filter(SmartImportRow.job_id == job_id).all()
    print(f"Loaded {len(rows)} rows into memory")
    
    emails_to_check = set()
    for i, r in enumerate(rows):
        if i % 1000 == 0:
            print(f"Parsed {i} rows")
        raw = json.loads(r.raw_json)
        e = str(raw.get("myurukov@rmcintservices.com", "")).strip().lower()
        if e: emails_to_check.add(e)
    
    print(f"Got {len(emails_to_check)} emails to check")
    
    print("Executing Email DB query...")
    existing = db.query(Recruiter).filter(Recruiter.email.in_(emails_to_check)).all()
    print(f"Got {len(existing)} existing recruiters by email")

    phones_to_check = set(["555-1234", "555-5678"])
    print("Executing Phone DB query...")
    existing_by_phone = db.query(Recruiter).filter(Recruiter.phone.in_(phones_to_check)).all()
    print(f"Got {len(existing_by_phone)} existing recruiters by phone")
    
    from backend.app.models.models import Company
    names_to_check = set(["Michael Yurukov", "John Doe"])
    print("Executing Name DB query...")
    matching_names = db.query(Recruiter).outerjoin(Company, Recruiter.company_id == Company.company_id).filter(Recruiter.recruiter_name.in_(names_to_check)).all()
    print(f"Got {len(matching_names)} existing recruiters by name")
    
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"CRASH: {e}")
