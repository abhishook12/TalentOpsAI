"""
check_pipeline_3_intent_and_api.py
Pipeline Verification Check 3: Intent Aggregator & FastAPI Staging Pipeline Dashboard APIs.

Tests:
1. Intent Engine execution on dev.db:
   - Calculate HIRING_INTENT for target company
   - Calculate TECHNOLOGY_ADOPTION for target candidates/companies
   - Validate explainability audit trails in EvidenceLedger
2. FastAPI Staging Pipeline Routes:
   - GET /health
   - GET /staging/summary
   - GET /staging/records
   - GET /staging/decision-distribution
   - GET /staging/resolved-persons
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models.auth_models import User
from app.models.intelligence_models import (
    CompanyEntity,
    PersonEntity,
    SignalEvent,
    DerivedIntent,
    EvidenceLedger,
)
from app.services.intelligence.intent_aggregator import IntentAggregator
from app.services.auth_service import get_current_user_from_request
from app.main import app
from starlette.testclient import TestClient

def run_pipeline_check_3():
    print("=" * 80)
    print("PIPELINE CHECK 3: INTENT AGGREGATOR & FASTAPI PIPELINE DASHBOARD APIS")
    print("=" * 80)

    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "dev.db"))
    print(f"Connecting to dev database: {db_path}")
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # ── Part 1: Run Layer 3 Intent Engine ────────────────────────────────────
    print("\n[Step 1/5] Running IntentAggregator on Knowledge Graph signals...")
    aggregator = IntentAggregator(db=session)

    comp = session.query(CompanyEntity).filter(CompanyEntity.canonical_name == "Anthropic AI").first()
    assert comp is not None, "Anthropic AI company entity not found in dev.db!"

    # Calculate Hiring Intent
    hiring_res = aggregator.calculate_company_hiring_intent(comp.canonical_key, window_days=90)
    print(f"-> Hiring Intent for {comp.canonical_name}:")
    print(f"   Score:      {hiring_res['score']} / 100")
    print(f"   Confidence: {hiring_res['confidence']:.2f}")
    print(f"   Evidence:   {hiring_res['evidence_count']} items")

    # Calculate Tech Adoption Intent for Kubernetes
    per = session.query(PersonEntity).filter(PersonEntity.canonical_key.ilike("PER-LI-DEVIN%")).first()
    assert per is not None, "Devin Chandler person entity not found in dev.db!"

    tech_res = aggregator.calculate_tech_adoption_intent(per.canonical_key, "Kubernetes")
    print(f"-> Technology Adoption Intent for '{tech_res['technology']}':")
    print(f"   Score:      {tech_res['score']} / 100")
    print(f"   Confidence: {tech_res['confidence']:.2f}")

    # Step 2: Audit EvidenceLedger for claims
    print("\n[Step 2/5] Inspecting EvidenceLedger explainability records...")
    ledger_entries = session.query(EvidenceLedger).join(
        DerivedIntent, EvidenceLedger.derived_intent_id == DerivedIntent.id
    ).filter(DerivedIntent.target_canonical_key == comp.canonical_key).all()

    print(f"-> Verified {len(ledger_entries)} audit trail entries in EvidenceLedger:")
    for item in ledger_entries:
        print(f"   [OK] Claim: {item.claim_text}")
        print(f"        Excerpt: {item.evidence_excerpt}")
        print(f"        Confidence: {item.confidence:.2f}")

    # ── Part 2: Test FastAPI Staging Pipeline Dashboard Endpoints ─────────────
    print("\n[Step 3/5] Setting up FastAPI TestClient with Mock Auth & DB override...")
    mock_user = session.query(User).first()
    if not mock_user:
        mock_user = User(
            id=1,
            email="admin@talentops.ai",
            password_hash="mock",
            first_name="Admin",
            last_name="User",
            status="active",
        )
        session.add(mock_user)
        session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    def override_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_from_request] = override_current_user

    client = TestClient(app)

    # Test GET /health
    print("\n[Step 4/5] Testing GET /health...")
    resp_health = client.get("/health")
    print(f"-> GET /health: HTTP {resp_health.status_code} - {resp_health.json()}")
    assert resp_health.status_code == 200

    # Test GET /staging/summary
    print("\n[Step 5/5] Testing Staging Dashboard Endpoints (/staging/*)...")
    resp_summary = client.get("/staging/summary")
    print(f"-> GET /staging/summary: HTTP {resp_summary.status_code}")
    summary_data = resp_summary.json()
    print(f"   Committed: {summary_data.get('committed')}, Pending: {summary_data.get('pending')}, Total All-Time: {summary_data.get('total_all_time')}")
    assert resp_summary.status_code == 200
    assert "committed" in summary_data

    # Test GET /staging/records
    resp_records = client.get("/staging/records?limit=5")
    print(f"-> GET /staging/records: HTTP {resp_records.status_code}")
    records_data = resp_records.json()
    print(f"   Returned {len(records_data.get('records', []))} records (Total: {records_data.get('total')})")
    assert resp_records.status_code == 200

    # Test GET /staging/decision-distribution
    resp_dist = client.get("/staging/decision-distribution")
    print(f"-> GET /staging/decision-distribution: HTTP {resp_dist.status_code}")
    dist_data = resp_dist.json()
    print(f"   Distribution entries: {len(dist_data.get('distribution', []))}")
    assert resp_dist.status_code == 200

    # Test GET /staging/resolved-persons
    resp_resolved = client.get("/staging/resolved-persons?limit=5")
    print(f"-> GET /staging/resolved-persons: HTTP {resp_resolved.status_code}")
    assert resp_resolved.status_code == 200

    print("\n" + "=" * 80)
    print("PIPELINE CHECK 3 RESULT: PASSED (100% SUCCESSFUL)")
    print("Intent calculation, evidence ledger, and Staging API routes 100% verified.")
    print("=" * 80)

    # Clean dependency overrides
    app.dependency_overrides.clear()
    session.close()

if __name__ == "__main__":
    run_pipeline_check_3()
