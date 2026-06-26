import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace
from sqlalchemy import or_
import random

db = SessionLocal()
args = SimpleNamespace(
    dry_run=True, apply=False, minimum_confidence=70, 
    batch_size=500, max_updates=500, all_recruiters=True,
    start_after_id=None, company=None, resume_run_id=None,
    apply_pending=False, retry_failed=False
)
worker = EnrichmentWorker(db, args)
worker.run_id = 'audit'

sample = db.query(Recruiter).filter(
    or_(
        Recruiter.email == None,
        Recruiter.email == '',
        Recruiter.email_status != 'verified'
    )
).order_by(Recruiter.recruiter_id.desc()).limit(500).all()

no_pattern = []
invalid_name = []

for r in sample:
    outcome = worker.process_recruiter(r)
    company_name = r.company.company_name if r.company else ""
    if outcome == "SKIPPED_NO_VERIFIED_PATTERN":
        no_pattern.append({"name": r.recruiter_name, "company": company_name})
    elif outcome == "SKIPPED_INVALID_NON_PERSON_NAME":
        invalid_name.append({"name": r.recruiter_name, "company": company_name})

random.seed(99) # different seed from before
sampled_no_pattern = random.sample(no_pattern, min(10, len(no_pattern)))
sampled_invalid = random.sample(invalid_name, min(10, len(invalid_name)))

print("=== SKIPPED_NO_VERIFIED_PATTERN ===")
for x in sampled_no_pattern:
    print(f"Name: {x['name']} | Co: {x['company']}")

print("\n=== SKIPPED_INVALID_NON_PERSON_NAME ===")
for x in sampled_invalid:
    print(f"Name: {x['name']} | Co: {x['company']}")

