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
co_name_to_id = {c.company_name.lower(): c.company_id for c in all_companies if c.company_name}

for c in all_companies:
    co = c.company_name or ""
    if co and ' ' in co and worker.is_human_name(co, ''):
        human_company_ids.add(c.company_id)

swapped_recruiters = db.query(Recruiter).filter(Recruiter.company_id.in_(human_company_ids)).all()

group_2887 = []
group_6561_new = []

for r in swapped_recruiters:
    rec_name = r.recruiter_name or ""
    orig_fixable = (not worker.is_human_name(rec_name, "") or any(w in rec_name.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting']))
    
    is_email_like = ('@' in rec_name or any(rec_name.lower().endswith(t) for t in ['com', 'net', 'org', 'io', 'tech', 'couk', 'uk']))
    is_buzzword = any(w in rec_name.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting'])
    new_fixable = (is_email_like or is_buzzword or not worker.is_human_name(rec_name, ""))
    
    if orig_fixable:
        group_2887.append(r)
    elif new_fixable:
        group_6561_new.append(r)

print(f"=== 1. SUBGROUP BREAKDOWN ===")
print(f"Original 2,887 group count: {len(group_2887)}")
print(f"New jump subgroup count (~6,561): {len(group_6561_new)}")

print(f"\n=== 10 EXAMPLES FROM JUST THE NEW SUBGROUP ===")
random.seed(99)
sample_new = random.sample(group_6561_new, min(10, len(group_6561_new)))
for i, r in enumerate(sample_new):
    co = company_map[r.company_id].company_name if r.company_id in company_map else ""
    print(f"{i+1}. ID={r.recruiter_id} | RecNameField='{r.recruiter_name}' | CoNameField='{co}' | Email='{r.email}'")

print(f"\n=== 2. DUPLICATE MATCH RATE AT SCALE (Across {len(group_2887) + len(group_6561_new)} candidates) ===")
full_pool = group_2887 + group_6561_new

# Preload all recruiters into memory indexed by company_id and lowercase name
all_recs = db.query(Recruiter).all()
co_recs_by_name = {}
for cand in all_recs:
    if cand.company_id:
        co_recs_by_name.setdefault(cand.company_id, {}).setdefault(cand.recruiter_name.lower().strip(), []).append(cand)

pass_all_3 = 0
partial_match = 0
no_dup_found = 0

worst_matches = []

for rec in full_pool:
    primary_email_string = rec.recruiter_name.split(';')[0].strip()
    misplaced_human_name = company_map[rec.company_id].company_name if rec.company_id in company_map else ""
    misplaced_lower = misplaced_human_name.lower().strip()
    
    if "@" in primary_email_string:
        parts = primary_email_string.split('@')
        domain_part = parts[1].lower()
        clean_domain = re.sub(r"\.?(com|net|org|tech|io|couk|uk)$", "", domain_part)
        reconstructed_co_name = clean_domain.replace('-', ' ').title()
        
        matched_id = co_name_to_id.get(reconstructed_co_name.lower())
        if matched_id and matched_id in co_recs_by_name:
            cand_dict = co_recs_by_name[matched_id]
            
            # Try exact match first
            dups = cand_dict.get(misplaced_lower, [])
            # Exclude self
            dups = [d for d in dups if d.recruiter_id != rec.recruiter_id]
            
            if dups:
                best_dup = dups[0]
                same_co = (best_dup.company_id == rec.company_id)
                cand_dom = best_dup.email.split('@')[1].lower() if (best_dup.email and '@' in best_dup.email) else ""
                same_dom = (cand_dom == domain_part if cand_dom else False)
                
                if same_co and same_dom:
                    pass_all_3 += 1
                else:
                    partial_match += 1
                    worst_matches.append((rec, best_dup, 1.0, same_co, same_dom))
            else:
                no_dup_found += 1
        else:
            no_dup_found += 1
    else:
        no_dup_found += 1

print(f"Total checked for duplicates: {len(full_pool)}")
print(f"1. Pass ALL 3 checks automatically (Exact Name match, Same Co ID, Same Domain): {pass_all_3}")
print(f"2. Partial matches (Same name, but different Co ID/Domain): {partial_match}")
print(f"3. No exact duplicate found at target company: {no_dup_found}")

print(f"\n=== WORST / EDGE CASE MATCHES ===")
for i, x in enumerate(worst_matches[:10]):
    rec, dup, score, sco, sdom = x
    print(f"\nEdgeCase #{i+1} (SameCoID: {sco} | SameDom: {sdom}):")
    print(f"  CORRUPTED: ID={rec.recruiter_id} | NameField='{rec.recruiter_name}' | CoField='{company_map[rec.company_id].company_name if rec.company_id in company_map else ''}' | Email='{rec.email}'")
    print(f"  MATCH DUP: ID={dup.recruiter_id} | NameField='{dup.recruiter_name}' | CoField='{company_map[dup.company_id].company_name if dup.company_id in company_map else ''}' | Email='{dup.email}'")

