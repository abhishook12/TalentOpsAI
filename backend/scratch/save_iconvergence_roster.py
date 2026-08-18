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
    {"name": "Matthew Gardebled", "position": "Assistant Account Manager", "email": "matthewg@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "Michael Tromblay", "position": "Systems Engineer", "email": "michael@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "Ramsha Khan", "position": "BDM", "email": "ramsha@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "Brandon Angelle", "position": "Service and Support Technician", "email": "brandon@iconvergence.com", "company": "iConvergence", "seniority": "Junior"},
    {"name": "Indira Dhingra", "position": "President, Technology Executive", "email": "indira@iconvergence.com", "company": "iConvergence", "seniority": "Executive"},
    {"name": "Scott Louviere", "position": "Senior Account Manager", "email": "scott@iconvergence.com", "company": "iConvergence", "seniority": "Senior"},
    {"name": "Scotty Barron", "position": "Security Solutions Engineer", "email": "scotty@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Pankaj Dhingra", "position": "Chief AI & Technology Transformation Executive", "email": "pankaj@iconvergence.com", "company": "iConvergence", "seniority": "Executive"},
    {"name": "Chris Abbott", "position": "Data Center Engineer", "email": "chris@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Courtney Pellegrin", "position": "Customer Success Manager", "email": "courtney@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "Kathy Harris", "position": "Accountant", "email": "kathy@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Connor Linde", "position": "Technical Staff", "email": "connor@iconvergence.com", "company": "iConvergence", "seniority": "Junior"},
    {"name": "Jonathon Monk", "position": "Director of Inside Sales", "email": "jonathon@iconvergence.com", "company": "iConvergence", "seniority": "Director"},
    {"name": "S C", "position": "Recruiter", "email": "sc@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Rachel Bott", "position": "Renewals Manager", "email": "rachel@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "Wesley Ducote", "position": "Sr Systems Engineer", "email": "wesley@iconvergence.com", "company": "iConvergence", "seniority": "Senior"},
    {"name": "Ashley Braus", "position": "Project Manager", "email": "ashley@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "Brock Guidry, CSM, CCST-IT Support", "position": "IT Professional", "email": "brock@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Adam Clause", "position": "DataCenter Engineer", "email": "adam@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Douglas Meaux", "position": "Technology Leader", "email": "douglas@iconvergence.com", "company": "iConvergence", "seniority": "Lead"},
    {"name": "Richard Maliden", "position": "Systems Engineer", "email": "richard@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "Amanda Russo", "position": "Marketing and Business Development", "email": "amanda@iconvergence.com", "company": "iConvergence", "seniority": "Mid"},
    {"name": "John Dymond", "position": "Senior Account Manager", "email": "john@iconvergence.com", "company": "iConvergence", "seniority": "Senior"},
    {"name": "Chama Chlieh", "position": "Responsable communications marketing", "email": "chama@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Jason Suarez", "position": "Network Engineer", "email": "jason@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Toby B.", "position": "IT Enterprise Architect", "email": "toby@iconvergence.com", "company": "iConvergence", "seniority": "Lead"},
    {"name": "Matt Creswell", "position": "WebEx, Meraki installation & support", "email": "matt@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Mike Kling", "position": "Technical Sales Support Specialist", "email": "mike@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Brannon Bourque", "position": "Technology", "email": "brannon@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
    {"name": "Beau Peyton", "position": "Executive Director, Emerging Markets", "email": "beau@iconvergence.com", "company": "iConvergence", "seniority": "Executive"},
    {"name": "Chad Wells", "position": "Owner at CAWCAM PRODUCTIONS", "email": "chad@iconvergence.com", "company": "iConvergence", "seniority": "Executive"},
    {"name": "Houda Zanibel", "position": "Commercial", "email": "houda@iconvergence.com", "company": "iConvergence", "seniority": "Specialist"},
]

def save_iconvergence_roster():
    print("=" * 80)
    print("INGESTING AND PERSISTING iConvergence ROSTER (32 CONTACTS)")
    print("=" * 80)

    db = SessionLocal()

    # 1. Ensure iConvergence Company exists in PostgreSQL
    comp = db.query(Company).filter(
        (Company.company_name.ilike("%iconvergence%")) | 
        (Company.primary_domain.ilike("%iconvergence.com%")) |
        (Company.website.ilike("%iconvergence.com%"))
    ).first()

    if not comp:
        print("[1] Creating new Company record for iConvergence in PostgreSQL...")
        comp = Company(
            company_name="iConvergence",
            canonical_name="iConvergence",
            normalized_company_name="iconvergence",
            website="https://iconvergence.com",
            primary_domain="iconvergence.com",
            email_pattern="iconvergence.com",
            location="Lafayette, LA",
            state="LA",
            industry="IT Services & Network Solutions",
            notes="Premier Cisco Gold Integrator and Enterprise IT Consulting",
            completeness_score=100,
            trust_score=100
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)
        print(f"    -> Created Company: ID {comp.company_id} - {comp.company_name}")
    else:
        print(f"[1] Found existing Company: ID {comp.company_id} - {comp.company_name}")
        comp.website = "https://iconvergence.com"
        comp.primary_domain = "iconvergence.com"
        comp.state = "LA"
        comp.location = "Lafayette, LA"
        db.commit()

    company_id_val = comp.company_id

    # 2. Get current max recruiter_id
    con = duckdb.connect()
    parquet_clean = PARQUET_FILE.replace(os.sep, '/')
    max_rec_id = con.execute(f"SELECT COALESCE(MAX(TRY_CAST(recruiter_id AS BIGINT)), 2633600) FROM read_parquet('{parquet_clean}')").fetchone()[0]
    
    # Check existing emails in parquet
    existing_emails_pq = set(con.execute(f"SELECT LOWER(email) FROM read_parquet('{parquet_clean}') WHERE email IS NOT NULL").df()['lower(email)'].tolist())
    con.close()

    parquet_records = []
    now_str = datetime.now(timezone.utc).isoformat()
    pg_created = 0
    pg_updated = 0

    print(f"\n[2] Processing {len(contacts_data)} contact profiles...")
    for i, c in enumerate(contacts_data, start=1):
        email = c["email"].strip().lower()
        current_id = max_rec_id + i
        
        # Check if exists in PostgreSQL
        pg_rec = db.query(Recruiter).filter(Recruiter.email == email).first()
        if not pg_rec:
            pg_rec = Recruiter(
                recruiter_id=current_id,
                recruiter_name=c["name"],
                normalized_recruiter_name=c["name"].lower(),
                email=email,
                company_id=company_id_val,
                title=c["position"],
                specialization=c["position"],
                location="Lafayette, LA",
                state="LA",
                normalized_city="Lafayette",
                is_active=True,
                needs_review=False,
                completeness_score=95,
                quality_score=95,
                notes=f"Position: {c['position']} | iConvergence Roster",
                created_at=datetime.now(timezone.utc),
                data_source="USER_ROSTER_UPLOAD"
            )
            db.add(pg_rec)
            pg_created += 1
        else:
            pg_rec.recruiter_name = c["name"]
            pg_rec.title = c["position"]
            pg_rec.company_id = company_id_val
            pg_rec.state = "LA"
            pg_rec.location = "Lafayette, LA"
            pg_rec.completeness_score = 95
            pg_rec.quality_score = 95
            pg_rec.is_active = True
            pg_updated += 1
        
        # If not in Parquet, prepare append record
        if email not in existing_emails_pq:
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
                "title": c["position"],
                "specialization": c["position"],
                "notes": f"Position: {c['position']} | iConvergence Roster",
                "quality_score": 95,
                "company_id": str(company_id_val),
                "location": "Lafayette, LA",
                "state": "LA",
                "normalized_city": "Lafayette",
                "is_active": True,
                "needs_review": False,
                "completeness_score": 95,
                "location_confidence": "HIGH",
                "state_source": "AUTO",
                "created_at": now_str,
                "relevance_score": 100,
                "seniority_level": c["seniority"],
                "timezone": "America/Chicago",
                "timezone_code": "CT",
                "company_scale": "Enterprise IT Provider",
                "is_deliverable": True,
                "email_status": "business_valid",
                "email_source": "USER_UPLOAD",
                "email_confidence": 100,
            })

    db.commit()
    db.close()
    print(f"    -> PostgreSQL sync complete: {pg_created} created, {pg_updated} updated.")

    # 3. Append to Parquet dataset
    if parquet_records:
        print(f"\n[3] Appending {len(parquet_records)} records to Parquet dataset ({PARQUET_FILE})...")
        pw = ParquetWriter()
        appended_cnt = pw.append_records(parquet_records)
        print(f"    -> Successfully appended {appended_cnt} records to Parquet store!")
    else:
        print("\n[3] All records already present in Parquet.")

    # 4. Force reload recruiter store
    print("\n[4] Reloading Unified RecruiterStore query engine...")
    recruiter_store.reload()
    print("    -> RecruiterStore reloaded.")

    print("\n" + "=" * 80)
    print("iConvergence ROSTER INGESTION COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    save_iconvergence_roster()
