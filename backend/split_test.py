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

group_9448 = []

for r in swapped_recruiters:
    rec_name = r.recruiter_name or ""
    is_email_like = ('@' in rec_name or any(rec_name.lower().endswith(t) for t in ['com', 'net', 'org', 'io', 'tech', 'couk', 'uk']))
    is_buzzword = any(w in rec_name.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting'])
    fixable = (is_email_like or is_buzzword or not worker.is_human_name(rec_name, ""))
    if fixable:
        group_9448.append(r)

all_recs = db.query(Recruiter).all()
co_recs_by_name = {}
for cand in all_recs:
    if cand.company_id:
        co_recs_by_name.setdefault(cand.company_id, {}).setdefault(cand.recruiter_name.lower().strip(), []).append(cand)

clean_matches = []
corrupted_pair_matches = []

for rec in group_9448:
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
            dups = cand_dict.get(misplaced_lower, [])
            dups = [d for d in dups if d.recruiter_id != rec.recruiter_id]
            
            if dups:
                best_dup = dups[0]
                em = best_dup.email or ""
                is_clean = (em and str(em).strip() != "" and "@missing.local" not in em and "@invalid.local" not in em and "@example.com" not in em)
                
                if is_clean:
                    clean_matches.append((rec, best_dup))
                else:
                    corrupted_pair_matches.append((rec, best_dup))

print(f"=== DUPLICATE SPLIT COUNT (Total Matched: {len(clean_matches) + len(corrupted_pair_matches)}) ===")
print(f"1. Matches against TRULY clean records (real email) -> Tag: 'merged_corrupted_duplicate_pending_review': {len(clean_matches)}")
print(f"2. Matches against ANOTHER corrupted/placeholder record -> Tag: 'duplicate_pair_both_corrupted_pending_review': {len(corrupted_pair_matches)}")

print(f"\n=== 5 EXAMPLES OF CASE 1 (Clean-record matches) ===")
for i, x in enumerate(clean_matches[:5]):
    rec, dup = x
    print(f"\nCleanCase #{i+1}:")
    print(f"  CORRUPTED: ID={rec.recruiter_id} | NameField='{rec.recruiter_name}' | CoField='{company_map[rec.company_id].company_name if rec.company_id in company_map else ''}' | Email='{rec.email}'")
    print(f"  CLEAN DUP: ID={dup.recruiter_id} | NameField='{dup.recruiter_name}' | CoField='{company_map[dup.company_id].company_name if dup.company_id in company_map else ''}' | Email='{dup.email}'")

print(f"\n=== 5 EXAMPLES OF CASE 2 (Corrupted-pair matches) ===")
for i, x in enumerate(corrupted_pair_matches[:5]):
    rec, dup = x
    print(f"\nCorruptedPair #{i+1}:")
    print(f"  CORRUPTED: ID={rec.recruiter_id} | NameField='{rec.recruiter_name}' | CoField='{company_map[rec.company_id].company_name if rec.company_id in company_map else ''}' | Email='{rec.email}'")
    print(f"  PAIR DUP : ID={dup.recruiter_id} | NameField='{dup.recruiter_name}' | CoField='{company_map[dup.company_id].company_name if dup.company_id in company_map else ''}' | Email='{dup.email}'")

