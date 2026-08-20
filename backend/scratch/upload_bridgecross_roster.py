import sys
import os
import duckdb
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.services.parquet_writer import ParquetWriter
from app.services.recruiter_store import recruiter_store, PARQUET_FILE

contacts_data = [
    {"name": "Danny Collins", "position": "Managing Partner/Director of Programs", "email": "dcollins@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Executive"},
    {"name": "Natia Mgebrishvili", "position": "HR Operations Specialist", "email": "nmgebrishvili@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Suman B.", "position": "Software Engineer", "email": "sb@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Riley Devaul", "position": "Summer Intern", "email": "rdevaul@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Campus"},
    {"name": "Sankar Subramanian", "position": "SAPBI Consultant", "email": "ssubramanian@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Margie Collins", "position": "SAP Cyber BASIS Administrator", "email": "mcollins@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Calvin Hsu", "position": "Full Stack Software Engineer", "email": "chsu@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Kelly T.", "position": "Social Media Coordinator", "email": "kt@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Bryan Pham", "position": "Security Professional", "email": "bpham@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Barbara Lanza", "position": "Office Manager", "email": "blanza@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
    {"name": "Matt Starr", "position": "Software Engineer V/Agile Coach", "email": "mstarr@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Lead"},
    {"name": "Jagadesh Yellapu", "position": "Data Analytics Leader", "email": "jyellapu@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Lead"},
    {"name": "Petros Melake", "position": "Senior Full Stack Engineer", "email": "pmelake@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Senior"},
    {"name": "Dan Roever", "position": "Infrastructure & Security Operations Leader", "email": "droever@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Lead"},
    {"name": "Olivia Cruz-Martinez", "position": "Cybersecurity Compliance Technician", "email": "ocruz-martinez@bridgecrossllc.com", "company": "BridgeCross, LLC", "seniority": "Specialist"},
]

db = SessionLocal()

# 1. Ensure BridgeCross, LLC company exists in PostgreSQL
comp = db.query(Company).filter(
    (Company.company_name.ilike("%bridgecross%")) | 
    (Company.website.ilike("%bridgecrossllc%")) |
    (Company.email_pattern.ilike("%bridgecrossllc%"))
).first()

if not comp:
    print("Creating new Company record for BridgeCross, LLC in PostgreSQL...")
    comp = Company(
        company_name="BridgeCross, LLC",
        canonical_name="BridgeCross, LLC",
        website="https://bridgecrossllc.com",
        email_pattern="bridgecrossllc.com",
        location="United States",
        industry="Staffing & Consulting",
        notes="Imported BridgeCross, LLC roster"
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    print(f"Created Company with ID: {comp.company_id}")
else:
    print(f"Found existing Company: ID {comp.company_id} - {comp.company_name}")

company_id_val = comp.company_id

# 2. Get current max recruiter_id
con = duckdb.connect()
max_rec_id = con.execute(f"SELECT COALESCE(MAX(TRY_CAST(recruiter_id AS BIGINT)), 2633583) FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')").fetchone()[0]
con.close()

parquet_records = []
now_str = datetime.now(timezone.utc).isoformat()

for i, c in enumerate(contacts_data, start=1):
    current_id = max_rec_id + i
    email = c["email"].strip().lower()
    
    # Check if recruiter already exists in PostgreSQL
    pg_rec = db.query(Recruiter).filter(Recruiter.email == email).first()
    if not pg_rec:
        pg_rec = Recruiter(
            recruiter_id=current_id,
            recruiter_name=c["name"],
            email=email,
            company_id=company_id_val,
            specialization=c["position"],
            location="United States",
            state="US",
            is_active=True,
            needs_review=False,
            completeness_score=95,
            quality_score=95,
            notes=f"Position: {c['position']}",
            created_at=datetime.now(timezone.utc)
        )
        db.add(pg_rec)
    
    parquet_records.append({
        "recruiter_id": current_id,
        "recruiter_name": c["name"],
        "normalized_recruiter_name": c["name"].lower(),
        "email": email,
        "phone": None,
        "email2": None,
        "phone2": None,
        "email3": None,
        "phone3": None,
        "email4": None,
        "phone4": None,
        "alternate_emails": None,
        "alternate_phones": None,
        "linkedin": None,
        "specialization": c["position"],
        "notes": f"Position: {c['position']}",
        "quality_score": 95,
        "company_id": str(company_id_val),
        "location": "United States",
        "state": "US",
        "is_active": True,
        "needs_review": False,
        "completeness_score": 95,
        "location_confidence": "HIGH",
        "state_source": "AUTO",
        "created_at": now_str,
        "relevance_score": 100,
        "seniority_level": c["seniority"],
        "timezone": "America/New_York",
        "timezone_code": "ET",
        "company_scale": "Boutique",
        "is_deliverable": True,
        "email_status": "verified",
        "email_source": "USER_UPLOAD",
        "email_confidence": 100,
    })

db.commit()
db.close()
print(f"Persisted PostgreSQL records for {len(contacts_data)} contacts.")

# 3. Append records to recruiters_full.parquet
pw = ParquetWriter()
count = pw.append_records(parquet_records)
print(f"Successfully appended {count} records to Parquet dataset.")

# 4. Reload recruiter store
recruiter_store.reload()
print("Recruiter store successfully reloaded in memory.")
