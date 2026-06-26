import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter
from enrich_recruiter_contacts import EnrichmentWorker, generate_email
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

sample = db.query(Recruiter).filter(
    or_(
        Recruiter.email == None,
        Recruiter.email == '',
        Recruiter.email_status != 'verified'
    )
).order_by(Recruiter.recruiter_id.desc()).limit(500).all()

names_13 = [
    'Jon Gaddis', 'James Anthony', 'Tami Staley', 'Mohammed Shkh', 
    'Syed Umar Ali', 'Ben Carlin', 'Megan Reed', 'Daniel Rivas', 
    'Freddy Engel', 'Kyle Stock', 'Haley Mcgurk', 'Tyler Zarbo', 'Karsen Pierce'
]

print('=== 1. THE 13 MISMATCH RECORDS ===')
for r in sample:
    if r.recruiter_name in names_13:
        company = r.company
        fn, ln = worker.extract_names(r.recruiter_name, r.email)
        pat = worker.detect_company_patterns(company) if company else None
        conf = pat['confidence'] if pat else 0
        cand = generate_email(fn, ln, pat['pattern'], pat['domain']) if pat else 'None'
        outcome = worker.process_recruiter(r)
        print(f'Name: {r.recruiter_name} | Old: {r.email} | Gen: {cand} | Conf: {conf}% | Status: {outcome}')

print('\n=== 2. EXACT COLUMN SWAP COUNT ===')
swapped_count = 0
for r in sample:
    outcome = worker.process_recruiter(r)
    if outcome == 'SKIPPED_INVALID_NON_PERSON_NAME':
        co = r.company.company_name if r.company else ''
        if co and worker.is_human_name(co, '') and ' ' in co:
            swapped_count += 1
print(f'Exact integer: {swapped_count}')

print('\n=== 3. ALL 20 AUDIT RECORDS VERBATIM ===')
no_pat = []
inv_name = []
for r in sample:
    outcome = worker.process_recruiter(r)
    co = r.company.company_name if r.company else ''
    if outcome == 'SKIPPED_NO_VERIFIED_PATTERN':
        no_pat.append((r.recruiter_name, co, r.email, outcome))
    elif outcome == 'SKIPPED_INVALID_NON_PERSON_NAME':
        inv_name.append((r.recruiter_name, co, r.email, outcome))

random.seed(99)
s_no_pat = random.sample(no_pat, min(10, len(no_pat)))
s_inv = random.sample(inv_name, min(10, len(inv_name)))

for i, x in enumerate(s_no_pat + s_inv):
    print(f'{i+1}. Name: {x[0]} | Co: {x[1]} | OldEmail: {x[2]} | Status: {x[3]}')

