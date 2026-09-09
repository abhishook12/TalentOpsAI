"""
scout_dead_letter.py — Dead-Letter Queue (DLQ) & Failed-Job Recovery API Routes (/scout/dead-letter/*)

Provides visibility and recovery controls for stalled, conflicted, or rejected
Scout observations to guarantee zero data loss.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..models.staging_models import DiscoveryStaging, ResolvedPerson
from ..models.auth_models import User
from ..services.auth_service import get_current_user_from_request
from ..services.discovery_processor import DiscoveryProcessor

logger = logging.getLogger("talentops.scout_dead_letter")
router = APIRouter(prefix="/scout/dead-letter", tags=["Scout Dead Letter Queue"])


class RetryDLQRequest(BaseModel):
    reason: Optional[str] = "Admin manual retry"


@router.get("")
def get_dead_letter_records(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status (review, rejected, conflict)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns uncommitted, failed, conflicted, or review-flagged Scout staging records.
    Allows administrators to inspect and recover data that could not be automatically resolved.
    """
    query = db.query(DiscoveryStaging).filter(
        DiscoveryStaging.processing_status.in_(["review", "rejected", "conflict", "failed"])
    )

    if status:
        query = query.filter(DiscoveryStaging.processing_status == status)

    total = query.count()
    records = query.order_by(desc(DiscoveryStaging.created_at)).offset(offset).limit(limit).all()

    items = []
    for r in records:
        items.append({
            "id": r.id,
            "discovery_id": r.discovery_id,
            "device_id": r.device_id,
            "owner_user_id": r.owner_user_id,
            "raw_name": r.raw_name,
            "raw_title": r.raw_title,
            "raw_company": r.raw_company,
            "raw_email": r.raw_email,
            "raw_phone": r.raw_phone,
            "raw_linkedin": r.raw_linkedin,
            "source_url": r.source_url,
            "processing_status": r.processing_status,
            "decision": r.decision,
            "decision_reason": r.decision_reason,
            "identity_confidence": r.identity_confidence,
            "quality_score": r.quality_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        })

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


@router.post("/{staging_id}/retry")
def retry_dead_letter_record(
    staging_id: int,
    req: RetryDLQRequest = RetryDLQRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Resets a failed/rejected observation back to 'pending' and immediately re-triggers
    batch intelligence processing.
    """
    record = db.query(DiscoveryStaging).filter(DiscoveryStaging.id == staging_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dead-letter record not found")

    record.processing_status = "pending"
    record.decision = None
    record.decision_reason = f"Queued for re-processing: {req.reason}"
    record.processed_at = None
    db.commit()

    # Trigger immediate batch processor
    processor = DiscoveryProcessor(db)
    stats = processor.process_pending_batch(limit=10)

    db.refresh(record)
    logger.info("Retried DLQ record id=%d discovery_id=%s. New status: %s", staging_id, record.discovery_id, record.processing_status)

    return {
        "ok": True,
        "staging_id": staging_id,
        "discovery_id": record.discovery_id,
        "processing_status": record.processing_status,
        "decision": record.decision,
        "processor_stats": stats,
    }


@router.post("/{staging_id}/replay")
def replay_dead_letter_record(
    staging_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Forces immediate re-evaluation and resolution of this single record against the master database.
    """
    record = db.query(DiscoveryStaging).filter(DiscoveryStaging.id == staging_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dead-letter record not found")

    record.processing_status = "pending"
    db.commit()

    processor = DiscoveryProcessor(db)
    stats = processor.process_pending_batch(limit=10)

    db.refresh(record)
    return {
        "ok": True,
        "staging_id": staging_id,
        "discovery_id": record.discovery_id,
        "processing_status": record.processing_status,
        "decision": record.decision,
        "stats": stats,
    }


@router.delete("/{staging_id}")
def discard_dead_letter_record(
    staging_id: int,
    reason: Optional[str] = Query("Discarded by admin audit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Safely marks a dead-letter item as discarded with full audit reason,
    without physically destroying historical raw observation data.
    """
    record = db.query(DiscoveryStaging).filter(DiscoveryStaging.id == staging_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dead-letter record not found")

    record.processing_status = "discarded"
    record.decision = "DISCARDED"
    record.decision_reason = reason
    record.processed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "ok": True,
        "staging_id": staging_id,
        "discovery_id": record.discovery_id,
        "status": "DISCARDED",
        "reason": reason,
    }
