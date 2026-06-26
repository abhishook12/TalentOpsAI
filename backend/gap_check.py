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
company_map = {c.company_id: c for c in all_companies}
for c in all_companies:
    co = c.company_name or ""
    if co and ' ' in co and worker.is_human_name(co, ''):
        human_company_ids.add(c.company_id)

swapped_recruiters = db.query(Recruiter).filter(Recruiter.company_id.in_(human_company_ids)).all()

plan_a_count = 0
personal_domain_count = 0
free_domains = ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol', 'protonmail']

plan_a_records = []

for r in swapped_recruiters:
    rec_name = r.recruiter_name or ""
    # Check if rec_name contains '@' or looks like an email/buzzword
    is_email_like = ('@' in rec_name or any(rec_name.lower().endswith(t) for t in ['com', 'net', 'org', 'io', 'tech', 'couk', 'uk']))
    is_buzzword = any(w in rec_name.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting'])
    
    if is_email_like or is_buzzword or not worker.is_human_name(rec_name, ""):
        plan_a_count += 1
        plan_a_records.append(r)
        if '@' in rec_name:
            dom = rec_name.split('@')[1].split('.')[0].lower()
            if any(f in dom for f in free_domains):
                personal_domain_count += 1

print(f"=== 1. RESOLVING THE 15,619 GAP ===")
print(f"Total swapped records (human name in Company column): {len(swapped_recruiters)}")
print(f"Total matching Plan A (Email-in-Name / Buzzwords / Non-Human): {plan_a_count}")
print(f"Total personal/free email domains detected in Plan A: {personal_domain_count}")
print(f"Remaining true ambiguous/unrecoverable count: {len(swapped_recruiters) - plan_a_count}")

print(f"\n=== 2. TEN CONCRETE COMPARISONS OF DUPLICATE MATCHES ===")
random.seed(42)
sample_dups = random.sample(plan_a_records, min(50, len(plan_a_records)))

co_name_to_id = {c.company_name.lower(): c.company_id for c in all_companies if c.company_name}

shown = 0
for rec in sample_dups:
    primary_email_string = rec.recruiter_name.split(';')[0].strip()
    misplaced_human_name = company_map[rec.company_id].company_name if rec.company_id in company_map else ""
    
    if "@" in primary_email_string:
        parts = primary_email_string.split('@')
        domain_part = parts[1].lower()
        clean_domain = re.sub(r"\.?(com|net|org|tech|io|couk|uk)$", "", domain_part)
        reconstructed_co_name = clean_domain.replace('-', ' ').title()
        
        matched_id = co_name_to_id.get(reconstructed_co_name.lower())
        if matched_id:
            dup = db.query(Recruiter).filter(Recruiter.company_id == matched_id, Recruiter.recruiter_name.ilike(misplaced_human_name), Recruiter.recruiter_id != rec.recruiter_id).first()
            if dup:
                shown += 1
                print(f"\nComparison #{shown}:")
                print(f"  CORRUPTED: ID={rec.recruiter_id} | NameField='{rec.recruiter_name}' | CoField='{misplaced_human_name}' | Email='{rec.email}'")
                print(f"  CLEAN DUP: ID={dup.recruiter_id} | NameField='{dup.recruiter_name}' | CoField='{company_map[dup.company_id].company_name if dup.company_id in company_map else ''}' | Email='{dup.email}' | Status='{dup.email_status}'")
                if shown >= 10:
                    break

