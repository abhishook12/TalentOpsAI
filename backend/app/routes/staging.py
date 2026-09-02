"""
Staging Pipeline API Routes — /staging/*

Endpoints for the Discovery Staging & Batch Intelligence Pipeline dashboard.
Provides visibility into the staging buffer, batch processing status,
resolved person clusters, and manual review queue.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from ..database import get_db
from ..models.staging_models import DiscoveryStaging, ResolvedPerson
from ..models.models import Recruiter, Company
from ..models.extension_models import ExtensionDiscoveryEvent
from ..models.auth_models import User
from ..services.auth_service import get_current_user_from_request
from ..services.discovery_processor import run_batch_processor, DiscoveryProcessor

logger = logging.getLogger('talentops.staging')
router = APIRouter(prefix='/staging', tags=['Staging Pipeline'])


class ReviewActionRequest(BaseModel):
    action: str  # 'approve', 'reject', 'merge'
    recruiter_id: Optional[int] = None
    notes: Optional[str] = None


@router.get("/summary")
def get_staging_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns aggregate counts for the staging pipeline dashboard (Bronze, Silver, Gold).
    """
    try:
        # Status counts
        status_counts = dict(
            db.query(
                DiscoveryStaging.processing_status,
                sqlfunc.count(DiscoveryStaging.id)
            ).group_by(DiscoveryStaging.processing_status).all()
        )

        pending = status_counts.get("pending", 0)
        batched = status_counts.get("batched", 0)
        processing = status_counts.get("processing", 0)
        committed = status_counts.get("committed", 0)
        rejected = status_counts.get("rejected", 0)
        review = status_counts.get("review", 0)

        # Today's totals
        today_cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(sqlfunc.count(DiscoveryStaging.id)).filter(
            DiscoveryStaging.created_at >= today_cutoff
        ).scalar() or 0

        total_all_time = db.query(sqlfunc.count(DiscoveryStaging.id)).scalar() or 0
        resolved_persons_count = db.query(sqlfunc.count(ResolvedPerson.id)).scalar() or 0

        # Last processed timestamp
        last_processed = db.query(DiscoveryStaging.processed_at).filter(
            DiscoveryStaging.processed_at != None
        ).order_by(DiscoveryStaging.processed_at.desc()).first()

        last_processed_at = last_processed[0].isoformat() if last_processed and last_processed[0] else None

        # Rate calculation (records processed today per hour elapsed)
        now = datetime.now(timezone.utc)
        hours_elapsed = max(1.0, (now - today_cutoff).total_seconds() / 3600.0)
        rate = round(committed / hours_elapsed, 1)

        return {
            "pending": pending,
            "batched": batched,
            "processing": processing,
            "committed": committed,
            "rejected": rejected,
            "review": review,
            "total_today": today_count,
            "total_all_time": total_all_time,
            "resolved_persons": resolved_persons_count,
            "last_processed_at": last_processed_at,
            "processing_rate": rate,
        }
    except Exception as e:
        logger.error("Error fetching staging summary: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/records")
