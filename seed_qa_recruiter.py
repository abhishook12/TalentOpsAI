import os
import sys

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

sys.path.insert(0, './backend')
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def seed():
    db = SessionLocal()
    try:
        # Check company
        company = db.query(Company).filter(Company.company_name == "QA Testing Inc").first()
        if not company:
            company = Company(company_name="QA Testing Inc", website="https://qatesting.inc")
            db.add(company)
            db.commit()
            db.refresh(company)
            
        # Check recruiter
        email = "qa_enrichment@example.com"
        recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
        if not recruiter:
            recruiter = Recruiter(
                email=email,
                recruiter_name="QA Tester",
                company_id=company.company_id,
                title="Lead QA",
                location="San Francisco, CA"
            )
            db.add(recruiter)
            db.commit()
            print(f"Seeded {email}")
        else:
            recruiter.company_id = company.company_id
            recruiter.recruiter_name = "QA Tester"
            db.commit()
            print(f"Updated {email}")
            
    finally:
        db.close()

if __name__ == "__main__":
    seed()
