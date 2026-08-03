from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Dict, Any

from ..database import get_db
from ..models.models import RecruiterEmail, DomainReputation, MailIntelTracking
from ..models.auth_models import User
from ..routes.auth import get_current_user_from_request
from pydantic import BaseModel

router = APIRouter()

class CleanupRequest(BaseModel):
    confidence_less_than: int = None
    hard_bounce_gte: int = None
    never_delivered: bool = False
    domain_does_not_exist: bool = False

@router.get("/stats")
def get_mailintel_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    # Total emails
    total = db.query(func.count(RecruiterEmail.id)).scalar()
    
    # Status breakdown
    verified = db.query(func.count(RecruiterEmail.id)).filter(RecruiterEmail.status == 'verified').scalar()
    likely = db.query(func.count(RecruiterEmail.id)).filter(RecruiterEmail.status == 'likely_valid').scalar()
    monitoring = db.query(func.count(RecruiterEmail.id)).filter(RecruiterEmail.status == 'needs_monitoring').scalar()
    suspicious = db.query(func.count(RecruiterEmail.id)).filter(RecruiterEmail.status == 'suspicious').scalar()
    invalid = db.query(func.count(RecruiterEmail.id)).filter(RecruiterEmail.status == 'invalid').scalar()
    never_checked = db.query(func.count(RecruiterEmail.id)).filter(RecruiterEmail.last_checked_at == None).scalar()
    never_used = db.query(func.count(RecruiterEmail.id)).outerjoin(MailIntelTracking).filter(
        MailIntelTracking.last_campaign_id == None
    ).scalar()
    
    # Recent activity
    recent_replied = db.query(func.count(MailIntelTracking.email_id)).filter(
        MailIntelTracking.last_reply_at != None
    ).scalar()
    recent_bounced = db.query(func.count(MailIntelTracking.email_id)).filter(
        MailIntelTracking.last_bounce_at != None
    ).scalar()
    
    avg_confidence = db.query(func.avg(RecruiterEmail.confidence_score)).scalar() or 0.0
    
    return {
        "total": total,
        "verified": verified,
        "likely_valid": likely,
        "needs_monitoring": monitoring,
        "suspicious": suspicious,
        "invalid": invalid,
        "never_checked": never_checked,
        "never_used": never_used,
        "recent_replied": recent_replied,
        "recent_bounced": recent_bounced,
        "average_confidence": round(avg_confidence, 1)
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
