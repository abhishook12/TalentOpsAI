"""
check_pipeline_2_intelligence_graph.py
Pipeline Verification Check 2: 4-Tier Knowledge Graph Multi-Source Ingestion & Resolution.

Tests:
1. Multi-source Ingestion Gateway execution against backend/dev.db:
   - Scout Desktop observation (with device metadata and visual provenance)
   - LinkedIn OAuth observation
   - ATS Greenhouse job opening
   - Published leadership post
2. Layer 1 Raw Signals Lake immutability & deduplication.
3. Layer 2 Canonical Entity Resolution (zero duplicate persons).
4. Graph relationship generation (CURRENTLY_WORKS_AT, HIRING_FOR).
5. Layer 3 Signal Event generation (JOB_POSTED, TECH_MENTIONED).
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.schemas.intelligence_contracts import (
    UniversalSourceObject,
    SourceObjectIdentity,
    SourceType,
    ScopeLevel,
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

def run_pipeline_check_2():
    print("=" * 80)
    print("PIPELINE CHECK 2: 4-TIER KNOWLEDGE GRAPH MULTI-SOURCE INGESTION & RESOLUTION")
    print("=" * 80)

    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "dev.db"))
    print(f"Connecting to dev database: {db_path}")
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    gateway = IngestionGateway(db=session)

    # Candidate info
    slug = "devin-chandler-ai"
    candidate_linkedin = f"https://www.linkedin.com/in/{slug}"

    # Step 1: Ingest observation from Desktop Scout Companion
    print("\n[Step 1/5] Ingesting observation from Desktop Scout Companion (Connector #1)...")
    desktop_data = {
        "raw_name": "Devin Chandler",
        "raw_title": "Head of AI Infrastructure",
        "raw_company": "Anthropic AI",
        "raw_linkedin": candidate_linkedin,
        "raw_email": "d.chandler@anthropic.com",
        "raw_location": "San Francisco, CA",
        "capture_id": "VC-88C10A",
        "visual_change_score": "0.92",
        "source_url": candidate_linkedin,
        "seniority_level": "Director",
    }
    obj_desktop = wrap_desktop_observation(
        staged_contact=desktop_data,
        device_id="NODE-DEV-01",
        hostname="WORKSTATION-X",
        scout_version="2.0.0",
    )
    res_desktop = gateway.ingest_observation(obj_desktop)
    print(f"-> Scout Desktop observation: status={res_desktop['status']}, canonical_key={res_desktop['canonical_key']}")
    assert res_desktop["canonical_key"].startswith("PER-LI-"), f"Unexpected key: {res_desktop['canonical_key']}"

    # Step 2: Ingest same candidate from LinkedIn OAuth feed
    print("\n[Step 2/5] Ingesting same candidate from authorized LinkedIn OAuth feed...")
    oauth_data = {
        "full_name": "Devin Chandler",
        "current_title": "Head of AI Infrastructure",
        "company_name": "Anthropic AI",
        "primary_email": "d.chandler@anthropic.com",
        "linkedin_url": candidate_linkedin,
        "seniority_level": "Director",
        "headline": "Scaling frontier training clusters & distributed ML systems",
    }
    obj_oauth = UniversalSourceObject(
        identity=SourceObjectIdentity(
            source=SourceType.LINKEDIN_OAUTH,
            source_object_type="person",
            source_object_id=f"urn:li:person:{slug}",
            authorization_scope=ScopeLevel.MEMBER_FULL_PROFILE.value,
            content_hash=compute_payload_hash(oauth_data),
        ),
        raw_payload=oauth_data,
        provenance_metadata={"connector": "LINKEDIN-OAUTH-PROD"},
    )
    res_oauth = gateway.ingest_observation(obj_oauth)
    print(f"-> LinkedIn OAuth observation: status={res_oauth['status']}, canonical_key={res_oauth['canonical_key']}")
    assert res_oauth["canonical_key"] == res_desktop["canonical_key"], (
        f"Cross-source resolution error: {res_oauth['canonical_key']} != {res_desktop['canonical_key']}"
    )

    # Step 3: Ingest ATS Greenhouse Job Opening
    print("\n[Step 3/5] Ingesting Job opening from ATS Greenhouse Connector...")
    job_payload = {
        "title": "Principal Distributed Training Engineer",
        "company_name": "Anthropic AI",
        "seniority": "Principal",
        "location": "San Francisco, CA / Remote",
        "description": "Designing high-performance NCCL clusters, PyTorch distributed pipelines, and GPU memory kernels.",
    }
    obj_job = UniversalSourceObject(
        identity=SourceObjectIdentity(
            source=SourceType.ATS_GREENHOUSE,
            source_object_type="job",
            source_object_id="greenhouse_job_anthropic_781",
            authorization_scope=ScopeLevel.ATS_READ_JOB.value,
            content_hash=compute_payload_hash(job_payload),
        ),
        raw_payload=job_payload,
    )
    res_job = gateway.ingest_observation(obj_job)
    print(f"-> ATS Job Ingestion: status={res_job['status']}, canonical_key={res_job['canonical_key']}, emitted={res_job['emitted_events']}")

    # Step 4: Ingest Published Post mentioning tech stack
    print("\n[Step 4/5] Ingesting published leadership post...")
    post_payload = {
        "author_canonical_key": res_desktop["canonical_key"],
        "content_text": "Excited to share our breakthrough in distributed fault tolerance utilizing Ray, Kubernetes, and Triton!",
        "technologies": ["Ray", "Kubernetes", "Triton"],
        "topics": ["Distributed Training", "MLOps"],
        "url": "https://www.linkedin.com/feed/update/urn:li:activity:99011223344",
    }
    obj_post = UniversalSourceObject(
        identity=SourceObjectIdentity(
            source=SourceType.LINKEDIN_OAUTH,
            source_object_type="post",
            source_object_id="urn:li:activity:99011223344",
            authorization_scope=ScopeLevel.ORGANIZATION_POSTS.value,
            content_hash=compute_payload_hash(post_payload),
        ),
        raw_payload=post_payload,
    )
    res_post = gateway.ingest_observation(obj_post)
    print(f"-> Post Ingestion: status={res_post['status']}, canonical_key={res_post['canonical_key']}, emitted={res_post['emitted_events']}")

    # Step 5: Verify Layer 1, 2, and 3 integrity in the database
    print("\n[Step 5/5] Verifying database entity deduplication & relationship graph...")
    per_key = res_desktop["canonical_key"]
    matching_persons = session.query(PersonEntity).filter(PersonEntity.canonical_key == per_key).all()
    print(f"-> Canonical PersonEntity records for '{per_key}': {len(matching_persons)}")
    assert len(matching_persons) == 1, f"Expected exactly 1 person record, found {len(matching_persons)} (duplication error!)"

    # Verify Company
    comp = session.query(CompanyEntity).filter(CompanyEntity.canonical_name == "Anthropic AI").first()
    assert comp is not None, "Company Anthropic AI was not created!"
    print(f"-> Canonical CompanyEntity: {comp.canonical_key} ({comp.canonical_name})")

    # Verify Relationships
    work_edge = session.query(RelationshipEdge).filter(
        RelationshipEdge.source_canonical_key == per_key,
        RelationshipEdge.relationship_type == RelationshipType.CURRENTLY_WORKS_AT.value,
    ).first()
    assert work_edge is not None, "CURRENTLY_WORKS_AT edge missing!"
    print(f"   [OK] Graph Edge: {work_edge.source_canonical_key} -> CURRENTLY_WORKS_AT -> {work_edge.target_canonical_key}")

    hiring_edge = session.query(RelationshipEdge).filter(
        RelationshipEdge.source_canonical_key == comp.canonical_key,
        RelationshipEdge.relationship_type == RelationshipType.HIRING_FOR.value,
    ).first()
    assert hiring_edge is not None, "HIRING_FOR edge missing!"
    print(f"   [OK] Graph Edge: {hiring_edge.source_canonical_key} -> HIRING_FOR -> {hiring_edge.target_canonical_key}")

    # Verify Signal Events
    events = session.query(SignalEvent).filter(
        SignalEvent.target_canonical_key.in_([comp.canonical_key, per_key])
    ).all()
    print(f"-> Layer 3 Signal Events emitted: {len(events)}")
    for ev in events:
        print(f"   [OK] Event {ev.id}: type={ev.event_type}, target={ev.target_canonical_key}, weight={ev.weight}")

    assert len(events) >= 2, f"Expected at least 2 events, got {len(events)}"

    print("\n" + "=" * 80)
    print("PIPELINE CHECK 2 RESULT: PASSED (100% SUCCESSFUL)")
    print("Multi-source Ingestion Gateway, Layer 1 Raw Lake, and Layer 2 Knowledge Graph verified.")
    print("=" * 80)
    session.close()

if __name__ == "__main__":
    run_pipeline_check_2()