def get_staging_records(
    status: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns paginated list of raw staging records with filters.
    """
    try:
        q = db.query(DiscoveryStaging)
        if status:
            q = q.filter(DiscoveryStaging.processing_status == status)
        if batch_id:
            q = q.filter(DiscoveryStaging.batch_id == batch_id)

        total = q.count()
        records = q.order_by(DiscoveryStaging.created_at.desc()).offset(skip).limit(limit).all()

        output = []
        for r in records:
            output.append({
                "id": r.id,
                "batch_id": r.batch_id,
                "discovery_id": r.discovery_id,
                "device_id": r.device_id,
                "raw_name": r.raw_name,
                "raw_title": r.raw_title,
                "raw_company": r.raw_company,
                "raw_email": r.raw_email,
                "raw_phone": r.raw_phone,
                "raw_linkedin": r.raw_linkedin,
                "raw_location": r.raw_location,
                "source_url": r.source_url,
                "source_page_title": r.source_page_title,
                "capture_id": r.capture_id,
                "extraction_source": r.extraction_source,
                "visual_change_score": r.visual_change_score,
                "dom_confidence": r.dom_confidence,
                "processing_status": r.processing_status,
                "resolved_person_id": r.resolved_person_id,
                "decision": r.decision,
                "decision_reason": r.decision_reason,
                "identity_confidence": r.identity_confidence,
                "quality_score": r.quality_score,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            })

        return {"records": output, "total": total}
    except Exception as e:
        logger.error("Error fetching staging records: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resolved-persons")
def get_resolved_persons(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    has_recruiter: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns paginated list of consolidated ResolvedPerson entities.
    """
    try:
        q = db.query(ResolvedPerson)
        if has_recruiter is True:
            q = q.filter(ResolvedPerson.recruiter_id != None)
        elif has_recruiter is False:
            q = q.filter(ResolvedPerson.recruiter_id == None)

        total = q.count()
        persons = q.order_by(ResolvedPerson.updated_at.desc()).offset(skip).limit(limit).all()

        output = []
        for p in persons:
            output.append({
                "id": p.id,
                "canonical_name": p.canonical_name,
                "current_title": p.current_title,
                "current_company": p.current_company,
                "previous_title": p.previous_title,
                "previous_company": p.previous_company,
                "primary_email": p.primary_email,
                "primary_phone": p.primary_phone,
                "linkedin_url": p.linkedin_url,
                "location": p.location,
                "identity_confidence": p.identity_confidence,
                "observation_count": p.observation_count,
                "recruiter_id": p.recruiter_id,
                "name_confidence": p.name_confidence,
                "title_confidence": p.title_confidence,
                "company_confidence": p.company_confidence,
                "email_confidence": p.email_confidence,
                "phone_confidence": p.phone_confidence,
                "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
            })

        return {"persons": output, "total": total}
    except Exception as e:
        logger.error("Error fetching resolved persons: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review-queue")
def get_staging_review_queue(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns items flagged for human review (conflicts, low-confidence matches).
    """
    try:
        q = db.query(DiscoveryStaging).filter(DiscoveryStaging.processing_status == "review")
        total = q.count()
        records = q.order_by(DiscoveryStaging.created_at.desc()).offset(skip).limit(limit).all()

        items = []
        for r in records:
            # Check if there is an existing recruiter match for conflict comparison
            matched_recruiter = None
            if r.raw_name:
                matched = db.query(Recruiter).filter(
                    Recruiter.recruiter_name.ilike(f"%{r.raw_name.strip()}%")
                ).first()
                if matched:
                    matched_recruiter = {
                        "recruiter_id": matched.recruiter_id,
                        "recruiter_name": matched.recruiter_name,
                        "company_name": matched.company.company_name if matched.company else None,
                        "title": matched.title,
                        "email": matched.email,
                        "phone": matched.phone,
                        "linkedin": matched.linkedin,
                        "location": matched.location,
                    }

            items.append({
                "staging_id": r.id,
                "discovery_id": r.discovery_id,
                "raw_name": r.raw_name,
                "raw_title": r.raw_title,
                "raw_company": r.raw_company,
                "raw_email": r.raw_email,
                "raw_phone": r.raw_phone,
                "raw_linkedin": r.raw_linkedin,
                "raw_location": r.raw_location,
                "decision": r.decision,
                "decision_reason": r.decision_reason,
                "identity_confidence": r.identity_confidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "matched_master": matched_recruiter,
            })

        return {"items": items, "total": total}
    except Exception as e:
        logger.error("Error fetching staging review queue: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/{staging_id}/approve")
def approve_review_item(
    staging_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Admin approves a review-flagged staging record, forcing promotion to master DB.
    """
    stg = db.query(DiscoveryStaging).filter(DiscoveryStaging.id == staging_id).first()
    if not stg:
        raise HTTPException(status_code=404, detail="Staging record not found")

    processor = DiscoveryProcessor(db)
    person = processor._resolve_cluster([stg])
    match, conf = processor._match_master_db(person)

    # Force decision to NEW or ENRICH
    decision_type = 'ENRICH' if match else 'NEW'
    decision = {
        'person': person,
        'recruiter': match,
        'decision': decision_type,
        'reason': 'Manually approved by administrator',
    }
    stats = processor._execute_decisions([decision])
    stg.processing_status = 'committed'
    stg.decision = decision_type
    stg.processed_at = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True, "decision": decision_type, "stats": stats}


@router.post("/review/{staging_id}/reject")
def reject_review_item(
    staging_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Admin rejects a review-flagged staging record.
    """
    stg = db.query(DiscoveryStaging).filter(DiscoveryStaging.id == staging_id).first()
    if not stg:
        raise HTTPException(status_code=404, detail="Staging record not found")

    stg.processing_status = 'rejected'
    stg.decision = 'IGNORE'
    stg.decision_reason = 'Manually rejected by administrator'
    stg.processed_at = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True, "status": "rejected"}


@router.post("/process-now")
def trigger_batch_processing_now(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Forces immediate execution of the Discovery Batch Intelligence Processor.
    """
    stats = run_batch_processor(db, limit=limit)
    return {"ok": True, "stats": stats}


@router.get("/decision-distribution")
def get_decision_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns breakdown of decisions (NEW, ENRICH, DUPLICATE, REVIEW, CONFLICT, IGNORE) for analytics chart.
    """
    try:
        results = db.query(
            DiscoveryStaging.decision,
            sqlfunc.count(DiscoveryStaging.id)
        ).filter(DiscoveryStaging.decision != None).group_by(DiscoveryStaging.decision).all()

        distribution = [{"decision": d or "UNKNOWN", "count": count} for d, count in results]
        return {"distribution": distribution}
    except Exception as e:
        logger.error("Error fetching decision distribution: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
