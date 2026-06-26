import os
import sys
import json
from sqlalchemy import or_, not_, func
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter
from enrich_recruiter_contacts import EnrichmentWorker, generate_email
from types import SimpleNamespace

def main():
    db = SessionLocal()
    args = SimpleNamespace(
        dry_run=True, apply=False, minimum_confidence=70, 
        batch_size=500, max_updates=500, all_recruiters=True,
        start_after_id=None, company=None, resume_run_id=None,
        apply_pending=False, retry_failed=False
    )
    worker = EnrichmentWorker(db, args)
    worker.run_id = "dry-run-sample"
    
    # 2. Fetch sample: 500 records (missing, malformed, generic)
    sample = db.query(Recruiter).filter(
        or_(
            Recruiter.email == None,
            Recruiter.email == '',
            Recruiter.email_status != 'verified'
        )
    ).order_by(Recruiter.recruiter_id.desc()).limit(500).all()
    
    results = {
        "APPLIED_MISSING_EMAIL": [],
        "SKIPPED_ALREADY_CORRECT": [],
        "PENDING_REVIEW_EXISTING_EMAIL_MISMATCH": [],
        "PENDING_REVIEW_SUSPICIOUS_EXISTING_EMAIL": [],
        "PENDING_REVIEW_NAME_NORMALIZATION": [],
        "REJECTED_INVALID_GENERATED_EMAIL": [],
        "REJECTED_INSUFFICIENT_EVIDENCE": [],
        "SKIPPED_NO_VERIFIED_PATTERN": [],
        "SKIPPED_INVALID_NON_PERSON_NAME": [],
        "FAILED_TECHNICAL_ERROR": []
    }
    
    def map_status(status):
        if status in results: return status
        if status == "APPLIED": return "APPLIED_MISSING_EMAIL"
        if status == "FAILED": return "FAILED_TECHNICAL_ERROR"
        return status
        
    for r in sample:
        try:
            outcome = worker.process_recruiter(r)
            mapped = map_status(outcome)
            if mapped not in results:
                results[mapped] = []
                
            # Determine generated candidate if any
            candidate = None
            if r.company:
                fn, ln = worker.extract_names(r.recruiter_name, r.email)
                pattern_data = worker.detect_company_patterns(r.company)
                if pattern_data and fn and ln:
                    candidate = generate_email(fn, ln, pattern_data['domain'], pattern_data['pattern'])
                    
            results[mapped].append({
                "id": r.recruiter_id,
                "name": r.recruiter_name,
                "old_email": r.email,
                "candidate": candidate,
                "company": r.company.company_name if r.company else "None",
                "reason": f"Outcome from worker process: {mapped}"
            })
        except Exception as e:
            results["FAILED_TECHNICAL_ERROR"].append({
                "id": r.recruiter_id,
                "name": r.recruiter_name,
                "old_email": r.email,
                "candidate": None,
                "company": r.company.company_name if r.company else "None",
                "reason": str(e)
            })
            
    # CRITICAL: Rollback so dry-run never writes to DB (since process_recruiter writes proposals)
    db.rollback()
    
    # 5. Output exact counts & examples
    print("=== FINAL DRY-RUN COUNTS ===")
    for k in results.keys():
        print(f"{k}: {len(results[k])}")
        
    import random
    print("\n=== EXAMPLES (Custom Output for V4) ===")
    
    # Show ALL 13 PENDING_REVIEW_EXISTING_EMAIL_MISMATCH records
    mismatches = results.get("PENDING_REVIEW_EXISTING_EMAIL_MISMATCH", [])
    print(f"\n--- PENDING_REVIEW_EXISTING_EMAIL_MISMATCH (ALL {len(mismatches)} items) ---")
    for item in mismatches:
        print(f"Name: {item['name']} | Co: {item['company']}")
        print(f"Old Email: {item['old_email']}")
        print(f"Generated: {item['candidate']}")
        print(f"Reason: {item['reason']}")
        print("-")
        
    # Show 15 RANDOM SKIPPED_INVALID_NON_PERSON_NAME records
    non_persons = results.get("SKIPPED_INVALID_NON_PERSON_NAME", [])
    random.seed(42) # Deterministic random
    sampled_non_persons = random.sample(non_persons, min(15, len(non_persons)))
    print(f"\n--- SKIPPED_INVALID_NON_PERSON_NAME (15 RANDOM out of {len(non_persons)}) ---")
    for item in sampled_non_persons:
        print(f"Name: {item['name']} | Co: {item['company']}")
        print(f"Old Email: {item['old_email']}")
        print(f"Generated: {item['candidate']}")
        print(f"Reason: {item['reason']}")
        print("-")
            
    # 6. Step D
    zero_yield = len(results.get("APPLIED_MISSING_EMAIL", [])) == 0 and \
                 len(results.get("PENDING_REVIEW_EXISTING_EMAIL_MISMATCH", [])) == 0 and \
                 len(results.get("PENDING_REVIEW_SUSPICIOUS_EXISTING_EMAIL", [])) == 0 and \
                 len(results.get("PENDING_REVIEW_NAME_NORMALIZATION", [])) == 0
                 
    if zero_yield:
        print("\n=== YIELD IS ZERO. CHECKING COMPANY EVIDENCE ===")
        evidence_count = 0
        companies_checked = set()
        for r in sample:
            if not r.company_id: continue
            if r.company_id in companies_checked: continue
            companies_checked.add(r.company_id)
            
            c_count = db.query(func.count(Recruiter.recruiter_id)).filter(
                Recruiter.company_id == r.company_id,
                Recruiter.email.like('%@%'),
                not_(Recruiter.email.like('%missing.local%')),
                Recruiter.email_status != 'invalid'
            ).scalar()
            
            if c_count >= 2:
                evidence_count += 1
                
        print(f"RECORDS WITH COMPANY EVIDENCE: {evidence_count} companies out of {len(companies_checked)} unique companies in sample have 2+ verified-looking emails.")

if __name__ == "__main__":
    main()
