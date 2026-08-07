from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Dict, Any

from ..database import get_db
from ..models.models import RecruiterEmail, DomainReputation, MailIntelTracking
from ..models.auth_models import User
from ..routes.auth import get_current_user_from_request
from pydantic import BaseModel

from ..services.email_verification_engine import verification_engine
from ..services.verification_state import verification_state

router = APIRouter()

class CleanupRequest(BaseModel):
    confidence_less_than: int = None
    hard_bounce_gte: int = None
    never_delivered: bool = False
    domain_does_not_exist: bool = False
from ..services.recruiter_store import recruiter_store

@router.get("/stats")
def get_mailintel_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    # Total emails and status breakdown from DuckDB
    recruiter_store._ensure_loaded()
    duck = recruiter_store._conn
    
    stats_row = duck.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE email_status = 'verified') as verified,
            COUNT(*) FILTER (WHERE email_status = 'likely_valid') as likely_valid,
            COUNT(*) FILTER (WHERE email_status = 'needs_monitoring') as needs_monitoring,
            COUNT(*) FILTER (WHERE email_status = 'suspicious') as suspicious,
            COUNT(*) FILTER (WHERE email_status = 'invalid') as invalid,
            COUNT(*) FILTER (WHERE email_status = 'likely_invalid') as likely_invalid,
            COUNT(*) FILTER (WHERE email_status IS NULL OR email_status = 'unknown' OR email_status = '') as never_checked,
            AVG(CAST(email_confidence AS DOUBLE)) as avg_confidence
        FROM recruiters
        WHERE email IS NOT NULL AND email != ''
    """).fetchone()
    
    # Recent activity from PostgreSQL tracking table
    recent_replied = db.query(func.count(MailIntelTracking.email_id)).filter(
        MailIntelTracking.last_reply_at != None
    ).scalar()
    recent_bounced = db.query(func.count(MailIntelTracking.email_id)).filter(
        MailIntelTracking.last_bounce_at != None
    ).scalar()
    
    return {
        "total": stats_row[0] or 0,
        "verified": stats_row[1] or 0,
        "likely_valid": stats_row[2] or 0,
        "needs_monitoring": stats_row[3] or 0,
        "suspicious": stats_row[4] or 0,
        "invalid": (stats_row[5] or 0) + (stats_row[6] or 0),
        "never_checked": stats_row[7] or 0,
        "never_used": 0, # Deprecated
        "recent_replied": recent_replied,
        "recent_bounced": recent_bounced,
        "average_confidence": round(stats_row[8] or 0.0, 1)
    }

@router.get("/domains")
def get_domain_reputation(
    limit: int = 50,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user_from_request)
):
    domains = db.query(DomainReputation).order_by(DomainReputation.total_sent.desc()).limit(limit).all()
    
    results = []
    for d in domains:
        success_rate = (d.total_delivered / d.total_sent * 100) if d.total_sent > 0 else 0
        bounce_rate = (d.total_bounced / d.total_sent * 100) if d.total_sent > 0 else 0
        reply_rate = (d.total_replied / d.total_sent * 100) if d.total_sent > 0 else 0
        
        results.append({
            "domain": d.domain,
            "total_sent": d.total_sent,
            "success_rate": round(success_rate, 1),
            "bounce_rate": round(bounce_rate, 1),
            "reply_rate": round(reply_rate, 1),
            "reputation_score": float(d.reputation_score)
        })
    
    return results

@router.post("/cleanup")
def run_bulk_cleanup(
    payload: CleanupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    query = db.query(RecruiterEmail).outerjoin(MailIntelTracking)
    
    if payload.confidence_less_than is not None:
        query = query.filter(RecruiterEmail.confidence_score < payload.confidence_less_than)
        
    if payload.hard_bounce_gte is not None:
        query = query.filter(MailIntelTracking.hard_bounce_count >= payload.hard_bounce_gte)
        
    if payload.never_delivered:
        query = query.filter(MailIntelTracking.last_delivery_at == None)
        
    count = query.count()
    
    # In a real scenario, this would queue a celery job to clean them up or archive them.
    # For now, we will flag them as invalid.
    emails = query.all()
    for e in emails:
        e.status = 'invalid'
        if e.mailintel:
            e.mailintel.flag_reason = 'Bulk Cleanup Job'
            
    db.commit()
    return {"cleaned_count": count, "message": f"Cleaned {count} emails."}

@router.get("/verification-progress")
def get_verification_progress(current_user: User = Depends(get_current_user_from_request)):
    return verification_engine.get_status()

@router.post("/start-verification")
def start_verification(current_user: User = Depends(get_current_user_from_request)):
    verification_engine.start()
    return {"message": "Verification engine started."}

@router.post("/pause-verification")
def pause_verification(current_user: User = Depends(get_current_user_from_request)):
    verification_engine.pause()
    return {"message": "Verification engine paused."}

@router.get("/verification-log")
def get_verification_log(current_user: User = Depends(get_current_user_from_request)):
    state = verification_engine.get_status()
    return {
        "errors": state.get("errors", []),
        "batch_log": state.get("batch_log", [])
    }

