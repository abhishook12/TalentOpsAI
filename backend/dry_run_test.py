import json
from sqlalchemy import text
from app.database import SessionLocal
from enrich_recruiter_contacts import EnrichmentWorker
from app.models.models import Recruiter

class DummyArgs:
    apply = False
    dry_run = True
    minimum_confidence = 70
    run_id = 'test'
    batch_size = 100

db = SessionLocal()
db.execute(text("DEALLOCATE ALL"))
db.commit()

worker = EnrichmentWorker(db, DummyArgs())

old_96 = db.execute(text("SELECT recruiter_id, final_value FROM enrichment_audit WHERE run_id = 'full-enrichment-20260623-221909' AND action = 'applied'")).fetchall()
old_96_ids = [r[0] for r in old_96]

rejected = db.execute(text("SELECT recruiter_id, overall_outcome FROM enrichment_results WHERE run_id = 'full-enrichment-20260623-221909' AND overall_outcome LIKE 'REJECTED%' LIMIT 100")).fetchall()

skipped = db.execute(text("SELECT recruiter_id, overall_outcome FROM enrichment_results WHERE run_id = 'full-enrichment-20260623-221909' AND overall_outcome LIKE 'SKIPPED%' LIMIT 100")).fetchall()

upcoming = db.execute(text("SELECT recruiter_id FROM recruiters WHERE recruiter_id > 38960 ORDER BY recruiter_id LIMIT 100")).fetchall()

for cat_name, cat_ids in [("Old 96 Applied", old_96_ids), ("Old Rejected", [r[0] for r in rejected]), ("Old Skipped", [r[0] for r in skipped]), ("Upcoming", [r[0] for r in upcoming])]:
    print(f"\n--- {cat_name} ({len(cat_ids)}) ---")
    cat_applied = 0
    
    if not cat_ids:
        continue
    
    for rid in cat_ids:
        r = db.query(Recruiter).filter(Recruiter.recruiter_id == rid).first()
        if not r: continue
        # Pre-load company
        c = r.company
        try:
            outcome = worker.process_recruiter(r)
            if outcome in ['PROPOSED', 'PENDING_UPDATE', 'applied']:
                cat_applied += 1
                # print(f"  [PROPOSED] ID: {r.recruiter_id} Name: {r.recruiter_name} Outcome: {outcome}")
        except Exception as e:
            pass

    print(f"Total proposed in {cat_name}: {cat_applied}")

db.close()
