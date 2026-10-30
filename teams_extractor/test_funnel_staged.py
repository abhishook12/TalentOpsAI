import sys
sys.path.insert(0, r'C:\TalentOpsAI')
from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging
from backend.app.services.ingestion_funnel import universal_funnel

db = SessionLocal()
try:
    # Get 3 pending records from TEAMS_CTV_UPWARD_STREAM
    staged_records = db.query(DiscoveryStaging).filter(
        DiscoveryStaging.batch_id == "TEAMS_CTV_UPWARD_STREAM",
        DiscoveryStaging.processing_status == "pending"
    ).limit(3).all()

    print(f"Testing funnel on {len(staged_records)} records...")
    for stg in staged_records:
        res = universal_funnel.process_staging_record(stg, db)
        print(f"Result for {stg.raw_name}: {res}")
    db.commit()
finally:
    db.close()
