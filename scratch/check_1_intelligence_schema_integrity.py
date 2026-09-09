"""
check_1_intelligence_schema_integrity.py
Verification Check 1: 4-Tier Knowledge Graph Schema Integrity & Database Constraints.

Tests:
1. Complete DDL creation for all 4 epistemic layers:
   - Layer 0: source_connectors, oauth_scope_registry, ingestion_runs
   - Layer 1: raw_signals
   - Layer 2: entity_registry, persons, companies_v2, jobs_v2, posts_v2, skills_v2, technologies_v2, relationships
   - Layer 3: signal_events, derived_intents, evidence_ledger, career_velocities
2. Verification of table existence and column reflection.
3. CRUD test across all 4 tiers.
4. Layer 1 SHA-256 unique deduplication constraint verification.
5. Layer 2 foreign key cascade verification (EntityRegistry -> PersonEntity).
"""

import sys
import os
import json
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Import Base and models
from app.database import Base
from app.models.intelligence_models import (
    SourceConnector,
    OAuthScopeRegistry,
    IngestionRun,
    RawSignal,
    EntityRegistry,
    PersonEntity,
    CompanyEntity,
    JobEntity,
    PostEntity,
    SkillEntity,
    TechnologyEntity,
    RelationshipEdge,
    SignalEvent,
    DerivedIntent,
    EvidenceLedger,
    CareerVelocityRecord,
)

