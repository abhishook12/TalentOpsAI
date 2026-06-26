import os
import sys
import json
import datetime
import re
from difflib import SequenceMatcher
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace

def execute_repair():
    db = SessionLocal()
    args = SimpleNamespace(
        dry_run=False, apply=True, minimum_confidence=70, 
        batch_size=500, max_updates=500, all_recruiters=True
    )
    worker = EnrichmentWorker(db, args)
    
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    script_version = "v1.0.0_comprehensive_repair_exec"
    
    total_rec_baseline = db.query(Recruiter).count()
    
    all_companies = db.query(Company).all()
    company_map = {c.company_id: c for c in all_companies}
    co_name_to_id = {c.company_name.lower(): c.company_id for c in all_companies if c.company_name}
    
    human_co_ids = set()
    for c in all_companies:
        co = c.company_name or ""
        if co and ' ' in co and worker.is_human_name(co, ''):
            human_co_ids.add(c.company_id)

    target_pool = db.query(Recruiter).filter(Recruiter.company_id.in_(human_co_ids)).all()
    
    print(f"=== REAL REPAIR EXECUTION START (RunID: {run_id}) ===")
    print(f"Baseline Total Recruiters: {total_rec_baseline}")
    print(f"Target Swapped Pool Count: {len(target_pool)}")
    
    all_recs = db.query(Recruiter).all()
    co_recs_by_name = {}
    for cand in all_recs:
        if cand.company_id:
            co_recs_by_name.setdefault(cand.company_id, {}).setdefault(cand.recruiter_name.lower().strip(), []).append(cand)

    free_domains = ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol', 'protonmail']

    cat_clean_dup = 0
    cat_corr_pair = 0
    cat_personal_block = 0
    cat_safe_swap = 0
    cat_orphan = 0

    backup_export = []
    audit_log = []

    for rec in target_pool:
        # 1. Backup snapshot
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

            is_dup_handled = False
            if matched_id and matched_id in co_recs_by_name:
                dups = [d for d in co_recs_by_name[matched_id].get(misplaced_lower, []) if d.recruiter_id != rec.recruiter_id]
                if dups:
                    best_dup = dups[0]
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
                    is_dup_handled = True

            if not is_dup_handled:
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
                    
                    new_email = primary_email_string if "@" in primary_email_string else None
                    if new_email and "." not in new_email.split('@')[1]:
                        dpart = new_email.split('@')[1]
                        for tld in ['com', 'net', 'org', 'io', 'tech']:
                            if dpart.endswith(tld):
                                new_email = new_email.split('@')[0] + "@" + dpart[:-len(tld)] + "." + tld
                                break
                    
                    gen_email = new_email if (new_email and re.match(r"[^@]+@[^@]+\.[^@]+", new_email)) else None
                    
                    # Update audit metadata
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
                    rec.repair_reason = "repaired_column_swap"
        else:
            cat_orphan += 1
            rec.needs_review = True
            rec.repair_reason = f"unrecoverable_import_corruption:{rec.source_job_id or 'location_workbook'}"

    total_cat = cat_clean_dup + cat_corr_pair + cat_personal_block + cat_safe_swap + cat_orphan
    assert total_cat == len(target_pool), f"Count mismatch: {total_cat} vs {len(target_pool)}"

    # Write backup file
    backup_path = f"backend/backup_18774_cohort_{run_id}.json"
    with open(backup_path, "w", encoding="utf-8") as bf:
        json.dump(backup_export, bf, indent=2)
    print(f"[SUCCESS] Wrote full backup to {backup_path}")

    # Commit transaction
    db.commit()
    print("[SUCCESS] DB Transaction Committed Successfully!")

    # Verification Queries
    print("\n=== POST-REPAIR VERIFICATION QUERIES ===")
    final_count = db.query(Recruiter).count()
    print(f"1. Final Total Recruiters Count: {final_count} (Expected: 91333)")
    assert final_count == 91333, "Recruiter count changed!"

    bad_emails = db.query(Recruiter).filter(
        Recruiter.repair_reason == 'repaired_column_swap',
        or_(Recruiter.email.like('%@missing.local%'), Recruiter.email.like('%@invalid.local%'))
    ).count()
    print(f"2. Newly Repaired rows with placeholder emails: {bad_emails} (Expected: 0)")

    resolved_count = db.query(Recruiter).filter(
        or_(
            Recruiter.repair_reason.in_([
                'merged_corrupted_duplicate_pending_review',
                'duplicate_pair_both_corrupted_pending_review',
                'repaired_column_swap',
                'repair_blocked_personal_email_domain'
            ]),
            Recruiter.repair_reason.like('unrecoverable_import_corruption%')
        )
    ).count()
    print(f"3. Total Tagged/Repaired Cohort Rows: {resolved_count} (Expected: 18774)")

    print("\n=== REPAIR WORKFLOW COMPLETE ===")

if __name__ == "__main__":
    execute_repair()
