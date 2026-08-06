import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, DomainIntelligence
from sentinel_worker import process_batch

def check_db(check_num):
    db = SessionLocal()
    try:
        completed = db.query(Recruiter).filter(Recruiter.sentinel_status == 'Completed').count()
        pending = db.query(Recruiter).filter(Recruiter.sentinel_status == 'Pending').count()
        with_company = db.query(Recruiter).filter(Recruiter.company_id.isnot(None)).count()
        domains = db.query(DomainIntelligence).count()
        
        example = db.query(Recruiter).filter(
            Recruiter.sentinel_status == 'Completed', 
            Recruiter.company_confidence > 0
        ).first()
        
        example_data = "None"
        if example:
            example_data = f"{example.recruiter_name} | {example.email} | CompanyID: {example.company_id} | Confidence: {example.company_confidence}% | Score: {example.completeness_score}%"

        result = (
            f"--- Check {check_num} ---\n"
            f"Completed: {completed}, Pending: {pending}\n"
            f"Recruiters with Company: {with_company}\n"
            f"Domains Mapped: {domains}\n"
            f"Example Enrichment: {example_data}\n"
        )
        return result
    finally:
        db.close()

if __name__ == "__main__":
    with open("sentinel_proof.txt", "w") as f:
        f.write("Sentinel Phase II - 3 Times Check Proof\n=========================================\n\n")
        
    for i in range(1, 4):
        print(f"Processing batch {i}...")
        processed = process_batch(batch_size=50)
        print(f"Processed {processed} profiles.")
        
        output = check_db(i)
        print(output)
        with open("sentinel_proof.txt", "a") as f:
            f.write(output + "\n")
