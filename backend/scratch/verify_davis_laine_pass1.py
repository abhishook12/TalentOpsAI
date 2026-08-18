import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def run_pass1():
    print("=" * 80, flush=True)
    print("CHECK 1 (PASS 1): POSTGRESQL DATABASE FORENSIC VERIFICATION", flush=True)
    print("=" * 80, flush=True)
    
    db = SessionLocal()
    comp = db.query(Company).filter(Company.website.ilike("%davislaine.com%")).first()
    assert comp is not None, "Davis Laine, LLC company not found in DB!"
    print(f"[1.1] Company Verified: {comp.company_name} (ID: {comp.company_id}, Website: {comp.website}, HQ: {comp.location})", flush=True)
    
    recs = db.query(Recruiter).filter(Recruiter.company_id == comp.company_id).all()
    print(f"[1.2] Total Recruiter Profiles in DB for Davis Laine: {len(recs)}", flush=True)
    assert len(recs) == 10, f"Expected 10 records in DB, found {len(recs)}"
    
    for r in recs:
        print(f"      - ID {r.recruiter_id}: {r.recruiter_name} | <{r.email}> | Phone: {r.phone or 'N/A'} | Status: {r.email_status} | Conf: {r.email_confidence}%", flush=True)
        assert r.email_status == "verified"
        assert r.email_confidence == 95
        
    db.close()
    print("\n" + "=" * 80, flush=True)
    print("CHECK 1 (PASS 1) RESULT: ALL 10 RECORDS 100% VERIFIED IN POSTGRESQL DATABASE!", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_pass1()
