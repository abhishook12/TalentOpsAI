import sys, os, json
sys.path.insert(0, r'C:\TalentOpsAI')

from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging

db = SessionLocal()
try:
    # 1. Total staged in batch TEAMS_CTV_UPWARD_STREAM
    upward_records = db.query(DiscoveryStaging).filter(
        DiscoveryStaging.batch_id == "TEAMS_CTV_UPWARD_STREAM"
    ).order_by(DiscoveryStaging.id.asc()).all()

    print(f"Total in TEAMS_CTV_UPWARD_STREAM: {len(upward_records)}")
    
    # 2. Total all Teams
    all_teams = db.query(DiscoveryStaging).filter(
        DiscoveryStaging.device_id.like("%TEAMS%")
    ).count()
    print(f"Total all Teams records in discovery_staging: {all_teams}")

    # 3. Print the most recent candidates in upward stream
    print("\n--- Recent Candidates in TEAMS_CTV_UPWARD_STREAM ---")
    for r in upward_records[-15:]:
        meta = json.loads(r.metadata_json or '{}')
        p2 = meta.get('phone2')
        p3 = meta.get('phone3')
        p4 = meta.get('phone4')
        e2 = meta.get('email2')
        ts = meta.get('timestamp')
        print(f"ID {r.id}: {r.raw_name} | Co: {r.raw_company} | Email: {r.raw_email} (e2: {e2}) | Phone: {r.raw_phone} (p2: {p2}, p3: {p3}, p4: {p4}) | Time: {ts}")

    # 4. Specifically look for Scott Tupper, Mike Colles, Rebecca Rouse, Jessie White
    print("\n--- Specific Highlight Search ---")
    for name in ["Scott Tupper", "Mike Colles", "Rebecca Rouse", "Jessie White", "bob cusack", "Sandra Stewart"]:
        found = db.query(DiscoveryStaging).filter(DiscoveryStaging.raw_name.ilike(f"%{name}%")).first()
        if found:
            meta = json.loads(found.metadata_json or '{}')
            print(f"FOUND {name}: Co: {found.raw_company} | Email: {found.raw_email} | Phone: {found.raw_phone} | Batch: {found.batch_id} | TS: {meta.get('timestamp')}")
        else:
            print(f"NOT FOUND: {name}")

finally:
    db.close()