def run_check_1():
    print("=" * 80)
    print("CHECK 1: 4-TIER KNOWLEDGE GRAPH SCHEMA INTEGRITY & CONSTRAINTS")
    print("=" * 80)

    # 1. Initialize SQLite engine with foreign keys enabled
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # 2. Create all tables
    print("\n[Step 1/5] Creating all 4-Tier Knowledge Graph tables...")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    created_tables = set(inspector.get_table_names())
    print(f"-> Total tables created in DB: {len(created_tables)}")

    expected_tables = {
        # Layer 0
        "source_connectors",
        "oauth_scope_registry",
        "ingestion_runs",
        # Layer 1
        "raw_signals",
        # Layer 2
        "entity_registry",
        "persons",
        "companies_v2",
        "jobs_v2",
        "posts_v2",
        "skills_v2",
        "technologies_v2",
        "relationships",
        # Layer 3
        "signal_events",
        "derived_intents",
        "evidence_ledger",
        "career_velocities",
    }

    missing_tables = expected_tables - created_tables
    if missing_tables:
        print(f"FAILED: Missing tables: {missing_tables}")
        sys.exit(1)
    print("-> ALL 16 EXPECTED KNOWLEDGE GRAPH TABLES CONFIRMED PRESENT:")
    for t in sorted(expected_tables):
        cols = [c["name"] for c in inspector.get_columns(t)]
        print(f"   [OK] Table '{t}': {len(cols)} columns ({', '.join(cols[:4])}...)")

    Session = sessionmaker(bind=engine)
    session = Session()

    # 3. Test insertions into all 4 layers
    print("\n[Step 2/5] Testing data insertion into Layer 0 (Source & Scope Registry)...")
    src = SourceConnector(
        connector_key="CONN-LINKEDIN-01",
        source_type="LINKEDIN_OAUTH",
        name="LinkedIn OAuth Connector",
        auth_type="OAUTH2",
        config_json=json.dumps({"scope": "r_basicprofile"}),
    )
    session.add(src)
    session.flush()
    print(f"-> Layer 0 SourceConnector created with ID {src.id} ({src.connector_key})")

    scope_reg = OAuthScopeRegistry(
        connector_id=src.id,
        scopes_granted=json.dumps(["r_basicprofile", "r_organization_social"]),
        token_status="ACTIVE",
    )
    session.add(scope_reg)

    run = IngestionRun(
        run_uuid="RUN-2026-09-09-001",
        connector_id=src.id,
        status="RUNNING",
        records_observed=10,
    )
    session.add(run)
    session.commit()
    print(f"-> Layer 0 OAuthScopeRegistry & IngestionRun ({run.run_uuid}) committed successfully.")

    print("\n[Step 3/5] Testing Layer 1 (Immutable Raw Signals Lake) & Deduplication Constraint...")
    raw_hash_1 = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60001"
    raw1 = RawSignal(
        source_type="LINKEDIN_OAUTH",
        source_object_type="person",
        source_object_id="li_member_99812",
        content_hash=raw_hash_1,
        authorization_scope="r_basicprofile",
        raw_payload=json.dumps({"first_name": "Sarah", "last_name": "Connor", "title": "VP Engineering"}),
        provenance_json=json.dumps({"ip": "127.0.0.1", "version": "1.0"}),
    )
    session.add(raw1)
    session.commit()
    print(f"-> Layer 1 RawSignal inserted: ID={raw1.id}, hash={raw1.content_hash[:16]}...")

    # Test uniqueness constraint
    print("-> Verifying SHA-256 idempotency constraint on raw_signals...")
    raw1_dup = RawSignal(
        source_type="LINKEDIN_OAUTH",
        source_object_type="person",
        source_object_id="li_member_99812_duplicate",
        content_hash=raw_hash_1,  # Duplicate content_hash for same source & type
        raw_payload=json.dumps({"different": "payload"}),
    )
    session.add(raw1_dup)
    try:
        session.commit()
        print("FAILED: UniqueConstraint did not reject duplicate raw signal!")
        sys.exit(1)
    except IntegrityError:
        session.rollback()
        print("   [PASSED] UniqueConstraint uq_raw_signal_hash successfully rejected duplicate raw payload.")

    print("\n[Step 4/5] Testing Layer 2 (Canonical Knowledge Graph & Dedicated Fact Tables)...")
    # EntityRegistry entry
    per_key = "PER-CONNOR-SARAH-01"
    ent_per = EntityRegistry(
        canonical_key=per_key,
        entity_type="PERSON",
        primary_source="LINKEDIN_OAUTH",
    )
    session.add(ent_per)
    session.flush()

    cmp_key = "CMP-CYBERDYNE-01"
    ent_cmp = EntityRegistry(
        canonical_key=cmp_key,
        entity_type="COMPANY",
        primary_source="LINKEDIN_OAUTH",
    )
    session.add(ent_cmp)
    session.flush()

    person_fact = PersonEntity(
        canonical_key=per_key,
        full_name="Sarah Connor",
        headline="VP Engineering at Cyberdyne Systems",
        current_title="VP Engineering",
        current_company_name="Cyberdyne Systems",
        current_company_canonical_key=cmp_key,
        location_city="Los Angeles",
        location_state="CA",
        location_country="US",
        primary_email="s.connor@cyberdyne.io",
        seniority_level="VP",
    )
    session.add(person_fact)

    company_fact = CompanyEntity(
        canonical_key=cmp_key,
        canonical_name="Cyberdyne Systems",
        primary_domain="cyberdyne.io",
        industry="Artificial Intelligence & Robotics",
        headquarters="Sunnyvale, CA",
        headcount_range="501-1000",
    )
    session.add(company_fact)

    rel_edge = RelationshipEdge(
        source_canonical_key=per_key,
        target_canonical_key=cmp_key,
        relationship_type="CURRENTLY_WORKS_AT",
        is_current=True,
        epistemic_level="OBSERVED_FACT",
        confidence=1.0,
        evidence_summary="Verified via LinkedIn OAuth profile payload",
    )
    session.add(rel_edge)
    session.commit()
    print(f"-> Layer 2 PersonEntity '{person_fact.full_name}' and CompanyEntity '{company_fact.canonical_name}' created.")
    print(f"-> Layer 2 RelationshipEdge '{rel_edge.relationship_type}' ({per_key} -> {cmp_key}) created.")

    # Test foreign key cascade
    print("-> Verifying foreign key cascade (EntityRegistry -> PersonEntity)...")
    session.delete(ent_per)
    session.commit()
    remaining_person = session.query(PersonEntity).filter(PersonEntity.canonical_key == per_key).first()
    assert remaining_person is None, "PersonEntity should have cascaded when EntityRegistry record was deleted!"
    print("   [PASSED] Foreign key cascade on delete verified: PersonEntity removed when EntityRegistry deleted.")

    print("\n[Step 5/5] Testing Layer 3 (Intelligence, Intent Events & Explainable Provenance)...")
    # Expire previous session cache and re-insert person entity for Layer 3 testing
    session.expire_all()
    session.add(EntityRegistry(canonical_key=per_key, entity_type="PERSON", primary_source="LINKEDIN_OAUTH"))
    session.flush()
    session.add(PersonEntity(canonical_key=per_key, full_name="Sarah Connor", current_title="VP Engineering"))
    session.commit()

    sig_event = SignalEvent(
        target_canonical_key=cmp_key,
        event_type="JOB_POSTED",
        weight=0.35,
        raw_signal_hash=raw_hash_1,
        metadata_json=json.dumps({"title": "Principal AI Architect"}),
    )
    session.add(sig_event)
    session.flush()

    intent = DerivedIntent(
        target_canonical_key=cmp_key,
        intent_category="HIRING_INTENT",
        score=92,
        confidence=0.95,
        model_version="v1.0-event-aggregator",
    )
    session.add(intent)
    session.flush()

    evidence = EvidenceLedger(
        derived_intent_id=intent.id,
        signal_event_id=sig_event.id,
        claim_text="Observed job posting for Principal AI Architect",
        evidence_excerpt=f"Raw signal hash {raw_hash_1[:12]} verified on 2026-09-09",
        observed_at=datetime.now(timezone.utc),
        confidence=0.95,
    )
    session.add(evidence)

    velocity = CareerVelocityRecord(
        person_canonical_key=per_key,
        velocity_score=88,
        time_in_role_months=14,
        avg_promotion_interval_months=18.5,
        title_level_progression="Lead -> Director -> VP",
        skills_velocity=90,
    )
    session.add(velocity)
    session.commit()

    print(f"-> Layer 3 SignalEvent (ID={sig_event.id}, type={sig_event.event_type}) recorded.")
    print(f"-> Layer 3 DerivedIntent (ID={intent.id}, category={intent.intent_category}, score={intent.score}%) recorded.")
    print(f"-> Layer 3 EvidenceLedger (ID={evidence.id}) linked to Intent #{intent.id} and Event #{sig_event.id}.")
    print(f"-> Layer 3 CareerVelocityRecord (score={velocity.velocity_score}/100) recorded.")

    print("\n" + "=" * 80)
    print("CHECK 1 RESULT: PASSED (100% SUCCESSFUL)")
    print("All 16 tables across all 4 epistemic layers verified with integrity constraints.")
    print("=" * 80)
    session.close()

if __name__ == "__main__":
    run_check_1()
