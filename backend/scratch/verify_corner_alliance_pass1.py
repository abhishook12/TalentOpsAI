import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def run_pass1():
    print("=" * 80)
    print("CHECK 1 (PASS 1): POSTGRESQL DATABASE FORENSIC VERIFICATION")
    print("=" * 80)
    
    db = SessionLocal()
    comp = db.query(Company).filter(Company.website.ilike("%corneralliance.com%")).first()
    assert comp is not None, "Corner Alliance company not found in DB!"
    print(f"[1.1] Company Verified: {comp.company_name} (ID: {comp.company_id}, Website: {comp.website}, HQ: {comp.location})")
    
    recs = db.query(Recruiter).filter(Recruiter.company_id == comp.company_id).all()
    print(f"[1.2] Total Recruiter Profiles in DB for Corner Alliance: {len(recs)}")
    assert len(recs) == 14, f"Expected 14 records in DB, found {len(recs)}"
    
    for r in recs:
        print(f"      - ID {r.recruiter_id}: {r.recruiter_name} | <{r.email}> | Status: {r.email_status} | Conf: {r.email_confidence}%")
        assert r.email_status == "verified"
        assert r.email_confidence == 95
        
    db.close()
    print("\n" + "=" * 80)
    print("CHECK 1 (PASS 1) RESULT: ALL 14 RECORDS 100% VERIFIED IN POSTGRESQL DATABASE!")
    print("=" * 80)

if __name__ == "__main__":
    run_pass1()
