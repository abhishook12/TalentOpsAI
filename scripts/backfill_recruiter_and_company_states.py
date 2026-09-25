"""
scripts/backfill_recruiter_and_company_states.py

Fast, set-based backfill for state, normalized_city, and company state across PostgreSQL master database.
"""
import sys
import os
import logging
from collections import Counter

sys.path.insert(0, r"c:\TalentOpsAI")

from backend.app.database import SessionLocal
from backend.app.models.models import Recruiter, Company, RecruiterLocation
from backend.app.routes.recruiters import _update_state_metadata
from backend.app.utils.state_recovery import infer_state_from_sources
from backend.app.routes.analytics import analytics_cache

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("backfill")

def run_backfill():
    db = SessionLocal()
    try:
        # Step 1: Baseline Stats
        init_unassigned_recs = db.query(Recruiter).filter((Recruiter.state == None) | (Recruiter.state == '')).count()
        total_recs = db.query(Recruiter).count()
        print(f"Baseline: {init_unassigned_recs} of {total_recs} recruiters have unassigned state.")

        # Step 2: Backfill Recruiters (282 records total)
        recs_to_update = db.query(Recruiter).filter((Recruiter.state == None) | (Recruiter.state == '')).all()
        recs_resolved = 0
        locs_created = 0

        for r in recs_to_update:
            _update_state_metadata(r, db)
            if r.state:
                recs_resolved += 1
            
            # Ensure RecruiterLocation entry exists
            if r.location:
                existing_loc = db.query(RecruiterLocation).filter(RecruiterLocation.recruiter_id == r.recruiter_id).first()
                if not existing_loc:
                    db.add(RecruiterLocation(
                        recruiter_id=r.recruiter_id,
                        city=r.location,
                        location_type="person",
                        is_fallback=False,
                        confidence_score=85,
                        source="backfill_recovery"
                    ))
                    locs_created += 1

        db.commit()
        print(f"Recruiter Pass: Resolved state for {recs_resolved} recruiters; created {locs_created} RecruiterLocation entries.")

        # Step 3: Backfill Companies that have recruiters or location
        comp_ids_with_recs = [c[0] for c in db.query(Recruiter.company_id).filter(Recruiter.company_id != None).distinct().all()]
        comps_to_update = db.query(Company).filter(
            Company.company_id.in_(comp_ids_with_recs),
            (Company.state == None) | (Company.state == '')
        ).all()
        
        comps_resolved = 0
        for c in comps_to_update:
            # 1. Try from company location
            if c.location:
                st_res = infer_state_from_sources([("company_location", c.location)])
                if st_res and st_res.get("state"):
                    c.state = st_res["state"]
                    comps_resolved += 1
                    continue

            # 2. Try consensus from linked recruiters in PostgreSQL
            r_states = [r.state for r in db.query(Recruiter).filter(Recruiter.company_id == c.company_id).all() if r.state and r.state not in ('US', 'Unknown')]
            if r_states:
                most_common_st = Counter(r_states).most_common(1)[0][0]
                c.state = most_common_st
                comps_resolved += 1

        db.commit()
        print(f"Company Pass: Resolved state for {comps_resolved} recruiter-linked companies.")

        # Step 4: Clear analytical caches
        analytics_cache.clear()
        print("Cleared analytics cache.")

        # Step 5: Verification & Distribution Breakdown
        final_unassigned_recs = db.query(Recruiter).filter((Recruiter.state == None) | (Recruiter.state == '')).count()
        print(f"\nFinal Status: Unassigned recruiters reduced from {init_unassigned_recs} down to {final_unassigned_recs}!")
        
        from sqlalchemy import func
        state_dist = db.query(Recruiter.state, func.count(Recruiter.recruiter_id)).group_by(Recruiter.state).order_by(func.count(Recruiter.recruiter_id).desc()).all()
        print("\nRecruiter Distribution by State in Main Database:")
        for st, cnt in state_dist:
            print(f"  {st or 'Unassigned'}: {cnt}")

    finally:
        db.close()

if __name__ == "__main__":
    run_backfill()
