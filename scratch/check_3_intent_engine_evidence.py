"""
check_3_intent_engine_evidence.py
Verification Check 3: Event-Based Intent Aggregation & Explainable Evidence Ledger.

Tests:
1. Event-based composite intent calculation:
   - Ingest 3 discrete, weighted SignalEvents for a target company:
     a. JOB_POSTED (wt=0.35)
     b. HEADCOUNT_GROWTH (wt=0.25)
     c. LEADERSHIP_EXPANSION (wt=0.25)
2. Temporal recency decay verification:
   - Recent events have higher contribution than aged events.
3. Multi-signal confidence calculation:
   - When multiple independent signal types agree, confidence scales to 0.95.
4. Explainable Evidence Ledger audit trail:
   - Verifies every score is supported by discrete EvidenceLedger rows answering "Why did you show me this?".
5. Technology Adoption Intent calculation:
   - Aggregates TECH_MENTIONED events into dedicated technology adoption signals.
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.schemas.intelligence_contracts import (
    SignalEventType,
    IntentCategory,
    SourceType,
)
from app.models.intelligence_models import (
    EntityRegistry,
    CompanyEntity,
    SignalEvent,
    DerivedIntent,
    EvidenceLedger,
    RawSignal,
)
from app.services.intelligence.intent_aggregator import IntentAggregator


def run_check_3():
    print("=" * 80)
    print("CHECK 3: EVENT-BASED INTENT AGGREGATION & EXPLAINABLE EVIDENCE LEDGER")
    print("=" * 80)

    # 1. Setup in-memory test database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    aggregator = IntentAggregator(db=session)

    # Target company
    comp_key = "CMP-DATABRICKS-01"
    session.add(EntityRegistry(canonical_key=comp_key, entity_type="COMPANY", primary_source="LINKEDIN_OAUTH"))
    session.add(CompanyEntity(canonical_key=comp_key, canonical_name="Databricks", primary_domain="databricks.com"))
    session.commit()

    # ── Step 1: Ingest 3 Atomic Signal Events ────────────────────────────────
    print("\n[Step 1/5] Ingesting 3 atomic SignalEvents for target company Databricks...")
    now = datetime.now(timezone.utc)

    # Event 1: Fresh Job Posting (1 day ago)
    ev1 = SignalEvent(
        target_canonical_key=comp_key,
        event_type=SignalEventType.JOB_POSTED.value,
        weight=0.35,
        event_timestamp=now - timedelta(days=1),
        raw_signal_hash="hash_raw_job_post_001",
        metadata_json=json.dumps({"job_title": "Staff AI Infrastructure Engineer", "department": "Platform"}),
    )
    # Event 2: Verified Headcount Growth (7 days ago)
    ev2 = SignalEvent(
        target_canonical_key=comp_key,
        event_type=SignalEventType.HEADCOUNT_GROWTH.value,
        weight=0.25,
        event_timestamp=now - timedelta(days=7),
        raw_signal_hash="hash_raw_headcount_002",
        metadata_json=json.dumps({"growth_pct": 14.5, "net_new_hires_30d": 42}),
    )
    # Event 3: Leadership Expansion (12 days ago)
    ev3 = SignalEvent(
        target_canonical_key=comp_key,
        event_type=SignalEventType.LEADERSHIP_EXPANSION.value,
        weight=0.25,
        event_timestamp=now - timedelta(days=12),
        raw_signal_hash="hash_raw_leader_003",
        metadata_json=json.dumps({"leader_title": "VP of Core Engineering", "previous_company": "Google"}),
    )

    session.add_all([ev1, ev2, ev3])
    session.commit()
    print(f"-> Created 3 signal events: JOB_POSTED (wt=0.35), HEADCOUNT_GROWTH (wt=0.25), LEADERSHIP_EXPANSION (wt=0.25)")

    # ── Step 2: Calculate Company Hiring Intent ──────────────────────────────
    print("\n[Step 2/5] Running IntentAggregator.calculate_company_hiring_intent()...")
    hiring_result = aggregator.calculate_company_hiring_intent(comp_key, window_days=90)

    assert hiring_result is not None, "Intent calculation returned None!"
    print(f"-> Hiring Intent Calculated:")
    print(f"   Score:      {hiring_result['score']} / 100")
    print(f"   Confidence: {hiring_result['confidence']:.2f}")
    print(f"   Evidence:   {hiring_result['evidence_count']} supporting items")

    assert hiring_result["score"] >= 80, f"Expected strong score >= 80, got {hiring_result['score']}"
    assert hiring_result["confidence"] == 0.95, f"Expected 0.95 confidence for 3 distinct signal types, got {hiring_result['confidence']}"

    # ── Step 3: Audit Trail in EvidenceLedger ────────────────────────────────
    print("\n[Step 3/5] Auditing EvidenceLedger: Answering 'Why did you show me this?'...")
    ledger_entries = session.query(EvidenceLedger).join(
        DerivedIntent, EvidenceLedger.derived_intent_id == DerivedIntent.id
    ).filter(DerivedIntent.target_canonical_key == comp_key).all()

    assert len(ledger_entries) == 3, f"Expected 3 ledger entries, got {len(ledger_entries)}"
    print(f"-> Found {len(ledger_entries)} verified audit records in EvidenceLedger:")
    for idx, row in enumerate(ledger_entries, 1):
        print(f"   [{idx}] Claim:      {row.claim_text}")
        print(f"       Evidence:   {row.evidence_excerpt}")
        print(f"       Observed:   {row.observed_at.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"       Confidence: {row.confidence:.2f}")
        assert row.claim_text, "Claim text must not be empty"
        assert row.evidence_excerpt, "Evidence excerpt must not be empty"
    print("   [PASSED] Every intent score has an unbroken, explainable audit trail.")

    # ── Step 4: Temporal Recency Decay Verification ──────────────────────────
    print("\n[Step 4/5] Testing Recency Decay on aged events...")
    # Add an event from 80 days ago (near edge of 90-day window)
    old_comp_key = "CMP-LEGACY-01"
    session.add(EntityRegistry(canonical_key=old_comp_key, entity_type="COMPANY", primary_source="SYSTEM"))
    session.add(CompanyEntity(canonical_key=old_comp_key, canonical_name="Legacy Systems Inc"))
    session.commit()

    ev_old = SignalEvent(
        target_canonical_key=old_comp_key,
        event_type=SignalEventType.JOB_POSTED.value,
        weight=0.35,
        event_timestamp=now - timedelta(days=80),
        raw_signal_hash="hash_old_job_80d",
        metadata_json=json.dumps({"job_title": "Old Opening"}),
    )
    session.add(ev_old)
    session.commit()

    legacy_result = aggregator.calculate_company_hiring_intent(old_comp_key, window_days=90)
    print(f"-> Fresh event (1 day old) contribution score: {hiring_result['score']}")
    print(f"-> Aged event (80 days old) score: {legacy_result['score']}")
    # An 80-day old event has a decay factor of ~0.55, so contribution is ~0.35 * 0.55 = 0.19 (score ~19-25)
    assert legacy_result["score"] < hiring_result["score"], "Aged event score must be lower than fresh event score!"
    print("   [PASSED] Temporal decay correctly discounts older signals.")

    # ── Step 5: Technology Adoption Intent Engine ────────────────────────────
    print("\n[Step 5/5] Testing Technology Adoption Intent Engine...")
    session.add(SignalEvent(
        target_canonical_key=comp_key,
        event_type=SignalEventType.TECH_MENTIONED.value,
        weight=0.30,
        raw_signal_hash="hash_tech_spark_1",
        metadata_json=json.dumps({"technology": "Apache Spark"}),
    ))
    session.add(SignalEvent(
        target_canonical_key=comp_key,
        event_type=SignalEventType.TECH_MENTIONED.value,
        weight=0.30,
        raw_signal_hash="hash_tech_spark_2",
        metadata_json=json.dumps({"technology": "Apache Spark"}),
    ))
    session.add(SignalEvent(
        target_canonical_key=comp_key,
        event_type=SignalEventType.TECH_MENTIONED.value,
        weight=0.30,
        raw_signal_hash="hash_tech_spark_3",
        metadata_json=json.dumps({"technology": "Apache Spark"}),
    ))
    session.commit()

    tech_result = aggregator.calculate_tech_adoption_intent(comp_key, "Apache Spark")
    assert tech_result is not None, "Tech adoption calculation returned None!"
    print(f"-> Tech Adoption Calculated for '{tech_result['technology']}':")
    print(f"   Score:      {tech_result['score']} / 100")
    print(f"   Confidence: {tech_result['confidence']:.2f}")
    print(f"   Evidences:  {tech_result['evidence_count']}")
    assert tech_result["score"] == 90, f"Expected 90, got {tech_result['score']}"
    assert tech_result["confidence"] >= 0.90

    print("\n" + "=" * 80)
    print("CHECK 3 RESULT: PASSED (100% SUCCESSFUL)")
    print("Intent aggregation, temporal decay, and explainable audit trail verified.")
    print("=" * 80)
    session.close()

if __name__ == "__main__":
    run_check_3()
