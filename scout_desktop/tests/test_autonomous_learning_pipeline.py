"""
scout_desktop/tests/test_autonomous_learning_pipeline.py — Verification of Autonomous Self-Learning Pipeline

Validates the full 3-pillar loop without human intervention:
Check 1: Edge Shadow Learner harvests ambiguous entity from screen context & transmits batch to backend.
Check 2: Autonomous Cloud AI Teacher adjudicates ground truth and auto-promotes entity to KnowledgeEntity graph.
Check 3: Fleet sync serves delta to Desktop Scout, dynamically injecting into DYNAMIC_CORPS for 0.99 confidence perception without restart.
"""

import sys
import os
import time
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scout_desktop.extractor.patterns import (
    classify_semantic_entity,
    register_learned_entity,
    DYNAMIC_CORPS,
    get_learned_entities_stats,
)
from scout_desktop.sync.shadow_learner import ShadowLearner
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.knowledge_models import KnowledgeEntity
from backend.app.services.autonomous_teacher_service import AutonomousTeacherService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_rule11_check1_edge_shadow_harvesting_and_ingestion(client):
    """
    CHECK 1 (Edge Shadow Learner Harvesting & API Ingestion):
    Verifies that an unconfirmed/ambiguous novel company is captured by the edge
    shadow learner with spatial context and successfully ingested into the cloud learning queue.
    """
    novel_company = "NovaSphere Dynamics"
    novel_norm = novel_company.lower().strip()

    # Ensure clean starting state: not in dynamic set
    DYNAMIC_CORPS.discard(novel_norm)

    # 1. Verify baseline perception: not recognized as verified dynamic entity
    baseline_classification = classify_semantic_entity(novel_company)
    assert baseline_classification.get("source") != "DYNAMIC_CLOUD_LEARNED", (
        f"Pre-condition failed: '{novel_company}' was already dynamically learned"
    )

    # 2. Simulate Desktop Scout capturing screen context with ambiguous company
    learner = ShadowLearner(max_buffer_size=50)
    context_lines = [
        "NovaSphere Dynamics",
        "Principal Systems Architect",
        "Cambridge, MA · Hybrid",
        "Experience: 8 yrs",
        "Skills: Distributed Systems, Rust, Python",
    ]

    buffered = learner.inspect_and_buffer(
        candidate_text=novel_company,
        entity_type="COMPANY",
        confidence=0.75,  # Ambiguous/borderline threshold
        context_lines=context_lines,
        source_url="https://www.linkedin.com/in/alex-mercer-systems",
        window_title="Alex Mercer | LinkedIn",
    )
    assert buffered is True, "ShadowLearner should buffer ambiguous entity"
    assert learner.buffer_size == 1, "ShadowLearner buffer size should be 1"

    pending = learner.get_pending_batch(max_items=10)
    assert len(pending) == 1
    assert pending[0]["candidate_text"] == novel_company
    assert len(pending[0]["content_hash"]) > 0

    # 3. Test API ingestion endpoint
    payload = {
        "device_id": "SCOUT-TEST-NODE-01",
        "scout_version": "2.9.2",
        "observations": pending,
    }
    response = client.post("/scout/learning/ingest-ambiguities", json=payload)
    assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["adjudicated"] >= 1
    assert data["promoted_to_knowledge_graph"] >= 1

    print(f"\n[CHECK 1 PROOF] Successfully harvested '{novel_company}' with {len(context_lines)} context lines")
    print(f"[CHECK 1 PROOF] Ingested by /scout/learning/ingest-ambiguities: {data}")


