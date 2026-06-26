import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace
from sqlalchemy import or_, not_, func

db = SessionLocal()
args = SimpleNamespace(
    dry_run=True, apply=False, minimum_confidence=70, 
    batch_size=500, max_updates=500, all_recruiters=True,
    start_after_id=None, company=None, resume_run_id=None,
    apply_pending=False, retry_failed=False
)
worker = EnrichmentWorker(db, args)
worker.run_id = 'investigate'

sample = db.query(Recruiter).filter(
    or_(
        Recruiter.email == None,
        Recruiter.email == '',
        Recruiter.email_status != 'verified'
    )
).order_by(Recruiter.recruiter_id.desc()).limit(500).all()

swapped = []
for r in sample:
    outcome = worker.process_recruiter(r)
    if outcome == "SKIPPED_INVALID_NON_PERSON_NAME":
        company_name = r.company.company_name if r.company else ""
        # Check if the company field looks like a human name.
        if company_name and worker.is_human_name(company_name, ""):
            # wait, what if the company is just a single word?
            # human names usually have space. Let's add that check.
            if ' ' in company_name:
                swapped.append({
                    "recruiter_id": r.recruiter_id,
                    "name_field": r.recruiter_name,
                    "company_field": company_name,
                    "email": r.email,
                    "source": getattr(r, 'source', 'Unknown')
                })

db.rollback()

print(f"Total swapped detected: {len(swapped)}")
for i, s in enumerate(swapped[:10]):
    print(f"{i+1}. ID: {s['recruiter_id']} | NameField: {s['name_field']} | CoField: {s['company_field']} | Source: {s['source']} | Email: {s['email']}")

