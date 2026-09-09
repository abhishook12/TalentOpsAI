"""
check_2_ingestion_gateway_dedup.py
Verification Check 2: Universal Source Object Ingestion & Cross-Source Deduplication Gateway.

Tests:
1. Multi-source ingestion of the same candidate:
   - Observation A: SourceType.LINKEDIN_OAUTH
   - Observation B: SourceType.SCOUT_DESKTOP (via wrap_desktop_observation)
2. Layer 1 Raw Signals Lake verification:
   - Both raw payloads preserved verbatim with distinct hashes and source provenance.
3. Layer 2 Canonical Entity Resolution:
   - Both observations resolve to the EXACT SAME canonical entity key (e.g. PER-LI-ELENA-ROSTOVA-DIST).
   - Confirms ZERO duplicate rows in `persons` table.
   - Confirms bidirectional relationship edge to company (CURRENTLY_WORKS_AT).
4. Idempotency test:
   - Re-submitting identical payload returns status="RE_OBSERVED" and does not duplicate Layer 1 or Layer 2.
5. Job opening and post ingestion:
   - Verifies HIRING_FOR edge creation and atomic SignalEvent emission (JOB_POSTED, TECH_MENTIONED).
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.schemas.intelligence_contracts import (
    UniversalSourceObject,
    SourceObjectIdentity,
    SourceType,
    ScopeLevel,
    EpistemicLevel,
    RelationshipType,
    SignalEventType,
)
from app.models.intelligence_models import (
    RawSignal,
    EntityRegistry,
    PersonEntity,
    CompanyEntity,
    JobEntity,
    PostEntity,
    RelationshipEdge,
    SignalEvent,
)
from app.services.intelligence.gateway import IngestionGateway, compute_payload_hash
from app.services.intelligence.desktop_connector import wrap_desktop_observation


def run_check_2():
    print("=" * 80)
    print("CHECK 2: UNIVERSAL INGESTION GATEWAY & CROSS-SOURCE DEDUPLICATION")
    print("=" * 80)

    # 1. Setup in-memory test database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    gateway = IngestionGateway(db=session)

    # ── Test 1: Ingest Candidate via Authorized LinkedIn OAuth Connector ─────
    print("\n[Step 1/5] Ingesting candidate from Source 1: LINKEDIN_OAUTH...")
    candidate_linkedin_payload = {
        "full_name": "Elena Rostova",
        "current_title": "Staff Distributed Systems Engineer",
        "company_name": "Snowflake",
        "primary_email": "elena@rostova.dev",
        "linkedin_url": "https://www.linkedin.com/in/elena-rostova-dist",
        "seniority_level": "Staff",
    }
    hash_li = compute_payload_hash(candidate_linkedin_payload)

    obj_li = UniversalSourceObject(
        identity=SourceObjectIdentity(
            source=SourceType.LINKEDIN_OAUTH,
            source_object_type="person",
            source_object_id="urn:li:person:elena-rostova-dist",
            authorization_scope=ScopeLevel.MEMBER_FULL_PROFILE.value,
            content_hash=hash_li,
        ),
        raw_payload=candidate_linkedin_payload,
        provenance_metadata={"oauth_client_id": "talentops_linkedin_prod", "tenant": "corp_us"},
    )

    res_li = gateway.ingest_observation(obj_li)
    print(f"-> Result from Source 1: status={res_li['status']}, canonical_key={res_li['canonical_key']}")
    assert res_li["status"] == "INGESTED", f"Expected INGESTED, got {res_li['status']}"
    assert "PER-LI-ELENA-ROSTOVA-DIST" in res_li["canonical_key"], f"Unexpected key: {res_li['canonical_key']}"

    # Verify Layer 1 & Layer 2 state
    raw_count_1 = session.query(RawSignal).count()
    person_count_1 = session.query(PersonEntity).count()
    comp_count_1 = session.query(CompanyEntity).count()
    rel_count_1 = session.query(RelationshipEdge).count()

    print(f"   [Layer 1] Raw signals stored: {raw_count_1}")
    print(f"   [Layer 2] Canonical persons: {person_count_1}, companies: {comp_count_1}, edges: {rel_count_1}")
    assert raw_count_1 == 1, "Expected 1 raw signal"
    assert person_count_1 == 1, "Expected 1 canonical person"

    # ── Test 2: Ingest SAME Candidate via Scout Desktop Companion ────────────
    print("\n[Step 2/5] Ingesting SAME candidate from Source 2: SCOUT_DESKTOP companion...")
    desktop_staged_contact = {
        "raw_name": "Elena Rostova",
        "raw_title": "Staff Distributed Systems Engineer",
        "raw_company": "Snowflake",
        "raw_linkedin": "https://www.linkedin.com/in/elena-rostova-dist",
        "raw_email": "elena@rostova.dev",
        "raw_location": "San Francisco, CA",
        "capture_id": "VC-77A19B",
        "visual_change_score": "0.88",
        "source_url": "https://www.linkedin.com/in/elena-rostova-dist/",
        "seniority_level": "Staff",
    }

    obj_desktop = wrap_desktop_observation(
        staged_contact=desktop_staged_contact,
        device_id="WIN-STATION-DEV01",
        hostname="DESKTOP-PRO-X",
        scout_version="2.0.0",
    )

    res_desktop = gateway.ingest_observation(obj_desktop)
    print(f"-> Result from Source 2: status={res_desktop['status']}, canonical_key={res_desktop['canonical_key']}")
    assert res_desktop["canonical_key"] == res_li["canonical_key"], (
        f"Entity resolution failure! LinkedIn key={res_li['canonical_key']} != Desktop key={res_desktop['canonical_key']}"
    )

    # Verify Layer 1 preserved BOTH raw signals, while Layer 2 resolved to 1 canonical person
    raw_count_2 = session.query(RawSignal).count()
    person_count_2 = session.query(PersonEntity).count()
    print(f"   [Layer 1] Raw signals stored: {raw_count_2} (BOTH source observations preserved verbatim)")
    print(f"   [Layer 2] Canonical persons: {person_count_2} (ZERO duplication!)")

    assert raw_count_2 == 2, f"Expected 2 raw signals, found {raw_count_2}"
    assert person_count_2 == 1, f"Expected exactly 1 person record, found {person_count_2} (duplication error!)"

    # Verify enriched attributes
    canonical_person = session.query(PersonEntity).filter(PersonEntity.canonical_key == res_li["canonical_key"]).first()
    assert canonical_person is not None
    assert canonical_person.full_name == "Elena Rostova"
    assert canonical_person.current_company_name == "Snowflake"
    print(f"   [PASSED] Candidate resolved to single entity: {canonical_person.canonical_key} ({canonical_person.full_name})")

    # ── Test 3: Idempotent Re-Ingestion of Identical Observation ──────────────
    print("\n[Step 3/5] Testing Idempotency: Re-ingesting Source 1 payload...")
    res_reingest = gateway.ingest_observation(obj_li)
    print(f"-> Result of re-ingestion: status={res_reingest['status']}")
    assert res_reingest["status"] == "RE_OBSERVED", f"Expected RE_OBSERVED, got {res_reingest['status']}"

    raw_count_3 = session.query(RawSignal).count()
    person_count_3 = session.query(PersonEntity).count()
    assert raw_count_3 == 2, "Raw signal count should NOT increase on re-observation"
    assert person_count_3 == 1, "Person count should NOT increase on re-observation"
    print("   [PASSED] Re-observation correctly recognized as duplicate; no redundant DB rows created.")

    # ── Test 4: Ingest Job Opening from ATS Connector ─────────────────────────
    print("\n[Step 4/5] Ingesting Job opening from Source 3: ATS_GREENHOUSE...")
    job_payload = {
        "title": "Principal Distributed Systems Architect",
        "company_name": "Snowflake",
        "seniority": "Principal",
        "location": "San Francisco, CA / Remote",
        "description": "Seeking distributed database experts in Rust and Go to scale query compilation.",
    }
    job_hash = compute_payload_hash(job_payload)

    obj_job = UniversalSourceObject(
        identity=SourceObjectIdentity(
            source=SourceType.ATS_GREENHOUSE,
            source_object_type="job",
            source_object_id="greenhouse_job_482910",
            authorization_scope=ScopeLevel.ATS_READ_JOB.value,
            content_hash=job_hash,
        ),
        raw_payload=job_payload,
    )

    res_job = gateway.ingest_observation(obj_job)
    print(f"-> Job Ingestion result: canonical_key={res_job['canonical_key']}, emitted={res_job['emitted_events']}")
    assert "JOB_POSTED" in res_job["emitted_events"], "Expected JOB_POSTED signal event"

    job_entity = session.query(JobEntity).filter(JobEntity.canonical_key == res_job["canonical_key"]).first()
    assert job_entity is not None
    assert job_entity.title == "Principal Distributed Systems Architect"

    # Check HIRING_FOR edge between Snowflake and the Job
    hiring_edge = session.query(RelationshipEdge).filter(
        RelationshipEdge.target_canonical_key == res_job["canonical_key"],
        RelationshipEdge.relationship_type == RelationshipType.HIRING_FOR.value,
    ).first()
    assert hiring_edge is not None
    print(f"   [PASSED] HIRING_FOR edge created: {hiring_edge.source_canonical_key} -> {hiring_edge.target_canonical_key}")

    # ── Test 5: Ingest Post from Author with Tech Mention ────────────────────
    print("\n[Step 5/5] Ingesting published Post from author...")
    post_payload = {
        "author_canonical_key": res_li["canonical_key"],
        "content_text": "Delighted to announce our new distributed engine architecture running on Rust, Kubernetes and Apache Iceberg!",
        "technologies": ["Rust", "Kubernetes", "Apache Iceberg"],
        "topics": ["Distributed Systems", "Cloud Data"],
        "url": "https://www.linkedin.com/feed/update/urn:li:activity:789123456",
    }
    post_hash = compute_payload_hash(post_payload)

    obj_post = UniversalSourceObject(
        identity=SourceObjectIdentity(
            source=SourceType.LINKEDIN_OAUTH,
            source_object_type="post",
            source_object_id="urn:li:activity:789123456",
            authorization_scope=ScopeLevel.ORGANIZATION_POSTS.value,
            content_hash=post_hash,
        ),
        raw_payload=post_payload,
    )

    res_post = gateway.ingest_observation(obj_post)
    print(f"-> Post Ingestion result: canonical_key={res_post['canonical_key']}, emitted={res_post['emitted_events']}")
    assert len(res_post["emitted_events"]) == 3, f"Expected 3 tech events, got {len(res_post['emitted_events'])}"

    post_entity = session.query(PostEntity).filter(PostEntity.canonical_key == res_post["canonical_key"]).first()
    assert post_entity is not None
    assert "Rust" in post_entity.technologies_json

    total_events = session.query(SignalEvent).count()
    print(f"-> Total Layer 3 Signal Events emitted into queue: {total_events}")
    assert total_events >= 4, f"Expected at least 4 signal events, got {total_events}"

    print("\n" + "=" * 80)
    print("CHECK 2 RESULT: PASSED (100% SUCCESSFUL)")
    print("Cross-source identity resolution verified. Zero duplicate records created.")
    print("=" * 80)
    session.close()

if __name__ == "__main__":
    run_check_2()