def test_rule11_check2_autonomous_cloud_ai_teacher_adjudication(db_session):
    """
    CHECK 2 (Autonomous Cloud AI Teacher Adjudication & Promotion):
    Verifies that the Cloud AI Teacher adjudicates the true semantic category
    from raw spatial context and auto-promotes to KnowledgeEntity without human intervention.
    """
    novel_company = "Aetheris Technologies"
    context = [
        "Aetheris Technologies",
        "Staff Infrastructure Engineer",
        "San Jose, CA",
        "About the company: Building next-generation telemetry systems",
    ]

    # Clean any prior test artifacts
    db_session.query(KnowledgeEntity).filter(
        KnowledgeEntity.canonical_name.ilike(novel_company)
    ).delete(synchronize_session=False)
    db_session.commit()

    # Execute Autonomous Teacher Adjudication
    adjudication = AutonomousTeacherService.adjudicate_observation(
        candidate_text=novel_company,
        context_lines=context,
        source_url="https://www.linkedin.com/in/sample-profile",
        window_title="Sample Profile | LinkedIn",
        owner_user_id=1,
        db=db_session,
    )

    assert adjudication["entity_type"] == "COMPANY", f"Expected COMPANY, got {adjudication['entity_type']}"
    assert adjudication["confidence"] >= 0.90, f"Confidence {adjudication['confidence']} should be >= 0.90"
    assert adjudication["promoted_id"] is not None, "Entity should be auto-promoted to KnowledgeEntity"

    # Verify database persistence
    persisted = db_session.query(KnowledgeEntity).filter(
        KnowledgeEntity.id == adjudication["promoted_id"]
    ).first()
    assert persisted is not None, "Promoted entity not found in database"
    assert persisted.canonical_name.lower() == novel_company.lower()
    assert persisted.entity_type == "COMPANY"

    print(f"\n[CHECK 2 PROOF] Autonomous Teacher Adjudicated: {adjudication}")
    print(f"[CHECK 2 PROOF] KnowledgeEntity ID #{persisted.id} auto-promoted into Canonical Graph: '{persisted.canonical_name}'")


def test_rule11_check3_fleet_delta_sync_and_live_perception(client):
    """
    CHECK 3 (Fleet Delta Sync & Zero-Restart Perception Update):
    Verifies that Desktop Scout queries knowledge deltas, dynamically injects the
    new entity into live memory without restarting, and immediately re-evaluates with 0.99 confidence.
    """
    novel_entity = "Vortex AI Solutions"
    norm_entity = novel_entity.lower().strip()

    # Pre-condition: not known dynamically
    DYNAMIC_CORPS.discard(norm_entity)

    # 1. Seed into KnowledgeEntity graph as verified entity
    db = SessionLocal()
    try:
        existing = db.query(KnowledgeEntity).filter(
            KnowledgeEntity.canonical_name.ilike(novel_entity)
        ).first()
        if not existing:
            ent = KnowledgeEntity(
                owner_user_id=1,
                entity_type="COMPANY",
                canonical_name=novel_entity,
                confidence=0.96,
                source_url="https://talentops.ai/fleet",
            )
            db.add(ent)
            db.commit()
            db.refresh(ent)
    finally:
        db.close()

    # 2. Fetch fleet knowledge deltas via API
    response = client.get("/scout/fleet/sync-knowledge?since=0.0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    entities = data["entities"]
    assert any(e["canonical_name"].lower() == norm_entity for e in entities), (
        f"'{novel_entity}' was not in fleet sync payload: {entities}"
    )

    # 3. Simulate Desktop Scout dynamic registration into local runtime sets
    learned_count = 0
    for e in entities:
        if register_learned_entity(e["entity_type"], e["canonical_name"]):
            learned_count += 1

    assert learned_count >= 1, "At least one entity should have been dynamically learned"
    assert norm_entity in DYNAMIC_CORPS, f"'{norm_entity}' must be in DYNAMIC_CORPS"

    # 4. CRITICAL ZERO-RESTART RE-PERCEPTION CHECK:
    # classify_semantic_entity must instantly perceive this entity with 0.99 confidence
    # and attribution source DYNAMIC_CLOUD_LEARNED on device WITHOUT application restart!
    re_perceived = classify_semantic_entity(novel_entity)
    assert re_perceived["entity_type"] == "COMPANY", f"Expected COMPANY, got {re_perceived}"
    assert re_perceived["confidence"] == 0.99, f"Expected 0.99, got {re_perceived['confidence']}"
    assert re_perceived["source"] == "DYNAMIC_CLOUD_LEARNED", f"Expected DYNAMIC_CLOUD_LEARNED, got {re_perceived['source']}"

    stats = get_learned_entities_stats()
    assert stats["corps_count"] >= 1

    print(f"\n[CHECK 3 PROOF] Fleet Delta Sync successfully received {len(entities)} entities")
    print(f"[CHECK 3 PROOF] Runtime Dynamic Stats: {stats}")
    print(f"[CHECK 3 PROOF] Instant Re-Perception Result: {re_perceived}")
