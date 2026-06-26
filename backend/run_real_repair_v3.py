import os
import sys
import json
import datetime
import re
import time
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace

db = SessionLocal()
args = SimpleNamespace(
    dry_run=False, apply=True, minimum_confidence=70, 
    batch_size=500, max_updates=500, all_recruiters=True
)
worker = EnrichmentWorker(db, args)

def fetch_with_retry(query_fn, retries=5):
    for i in range(retries):
        try:
            return query_fn()
        except Exception as e:
            print(f"Network hiccup: {e}. Retrying in {2**i}s...")
            time.sleep(2**i)
            db.rollback()
    raise RuntimeError("Failed to fetch data after retries")

print("Loading companies...")
all_companies = fetch_with_retry(lambda: db.query(Company).all())
company_map = {c.company_id: c for c in all_companies}
co_name_to_id = {c.company_name.lower(): c.company_id for c in all_companies if c.company_name}

human_co_ids = set()
for c in all_companies:
    co = c.company_name or ""
    if co and ' ' in co and worker.is_human_name(co, ''):
        human_co_ids.add(c.company_id)

print("Loading target pool...")
target_pool = fetch_with_retry(lambda: db.query(Recruiter).filter(Recruiter.company_id.in_(human_co_ids)).all())

print("Loading all recruiters...")
all_recs = fetch_with_retry(lambda: db.query(Recruiter).all())
co_recs_by_name = {}
email_to_rec = {}

for cand in all_recs:
    if cand.company_id:
        co_recs_by_name.setdefault(cand.company_id, {}).setdefault(cand.recruiter_name.lower().strip(), []).append(cand)
    if cand.email:
        email_to_rec[cand.email.lower().strip()] = cand

free_domains = ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol', 'protonmail']

cat_clean_dup = 0
cat_corr_pair = 0
cat_personal_block = 0
cat_safe_swap = 0
cat_orphan = 0

backup_export = []
audit_log = []

for rec in target_pool:
    backup_export.append({
        "recruiter_id": rec.recruiter_id,
        "recruiter_name": rec.recruiter_name,
        "company_id": rec.company_id,
        "company_name": company_map[rec.company_id].company_name if rec.company_id in company_map else None,
        "email": rec.email,
        "is_active": rec.is_active,
        "needs_review": rec.needs_review,
        "repair_reason": rec.repair_reason,
        "raw_data": rec.raw_data,
        "metadata_json": rec.metadata_json
    })

    rec_name = rec.recruiter_name or ""
    misplaced_human_name = company_map[rec.company_id].company_name if rec.company_id in company_map else ""
    misplaced_lower = misplaced_human_name.lower().strip()

    is_email_like = ('@' in rec_name or any(rec_name.lower().endswith(t) for t in ['com', 'net', 'org', 'io', 'tech', 'couk', 'uk']))
    is_buzzword = any(w in rec_name.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting'])
    is_plan_a = (is_email_like or is_buzzword or not worker.is_human_name(rec_name, ""))

    if is_plan_a:
        primary_email_string = rec_name.split(';')[0].strip()
        
        matched_id = None
        if "@" in primary_email_string:
            parts = primary_email_string.split('@')
            domain_part = parts[1].lower()
            clean_domain = re.sub(r"\.?(com|net|org|tech|io|couk|uk)$", "", domain_part)
            reconstructed_co_name = clean_domain.replace('-', ' ').title()
            matched_id = co_name_to_id.get(reconstructed_co_name.lower())

        new_email = primary_email_string if "@" in primary_email_string else None
        if new_email and "." not in new_email.split('@')[1]:
            dpart = new_email.split('@')[1]
            for tld in ['com', 'net', 'org', 'io', 'tech']:
                if dpart.endswith(tld):
                    new_email = new_email.split('@')[0] + "@" + dpart[:-len(tld)] + "." + tld
                    break
        
        gen_email = new_email if (new_email and re.match(r"[^@]+@[^@]+\.[^@]+", new_email)) else None
        gen_email_lower = gen_email.lower().strip() if gen_email else ""

        best_dup = None
        if gen_email_lower and gen_email_lower in email_to_rec and email_to_rec[gen_email_lower].recruiter_id != rec.recruiter_id:
            best_dup = email_to_rec[gen_email_lower]
        elif matched_id and matched_id in co_recs_by_name:
            dups = [d for d in co_recs_by_name[matched_id].get(misplaced_lower, []) if d.recruiter_id != rec.recruiter_id]
            if dups:
                best_dup = dups[0]

        if best_dup:
            dem = best_dup.email or ""
            is_clean = (dem and str(dem).strip() != "" and "@missing.local" not in dem and "@invalid.local" not in dem and "@example.com" not in dem)
            
            if is_clean:
                cat_clean_dup += 1
                rec.needs_review = True
                rec.repair_reason = "merged_corrupted_duplicate_pending_review"
            else:
                cat_corr_pair += 1
                rec.needs_review = True
                rec.repair_reason = "duplicate_pair_both_corrupted_pending_review"
        else:
            is_personal = False
            if "@" in primary_email_string:
                dom = primary_email_string.split('@')[1].split('.')[0].lower()
                if any(f in dom for f in free_domains):
                    is_personal = True

            if is_personal:
                cat_personal_block += 1
                rec.needs_review = True
                rec.repair_reason = "repair_blocked_personal_email_domain"
            else:
                cat_safe_swap += 1
                
                meta = json.loads(rec.metadata_json) if rec.metadata_json else {}
                meta["pre_repair_corrupted"] = {
                    "recruiter_name": rec.recruiter_name,
                    "company_id": rec.company_id,
                    "email": rec.email
                }
                rec.metadata_json = json.dumps(meta)
                
                rec.recruiter_name = misplaced_human_name
                rec.company_id = matched_id
                if gen_email:
                    rec.email = gen_email
                    email_to_rec[gen_email_lower] = rec
                rec.repair_reason = "repaired_column_swap"
    else:
        cat_orphan += 1
        rec.needs_review = True
        rec.repair_reason = f"unrecoverable_import_corruption:{rec.source_job_id or 'location_workbook'}"

run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"backend/backup_18774_cohort_{run_id}.json"
with open(backup_path, "w", encoding="utf-8") as bf:
    json.dump(backup_export, bf, indent=2)

print(f"Counts: CleanDup={cat_clean_dup}, CorrPair={cat_corr_pair}, Personal={cat_personal_block}, SafeSwap={cat_safe_swap}, Orphan={cat_orphan}")

for i in range(5):
    try:
        db.commit()
        print("[SUCCESS] Committed successfully!")
        break
    except Exception as e:
        print(f"Commit network drop: {e}. Retrying...")
        time.sleep(3)

