"""
Multi-User Scout Node Telemetry API Routes — /scout/*

Endpoints for verifying per-user browser extension heartbeats,
last captures, last extractions, and master DB writes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.auth_models import User
from ..services.auth_service import get_current_user_from_request
from ..services.scout_node_service import (
    record_scout_heartbeat,
    get_all_scout_nodes_telemetry,
)

router = APIRouter(prefix="/scout", tags=["Scout Node Telemetry"])


class HeartbeatPayload(BaseModel):
    device_id: str
    page_url: Optional[str] = None
    capture_id: Optional[str] = None
    client_metrics: Optional[Dict[str, Any]] = None


@router.post("/heartbeat")
def post_heartbeat(
    payload: HeartbeatPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Heartbeat ping sent by active browser extension scout nodes every 15-30 seconds.
    """
    return record_scout_heartbeat(
        db=db,
        user_id=current_user.id,
        device_id=payload.device_id,
        page_url=payload.page_url,
        capture_id=payload.capture_id,
        client_metrics=payload.client_metrics,
    )


@router.get("/nodes")
def get_scout_nodes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns live heartbeat, capture timestamps, and database write telemetry
    for all connected users / scout nodes.
    """
    return get_all_scout_nodes_telemetry(db)


@router.get("/summary")
def get_scout_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns high-level aggregate summary of all connected scout nodes.
    """
    data = get_all_scout_nodes_telemetry(db)
    return {
        "total_nodes": data["total_scout_nodes"],
        "active_connected_nodes": data["active_connected_nodes"],
        "streaming_nodes": data["active_nodes_streaming_data"],
    }
