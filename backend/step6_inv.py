import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace
import random

db = SessionLocal()
args = SimpleNamespace(
    dry_run=True, apply=False, minimum_confidence=70, 
    batch_size=500, max_updates=500, all_recruiters=True
)
worker = EnrichmentWorker(db, args)

all_companies = db.query(Company).all()
human_company_ids = set()
for c in all_companies:
    co = c.company_name or ""
    if co and ' ' in co and worker.is_human_name(co, ''):
        human_company_ids.add(c.company_id)

swapped_recruiters = db.query(Recruiter).filter(Recruiter.company_id.in_(human_company_ids)).all()

safely_fixable = []
ambiguous = []

for r in swapped_recruiters:
    name_field = r.recruiter_name or ""
    if not worker.is_human_name(name_field, "") or any(w in name_field.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting']):
        safely_fixable.append(r)
    else:
        ambiguous.append(r)

random.seed(42)
sample_15 = random.sample(safely_fixable, min(15, len(safely_fixable)))

print("=== 15 CONCRETE EXAMPLES OF SAFELY FIXABLE SWAPS ===")
for i, r in enumerate(sample_15):
    co = r.company.company_name if r.company else ""
    print(f"{i+1}. RecruiterNameField: '{r.recruiter_name}' | CompanyNameField: '{co}' | Email: '{r.email}' | Source: '{r.data_source}' | CreatedAt: '{r.created_at}'")

has_raw = 0
has_linkedin = 0
unrecoverable = 0

for r in ambiguous:
    raw = r.raw_data or r.metadata_json or ""
    li = r.linkedin or ""
    
    if raw and str(raw).strip() not in ["{}", "None", ""]:
        has_raw += 1
    elif li and str(li).strip() not in ["None", ""]:
        has_linkedin += 1
    else:
        unrecoverable += 1

print("\n=== AMBIGUOUS BUCKET SUB-BREAKDOWN (Total:", len(ambiguous), ") ===")
print(f"1. Preserved raw_data / original row available: {has_raw}")
print(f"2. LinkedIn URL independent verification available: {has_linkedin}")
print(f"3. Completely unrecoverable (no raw, no linkedin): {unrecoverable}")

