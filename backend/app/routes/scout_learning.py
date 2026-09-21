"""
backend/app/routes/scout_learning.py — Autonomous Scout Learning & Fleet Sync Endpoints

Handles:
- POST /scout/learning/ingest-ambiguities: Ingests ambiguous extractions and triggers autonomous teacher adjudication.
- GET /scout/fleet/sync-knowledge: Serves knowledge deltas to Desktop Scout instances for continuous learning.
- POST /scout/learning/adjudicate-instant: Direct real-time adjudication endpoint for verification and diagnostic tests.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.autonomous_teacher_service import AutonomousTeacherService

logger = logging.getLogger("talentops.routes.scout_learning")

router = APIRouter(prefix="/scout", tags=["Scout Autonomous Learning"])


class AmbiguousObservationItem(BaseModel):
    candidate_text: str
    provisional_type: Optional[str] = "UNKNOWN"
    provisional_confidence: Optional[float] = 0.50
    context_lines: Optional[List[str]] = Field(default_factory=list)
    source_url: Optional[str] = ""
    window_title: Optional[str] = ""


class IngestAmbiguitiesPayload(BaseModel):
    device_id: Optional[str] = "UNKNOWN"
    scout_version: Optional[str] = "2.9.2"
    observations: List[AmbiguousObservationItem]


class InstantAdjudicationPayload(BaseModel):
    candidate_text: str
    context_lines: Optional[List[str]] = Field(default_factory=list)
    source_url: Optional[str] = ""
    window_title: Optional[str] = ""


@router.post("/learning/ingest-ambiguities")
def ingest_ambiguities(
    payload: IngestAmbiguitiesPayload,
    db: Session = Depends(get_db),
):
    """
    Ingests batches of ambiguous observations buffered by Desktop Scout instances.
    Triggers asynchronous AI Teacher auto-adjudication, automatically resolving ground truth
    and promoting verified entities into the canonical Knowledge Graph.
    """
    obs_dicts = [obs.model_dump() for obs in payload.observations]
    if not obs_dicts:
        return {"status": "SUCCESS", "adjudicated": 0, "results": []}

    logger.info("Received shadow learning batch of %d items from %s", len(obs_dicts), payload.device_id)

    # Process adjudication
    results = AutonomousTeacherService.process_batch(
        observations=obs_dicts,
        owner_user_id=1,  # Default system administrator
        db=db,
    )

    promoted_count = sum(1 for r in results if r.get("promoted_id"))
    return {
        "status": "SUCCESS",
        "adjudicated": len(results),
        "promoted_to_knowledge_graph": promoted_count,
        "results": results,
    }


@router.get("/fleet/sync-knowledge")
def sync_knowledge(
    since: float = Query(0.0, description="Timestamp of last sync"),
    device_id: Optional[str] = Query(None, description="Requesting device identifier"),
    limit: int = Query(100, description="Max entities to return"),
    db: Session = Depends(get_db),
):
    """
    Serves incremental knowledge updates to Desktop Scout instances.
    Enables fleet collective intelligence: once one Scout encounters and resolves
    an entity, every Scout in the organization knows it without restarting.
    """
    deltas = AutonomousTeacherService.get_fleet_knowledge_deltas(
        since_timestamp=since,
        db=db,
        limit=limit,
    )

    return {
        "status": "SUCCESS",
        "device_id": device_id,
        "server_timestamp": time.time(),
        "entities_count": len(deltas),
        "entities": deltas,
    }


@router.post("/learning/adjudicate-instant")
def adjudicate_instant(
    payload: InstantAdjudicationPayload,
    db: Session = Depends(get_db),
):
    """
    Direct synchronous adjudication endpoint. Used for immediate diagnostic validation,
    ad-hoc classification, and test verification.
    """
    result = AutonomousTeacherService.adjudicate_observation(
        candidate_text=payload.candidate_text,
        context_lines=payload.context_lines,
        source_url=payload.source_url,
        window_title=payload.window_title,
        owner_user_id=1,
        db=db,
    )

    return {
        "status": "SUCCESS",
        "adjudication": result,
    }
