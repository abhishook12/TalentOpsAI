"""
data_intelligence.py — API Endpoints for Data Intelligence & Source Orchestration.

Features:
1. Pluggable Source Connector Catalog & Health Status
2. Natural Language AI Query Layer over Multi-Source Evidence
3. Google Chat & Microsoft Teams Unstructured Ingestion
4. Entity-Level Multi-Source Observation Reconciliation
5. Cost-Aware Enrichment Plan Formulation
"""

import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.data_quality_models import (
    PersonIdentity,
    FieldObservation,
    PersonContactHistory,
)
from ..models.intelligence_models import (
    SourceConnector,
    RawSignal,
    FieldConflictRecord,
)
from ..services.source_connector_base import (
    SourceConnectorRegistry,
    GoogleChatSourceConnector,
    MicrosoftTeamsSourceConnector,
)
from ..services.chat_intelligence_pipeline import ChatIntelligencePipeline
from ..services.source_reconciliation_engine import SourceReconciliationEngine
from ..services.enrichment_planner import EnrichmentPlanner
from ..services.ai_data_query_engine import AIDataQueryEngine

logger = logging.getLogger("talentops.routes.intelligence")
router = APIRouter(prefix="/intelligence", tags=["Data Intelligence & Connectors"])


# ── Pydantic Request Schemas ─────────────────────────────────────────────────

class AIQueryRequest(BaseModel):
    query: str
    limit: int = 50
    skip: int = 0


class ChatIngestRequest(BaseModel):
    text: str
    source_platform: str = "GOOGLE_CHAT"  # GOOGLE_CHAT, MICROSOFT_TEAMS, RECRUITER_NOTES
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    user_id: Optional[int] = None


# ── Route Handlers ───────────────────────────────────────────────────────────

@router.get("/connectors")
def list_connectors(db: Session = Depends(get_db)):
    """
    Returns registered source connectors, their reliability weighting,
    cost structures, and supported data categories.
    """
    connectors = SourceConnectorRegistry.list_all()
    results = []
    for c in connectors:
        results.append({
            "connector_key": c.connector_key,
            "source_type": c.source_type,
            "name": c.name,
            "auth_type": c.auth_type,
            "source_reliability": c.source_reliability,
            "field_reliability": c.field_reliability,
            "cost_per_query_usd": c.cost_per_query_usd,
            "supported_data_categories": c.supported_data_categories,
            "rate_limit_rpm": c.rate_limit_rpm,
        })
    return {"connectors": results, "total": len(results)}


@router.post("/query")
def execute_ai_query(
    req: AIQueryRequest,
    db: Session = Depends(get_db),
):
    """
    Translates natural language questions into structured queries across
    canonical entities, field provenance, and temporal contact history.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    return AIDataQueryEngine.execute_query(
        db=db,
        query_text=req.query,
        limit=req.limit,
        skip=req.skip,
    )


@router.post("/chat-ingest")
def ingest_chat_note(
    req: ChatIngestRequest,
    db: Session = Depends(get_db),
):
    """
    Parses unstructured chat notes or webhooks from Google Chat / Microsoft Teams.
    Extracts partial facts without fabricating identity, records an immutable
    RawSignal with SHA-256 hash, and returns normalized field observations.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text payload cannot be empty")

    # 1. Parse via ChatIntelligencePipeline
    parsed = ChatIntelligencePipeline.parse_message(
        text=req.text,
        source_platform=req.source_platform,
        sender_info={"name": req.sender_name, "email": req.sender_email},
    )

    # 2. Record immutable RawSignal with SHA-256 idempotency
    connector = SourceConnectorRegistry.get(req.source_platform)
    raw_dict = (connector or GoogleChatSourceConnector()).create_raw_record_dict(
        source_object_type="chat_message",
        source_object_id=f"CHAT-{hash(req.text) & 0xFFFFFFFF}",
        raw_payload={"text": req.text, "sender": req.sender_name},
        authorization_scope="chat_webhook",
        provenance={"sender_email": req.sender_email},
    )

    existing = db.query(RawSignal).filter(RawSignal.content_hash == raw_dict["content_hash"]).first()
    if not existing:
        raw_sig = RawSignal(
            source_type=raw_dict["source_type"],
            source_object_type=raw_dict["source_object_type"],
            source_object_id=raw_dict["source_object_id"],
            content_hash=raw_dict["content_hash"],
            authorization_scope=raw_dict["authorization_scope"],
            raw_payload=raw_dict["raw_payload"],
            provenance_json=raw_dict["provenance_json"],
        )
        db.add(raw_sig)
        db.commit()

    return {
        "status": "INGESTED",
        "content_hash": raw_dict["content_hash"],
        "analysis": parsed,
    }


