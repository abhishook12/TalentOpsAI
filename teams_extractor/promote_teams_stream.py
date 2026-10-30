"""
promote_teams_stream.py — Promotes TEAMS_CTV_UPWARD_STREAM staging records
through the Universal Ingestion Funnel into the Master Recruiters table,
and updates DuckDB Parquet for instant frontend availability.
"""

import sys, os, time, logging
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging
from backend.app.models.models import Recruiter
from backend.app.services.ingestion_funnel import universal_funnel
from backend.scripts.incremental_parquet_sync import sync as sync_parquet
from backend.app.services.recruiter_store import recruiter_store

def promote_all_teams_stream():
    db = SessionLocal()
    try:
        pending_records = db.query(DiscoveryStaging).filter(
            DiscoveryStaging.batch_id == "TEAMS_CTV_UPWARD_STREAM",
            DiscoveryStaging.processing_status == "pending"
        ).all()

        logging.info(f"Found {len(pending_records)} pending records in TEAMS_CTV_UPWARD_STREAM to process...")
        promoted = 0
        enriched = 0
        held = 0

        for stg in pending_records:
            try:
                res = universal_funnel.process_staging_record(stg, db)
                db.commit()
                status = res.get("status")
                if status == "PROMOTED":
                    promoted += 1
                    logging.info(f"✅ PROMOTED: {stg.raw_name} -> Recruiter #{res.get('recruiter_id')}")
                elif status == "ENRICHED":
                    enriched += 1
                    logging.info(f"🔄 ENRICHED: {stg.raw_name} -> Recruiter #{res.get('recruiter_id')}")
                else:
                    held += 1
            except Exception as e:
                logging.error(f"Error processing {stg.raw_name}: {e}")
                db.rollback()

        logging.info(f"Funnel Complete: {promoted} Promoted to Recruiter, {enriched} Enriched, {held} Held.")

        # Sync DuckDB Parquet so frontend sees them immediately
        logging.info("Running incremental Parquet sync...")
        try:
            sync_parquet()
            recruiter_store.reload()
            logging.info("Parquet & RecruiterStore successfully reloaded!")
        except Exception as e:
            logging.error(f"Parquet sync error: {e}")

        # Summary of Scott Tupper
        last_person = db.query(Recruiter).filter(Recruiter.recruiter_name == "Scott Tupper").first()
        if last_person:
            logging.info(f"Verified Scott Tupper in Recruiter table: ID {last_person.recruiter_id} | Co: {last_person.company_id} | Email: {last_person.email} | Phone: {last_person.phone}")

    finally:
        db.close()

if __name__ == "__main__":
    promote_all_teams_stream()
