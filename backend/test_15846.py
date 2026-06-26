import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace

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

count_15846 = 0

for r in swapped_recruiters:
    name_field = r.recruiter_name or ""
    is_plan_a = ('@' in name_field or '.com' in name_field.lower() or any(w in name_field.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting']))
    
    # If it was NOT in Plan A (meaning it went to ambiguous bucket)
    if not is_plan_a and worker.is_human_name(name_field, ""): # Wait, in step6_inv.py we did: if not worker.is_human_name(name_field) or buzzwords -> fixable. ELSE -> ambiguous.
        raw = r.raw_data or r.metadata_json or ""
        li = r.linkedin or ""
        em = r.email or ""
        is_synth = ('@missing.local' in em or '@invalid.local' in em or '@example.com' in em)
        
        if not raw or str(raw).strip() in ["{}", "None", ""]:
            if not li or str(li).strip() in ["None", ""]:
                # Wait, earlier unrecoverable was 15846 out of all ambiguous (regardless of email synth check? Let's check!)
                count_15846 += 1

print(f"Exact count matching 15846 cohort: {count_15846}")

