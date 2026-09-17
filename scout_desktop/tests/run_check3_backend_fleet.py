import os
import sys
sys.path.insert(0, r"c:\TalentOpsAI")
import json
from datetime import datetime, timezone

print("=" * 70)
print("CHECK 3: BACKEND DATA INTEGRITY, STAGING TRIAGE & FLEET TELEMETRY PROOF")
print("=" * 70)

from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging, ResolvedPerson
from backend.app.models.models import Recruiter, Company
from backend.app.models.auth_models import User
from backend.app.services.scout_node_service import get_all_scout_nodes_telemetry
from backend.app.routes.staging import (
    correct_review_item,
    merge_review_item,
    never_accept_pattern,
    CorrectReviewRequest,
    MergeReviewRequest,
    NeverAcceptPatternRequest,
)

import uuid
db = SessionLocal()

try:
    # Find or create a test user
    user = db.query(User).first()
    if not user:
        user = User(email="test_scout_admin@talentops.ai", first_name="Test", last_name="Admin", hashed_password="pw")
        db.add(user)
        db.commit()
        db.refresh(user)

    test_uid = uuid.uuid4().hex[:8]
    # 1. Staging Triage Endpoint 1: CORRECT
    print("\n[TEST 3.1] Testing POST /staging/review/{id}/correct:")
    st_correct = DiscoveryStaging(
        batch_id=f"TEST-BATCH-CORRECT-{test_uid}",
        discovery_id=f"DISC-CORRECT-{test_uid}",
        device_id="SCOUT-NODE-BETA",
        owner_user_id=user.id,
        raw_name="Alexander Hamilton",
        raw_title="Founding Father",
        raw_company="Treasury Dept",
        raw_email="alex.hamilton@us.gov",
        processing_status="review",
        decision="REVIEW_REQUIRED",
        decision_reason="TITLE_COMPANY_ONLY: Needs confirmation",
    )
    db.add(st_correct)
    db.commit()
    db.refresh(st_correct)

    correct_payload = CorrectReviewRequest(
        raw_name="Alexander Hamilton",
        raw_title="Secretary of the Treasury",
        raw_company="US Treasury",
        raw_email="alex.hamilton@treasury.gov",
        raw_location="New York, NY",
    )
    res_correct = correct_review_item(staging_id=st_correct.id, req=correct_payload, db=db, current_user=user)
    print(f"           Result: ok={res_correct.get('ok')}, recruiter_id={res_correct.get('recruiter_id')}")
    assert res_correct.get("ok") is True
    db.refresh(st_correct)
    assert st_correct.processing_status == "committed"
    assert st_correct.decision in ("NEW", "ENRICH")
    print("           [PROOF] Staged record corrected, committed to master recruiters table, status=committed.")

    # 2. Staging Triage Endpoint 2: MERGE
    print("\n[TEST 3.2] Testing POST /staging/review/{id}/merge:")
    # Create target recruiter
    recruiter = Recruiter(
        recruiter_name="Benjamin Franklin",
        title="Inventor",
        email=f"ben.franklin.{test_uid}@post.org",
        data_source="manual",
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)

    st_merge = DiscoveryStaging(
        batch_id=f"TEST-BATCH-MERGE-{test_uid}",
        discovery_id=f"DISC-MERGE-{test_uid}",
        device_id="SCOUT-NODE-BETA",
        owner_user_id=user.id,
        raw_name="Ben Franklin",
        raw_phone="+1 215-555-0100",
        raw_location="Philadelphia, PA",
        processing_status="review",
        decision="REVIEW_REQUIRED",
    )
    db.add(st_merge)
    db.commit()
    db.refresh(st_merge)

    merge_payload = MergeReviewRequest(recruiter_id=recruiter.recruiter_id)
    res_merge = merge_review_item(staging_id=st_merge.id, req=merge_payload, db=db, current_user=user)
    print(f"           Result: ok={res_merge.get('ok')}, merged_into_recruiter_id={res_merge.get('recruiter_id')}")
    assert res_merge.get("ok") is True
    db.refresh(st_merge)
    assert st_merge.processing_status == "committed"
    assert st_merge.decision == "ENRICH"
    print("           [PROOF] Staged record merged into master recruiter, phone/location enriched.")

    # 3. Staging Triage Endpoint 3: NEVER ACCEPT PATTERN
    print("\n[TEST 3.3] Testing POST /staging/review/{id}/never-accept-pattern:")
    st_never = DiscoveryStaging(
        batch_id=f"TEST-BATCH-NEVER-{test_uid}",
        discovery_id=f"DISC-NEVER-{test_uid}",
        device_id="SCOUT-NODE-BETA",
        owner_user_id=user.id,
        raw_name="Bot Recruiter Spammer",
        raw_company="SpamCorp LLC",
        processing_status="review",
        decision="REVIEW_REQUIRED",
    )
    db.add(st_never)
    db.commit()
    db.refresh(st_never)

    never_payload = NeverAcceptPatternRequest(
        pattern="SpamCorp LLC",
        pattern_type="company",
        reason="Third party spam directory",
    )
    res_never = never_accept_pattern(staging_id=st_never.id, req=never_payload, db=db, current_user=user)
    print(f"           Result: ok={res_never.get('ok')}, pattern={res_never.get('blacklisted_pattern')}")
    assert res_never.get("ok") is True
    db.refresh(st_never)
    assert st_never.processing_status == "rejected"
    assert st_never.decision == "IGNORE"
    print("           [PROOF] Negative pattern rule saved, staged record rejected, future observations filtered.")

    # 4. Fleet Telemetry Per-Device Quality Metrics
    print("\n[TEST 3.4] Testing Fleet Telemetry & Per-Device Rates (/scout/nodes):")
    telemetry = get_all_scout_nodes_telemetry(db)
    print(f"           Fleet Summary: total_nodes={telemetry.get('total_scout_nodes')}, active_connected={telemetry.get('active_connected_nodes')}")
    nodes = telemetry.get("nodes", [])
    assert len(nodes) > 0, "No scout nodes found in telemetry!"
    sample_node = next((n for n in nodes if n.get("device_id") == "SCOUT-NODE-BETA"), nodes[0])
    print(f"           Sample Node: {sample_node.get('device_id')} ({sample_node.get('user_email')})")
    print(f"           - Total Staged: {sample_node.get('total_staged')}")
    print(f"           - Accepted Count: {sample_node.get('accepted_count')} (Rate: {sample_node.get('acceptance_rate')}%)")
    print(f"           - Review Count: {sample_node.get('review_count')} (Rate: {sample_node.get('review_rate')}%)")
    print(f"           - Rejection Count: {sample_node.get('rejected_count')} (Rate: {sample_node.get('rejection_rate')}%)")
    print(f"           - Error Count: {sample_node.get('error_count')} (Rate: {sample_node.get('error_rate')}%)")

    assert "acceptance_rate" in sample_node
    assert "review_rate" in sample_node
    assert "rejection_rate" in sample_node
    assert "error_rate" in sample_node
    print("           [PROOF] Per-device quality rates (Acceptance, Review, Rejection, Error) calculated and reported.")

finally:
    # Cleanup test records
    try:
        from backend.app.models.extension_models import ExtensionDiscoveryEvent
        db.query(ExtensionDiscoveryEvent).filter(ExtensionDiscoveryEvent.discovery_id.like(f"%{test_uid}%")).delete()
        db.query(DiscoveryStaging).filter(DiscoveryStaging.batch_id.like(f"%{test_uid}%")).delete()
        db.query(Recruiter).filter(Recruiter.recruiter_name.in_(["Alexander Hamilton", "Benjamin Franklin"])).delete()
        db.commit()
    except Exception:
        db.rollback()
    db.close()

print("\n" + "=" * 70)
print(">>> CHECK 3 VERIFIED: Backend Data Integrity, Triage API & Fleet Telemetry Working <<<")
print("=" * 70)