@router.post("/reconcile/{person_id}")
def reconcile_person(
    person_id: int,
    db: Session = Depends(get_db),
):
    """
    Fuses all observations across all connected sources for a given PersonIdentity.
    Computes effective time-decayed confidences and quarantines detected conflicts.
    """
    person = db.query(PersonIdentity).filter(PersonIdentity.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail=f"Person {person_id} not found")

    # Fetch all observations
    obs_rows = (
        db.query(FieldObservation)
        .filter(FieldObservation.entity_type == "PERSON", FieldObservation.entity_id == person_id)
        .all()
    )

    observations = [
        {
            "field_name": o.field_name,
            "field_value": o.field_value,
            "source": o.source,
            "confidence": o.confidence,
            "observed_at": o.observed_at,
        }
        for o in obs_rows
    ]

    # Fetch existing contact history
    history_rows = (
        db.query(PersonContactHistory)
        .filter(PersonContactHistory.person_identity_id == person_id)
        .all()
    )
    existing_history = [
        {
            "contact_type": h.contact_type,
            "contact_value": h.contact_value,
            "status": h.status,
            "valid_from": h.valid_from,
            "valid_to": h.valid_to,
        }
        for h in history_rows
    ]

    fusion = SourceReconciliationEngine.fuse_entity_observations(
        observations=observations,
        existing_history=existing_history,
    )

    # If conflicts detected, record in field_conflict_records
    for conf in fusion.get("conflicts", []):
        cand_a = conf.get("candidate_a", {})
        cand_b = conf.get("candidate_b", {})
        conflict_rec = FieldConflictRecord(
            entity_type="PERSON",
            entity_id=person_id,
            field_name=conf.get("field_name"),
            source_a=",".join(cand_a.get("sources", ["UNKNOWN"])),
            value_a=str(cand_a.get("value")),
            confidence_a=cand_a.get("confidence", 0.0),
            source_b=",".join(cand_b.get("sources", ["UNKNOWN"])),
            value_b=str(cand_b.get("value")),
            confidence_b=cand_b.get("confidence", 0.0),
            resolution_notes=conf.get("reason"),
        )
        db.add(conflict_rec)
    db.commit()

    return {
        "person_id": person_id,
        "reconciliation": fusion,
    }


@router.post("/enrichment-plan/{person_id}")
def generate_enrichment_plan(
    person_id: int,
    tenant_spend_usd: float = Query(0.0),
    db: Session = Depends(get_db),
):
    """
    Formulates a conditional, cost-aware enrichment plan to fill missing candidate fields.
    """
    person = db.query(PersonIdentity).filter(PersonIdentity.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail=f"Person {person_id} not found")

    person_data = {
        "full_name": person.canonical_name,
        "current_company": person.current_company,
        "current_title": person.current_title,
        "primary_email": person.primary_email,
        "primary_phone": person.primary_phone,
        "linkedin_url": person.canonical_profile_url,
    }

    plan = EnrichmentPlanner.plan_enrichment(
        person_id=person_id,
        person_data=person_data,
        tenant_spend_usd=tenant_spend_usd,
    )
    return plan
