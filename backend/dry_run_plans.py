import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace
import random
import re

db = SessionLocal()
args = SimpleNamespace(
    dry_run=True, apply=False, minimum_confidence=70, 
    batch_size=500, max_updates=500, all_recruiters=True
)
worker = EnrichmentWorker(db, args)

all_companies = db.query(Company).all()
human_company_ids = set()
company_map = {}
for c in all_companies:
    company_map[c.company_id] = c
    co = c.company_name or ""
    if co and ' ' in co and worker.is_human_name(co, ''):
        human_company_ids.add(c.company_id)

swapped_recruiters = db.query(Recruiter).filter(Recruiter.company_id.in_(human_company_ids)).all()

plan_a_candidates = []
plan_b_count = 0

for r in swapped_recruiters:
    rec_name = r.recruiter_name or ""
    co_name = company_map[r.company_id].company_name if r.company_id in company_map else ""
    em = r.email or ""
    
    is_plan_a = ('@' in rec_name or '.com' in rec_name.lower() or any(w in rec_name.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting']))
    
    if is_plan_a or not worker.is_human_name(rec_name, ""):
        if is_plan_a:
            plan_a_candidates.append(r)
        else:
            raw = r.raw_data or r.metadata_json or ""
            li = r.linkedin or ""
            is_synth = ("@missing.local" in em or "@invalid.local" in em or "@example.com" in em)
            
            if (not raw or str(raw).strip() in ["{}", "None", ""]) and (not li or str(li).strip() in ["None", ""]) and is_synth:
                plan_b_count += 1

print(f"=== 1. CORRECTED PLAN B COUNT (Original Definition) ===")
print(f"Actual resulting count: {plan_b_count}")

print(f"\n=== 2. PLAN A DRY RUN (30 Sample Records) ===")
random.seed(123)
sample_30 = random.sample(plan_a_candidates, min(30, len(plan_a_candidates)))

# Build company name lookup
co_name_to_id = {c.company_name.lower(): c.company_id for c in all_companies if c.company_name}

for i, rec in enumerate(sample_30):
    primary_email_string = rec.recruiter_name.split(';')[0].strip()
    misplaced_human_name = company_map[rec.company_id].company_name if rec.company_id in company_map else ""
    
    final_co_id = None
    final_co_name = "Unknown"
    final_email_to_write = None
    outcome_status = "READY_TO_APPLY"
    
    if "@" in primary_email_string:
        parts = primary_email_string.split('@')
        if len(parts) == 2:
            domain_part = parts[1].lower()
            clean_domain = re.sub(r"\.?(com|net|org|tech|io)$", "", domain_part)
            reconstructed_co_name = clean_domain.replace('-', ' ').title()
            
            matched_id = co_name_to_id.get(reconstructed_co_name.lower())
            if matched_id:
                final_co_id = matched_id
                final_co_name = company_map[matched_id].company_name
            else:
                final_co_id = None
                final_co_name = reconstructed_co_name
            
            # Check dup
            if final_co_id:
                dup = db.query(Recruiter).filter(Recruiter.company_id == final_co_id, Recruiter.recruiter_name.ilike(misplaced_human_name), Recruiter.recruiter_id != rec.recruiter_id).first()
                if dup:
                    outcome_status = "REPAIR_BLOCKED_POSSIBLE_DUPLICATE"
            
            # Check email overwrite
            if rec.email and str(rec.email).strip() != "" and "@missing.local" not in rec.email and "@invalid.local" not in rec.email:
                final_email_to_write = rec.email
            else:
                sanitized = primary_email_string
                if "." not in domain_part and any(domain_part.endswith(t) for t in ['com', 'net', 'org']):
                    sanitized = parts[0] + "@" + domain_part[:-3] + "." + domain_part[-3:]
                final_email_to_write = sanitized
    else:
        final_co_name = rec.recruiter_name
        final_co_id = None
        final_email_to_write = rec.email if (rec.email and "@missing.local" not in rec.email) else None

    print(f"\nRecord #{i+1} (ID: {rec.recruiter_id}) | Outcome: {outcome_status}")
    print(f"  BEFORE: Name='{rec.recruiter_name}' | Co='{misplaced_human_name}' | Email='{rec.email}'")
    print(f"  AFTER : Name='{misplaced_human_name}' | Co='{final_co_name}' | Email='{final_email_to_write}'")

