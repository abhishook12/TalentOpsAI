"""
check_pipeline_1_ingestion_and_staging.py
Pipeline Verification Check 1: Ingestion Buffer, Batch Clustering & Identity Resolution Pipeline.

Tests:
1. Ingestion of raw observations into `discovery_staging` buffer.
2. Execution of `DiscoveryProcessor.process_pending_batch()`.
3. Multi-observation clustering (grouping same candidate from multiple frames).
4. Identity resolution and confidence calculation into `resolved_persons`.
5. Master database matching and commit (`NEW` / `ENRICH` / `DUPLICATE`).
6. Audit event logging into `extension_discovery_events`.
"""

import sys
import os
import json
import secrets
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.auth_models import User
from app.models.models import Recruiter, Company
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.models.extension_models import ExtensionDiscoveryEvent
from app.services.discovery_processor import DiscoveryProcessor, run_batch_processor

def run_pipeline_check_1():
    print("=" * 80)
    print("PIPELINE CHECK 1: INGESTION BUFFER, BATCH CLUSTERING & IDENTITY RESOLUTION")
    print("=" * 80)

    # In-memory clean test database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test user
    test_user = User(
        email="recruiter@talentops.ai",
        password_hash="hashed_pw_test",
        first_name="Alex",
        last_name="Mercer",
        status="active",
    )
    session.add(test_user)
    session.flush()
    user_id = test_user.id
    print(f"[Step 1/5] Initialized test user (ID={user_id})")

    # Step 1: Push 3 raw observations into DiscoveryStaging
    # Observations 1 & 2 are from the same person (Dr. Aris Thorne), observation 3 is a different person
    print("\n[Step 2/5] Ingesting 3 raw observation records into discovery_staging buffer...")
    batch_uuid = f"BATCH-{secrets.token_hex(4).upper()}"
    
    obs1 = DiscoveryStaging(
        batch_id=batch_uuid,
        discovery_id=f"DISC-{secrets.token_hex(4).upper()}",
        session_id="SESS-001",
        device_id="DEV-SCOUT-01",
        owner_user_id=user_id,
        raw_name="Dr. Aris Thorne",
        raw_title="VP of Autonomous Systems",
        raw_company="Apex Robotics",
        raw_email="aris.thorne@apexrobotics.io",
        raw_linkedin="https://www.linkedin.com/in/aris-thorne-robotics",
        raw_location="Boston, MA",
        source_url="https://www.linkedin.com/in/aris-thorne-robotics/",
        extraction_source="visual_dom_fusion",
        processing_status="pending",
    )
    obs2 = DiscoveryStaging(
        batch_id=batch_uuid,
        discovery_id=f"DISC-{secrets.token_hex(4).upper()}",
        session_id="SESS-001",
        device_id="DEV-SCOUT-01",
        owner_user_id=user_id,
        raw_name="Aris Thorne",
        raw_title="VP Autonomous Systems & Robotics",
        raw_company="Apex Robotics",
        raw_email="aris.thorne@apexrobotics.io",
        raw_linkedin="https://www.linkedin.com/in/aris-thorne-robotics/",
        raw_phone="+1-617-555-0199",
        raw_location="Boston, Massachusetts",
        source_url="https://www.linkedin.com/in/aris-thorne-robotics/",
        extraction_source="visual_ocr_stream",
        processing_status="pending",
    )
    obs3 = DiscoveryStaging(
        batch_id=batch_uuid,
        discovery_id=f"DISC-{secrets.token_hex(4).upper()}",
        session_id="SESS-002",
        device_id="DEV-SCOUT-02",
        owner_user_id=user_id,
        raw_name="Maya Lin",
        raw_title="Staff ML Platform Engineer",
        raw_company="Apex Robotics",
        raw_email="maya.lin@apexrobotics.io",
        raw_linkedin="https://www.linkedin.com/in/maya-lin-ml",
        source_url="https://www.linkedin.com/in/maya-lin-ml/",
        extraction_source="visual_dom_fusion",
        processing_status="pending",
    )

    session.add_all([obs1, obs2, obs3])
    session.commit()
    print(f"-> 3 pending observations staged in batch {batch_uuid}.")

    # Step 2: Run Batch Processor
    print("\n[Step 3/5] Executing DiscoveryProcessor.process_pending_batch()...")
    processor = DiscoveryProcessor(db=session)
    stats = processor.process_pending_batch()
    print(f"-> Batch processing results: {stats}")

    assert stats["processed"] == 3, f"Expected 3 processed, got {stats['processed']}"
    assert stats["new"] >= 2, f"Expected at least 2 new entities created, got {stats['new']}"

    # Step 3: Verify Clustering into ResolvedPerson
    print("\n[Step 4/5] Verifying cluster resolution in resolved_persons table...")
    resolved = session.query(ResolvedPerson).all()
    print(f"-> Total resolved persons formed: {len(resolved)}")
    assert len(resolved) == 2, f"Expected exactly 2 resolved entities (Aris and Maya), got {len(resolved)}"

    aris_resolved = session.query(ResolvedPerson).filter(ResolvedPerson.canonical_name.ilike("%Aris%")).first()
    assert aris_resolved is not None, "Aris Thorne was not resolved!"
    assert aris_resolved.observation_count == 2, f"Expected 2 observations clustered for Aris, got {aris_resolved.observation_count}"
    assert aris_resolved.primary_phone == "+1-617-555-0199", "Phone from observation 2 was not enriched into Aris!"
    assert aris_resolved.identity_confidence >= 0.85, f"Expected >= 0.85 confidence, got {aris_resolved.identity_confidence}"
    print(f"   [OK] Clustered {aris_resolved.observation_count} observations into: {aris_resolved.canonical_name}")
    print(f"        Title: {aris_resolved.current_title}")
    print(f"        Company: {aris_resolved.current_company}")
    print(f"        Email: {aris_resolved.primary_email}")
    print(f"        Phone: {aris_resolved.primary_phone} (Enriched across frames)")
    print(f"        Confidence: {aris_resolved.identity_confidence:.2f}")

    # Step 4: Verify Master DB Commit & Audit Logging
    print("\n[Step 5/5] Verifying Master Database Recruiters & Audit Ledger...")
    recruiters = session.query(Recruiter).all()
    print(f"-> Total recruiters committed to master DB: {len(recruiters)}")
    assert len(recruiters) == 2, f"Expected 2 recruiters in master table, got {len(recruiters)}"

    audit_events = session.query(ExtensionDiscoveryEvent).all()
    print(f"-> Audit discovery events logged: {len(audit_events)}")
    assert len(audit_events) == 2, f"Expected 2 audit events, got {len(audit_events)}"
    for ae in audit_events:
        print(f"   [OK] Event {ae.id}: action={ae.db_action}, candidate='{ae.recruiter_name}', company='{ae.company_name}'")

    print("\n" + "=" * 80)
    print("PIPELINE CHECK 1 RESULT: PASSED (100% SUCCESSFUL)")
    print("Staging buffer, multi-observation clustering, and DB commits fully verified.")
    print("=" * 80)
    session.close()

if __name__ == "__main__":
    run_pipeline_check_1()
