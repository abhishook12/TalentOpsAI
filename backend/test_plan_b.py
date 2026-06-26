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

count_plan_b = 0

for r in swapped_recruiters:
    name_field = r.recruiter_name or ""
    # Plan A items are fixable (email in name field or buzzwords).
    # Plan B cohort: recruiter_name does NOT pass is_human_name AND NOT fixable?
    # Wait, let's look at user definition:
    # "company_name field contains a plausible human name (is_human_name passes) AND recruiter_name does NOT pass is_human_name AND no raw_data/metadata_json exists AND no linkedin URL exists AND email is a synthetic placeholder"
    
    # Wait! If recruiter_name is 'Bdecicco@Truedconsultingcom', it does NOT pass is_human_name! But that's Plan A!
    # How do we separate Plan A vs Plan B?
    # Plan A: recruiter_name contains '@' OR '.com' (corrupted email string) OR corporate buzzwords.
    # Plan B: recruiter_name does NOT contain '@' and NOT corporate buzzwords? OR let's check:
    is_plan_a = ('@' in name_field or '.com' in name_field.lower() or any(w in name_field.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting']))
    
    raw = r.raw_data or r.metadata_json or ""
    li = r.linkedin or ""
    em = r.email or ""
    is_synth_email = ('@missing.local' in em or '@invalid.local' in em or '@example.com' in em)
    
    if not is_plan_a and not worker.is_human_name(name_field, ""):
        if not raw or str(raw).strip() in ["{}", "None", ""]:
            if not li or str(li).strip() in ["None", ""]:
                if is_synth_email:
                    count_plan_b += 1

print(f"Plan B exact count: {count_plan_b}")

