from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json

from app.database import get_db
from app.models.models import Recruiter
from app.models.sentinel_state import SentinelState
from app.models.sentinel_audit import SentinelAuditLog
from app.routes.auth import get_current_user_from_request
from app.models.auth_models import User

router = APIRouter(prefix="/sentinel", tags=["sentinel"])

@router.get("/health")
def get_sentinel_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    # Overall Quality Score
    avg_score = db.query(func.avg(Recruiter.quality_score)).scalar() or 0
    
    # Missing Fields Count (using simple approximation by looking at the json)
    # A more robust way is querying the actual columns since missing_fields is JSON
    total_recruiters = db.query(func.count(Recruiter.recruiter_id)).scalar() or 0
    
    missing_emails = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.email.like('%missing.local%')).scalar() or 0
    missing_phones = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.phone == None) | (Recruiter.phone == '')).scalar() or 0
    missing_linkedin = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.linkedin == None) | (Recruiter.linkedin == '')).scalar() or 0
    missing_location = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.location == None) | (Recruiter.location == '')).scalar() or 0
    missing_company = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.company_id == None).scalar() or 0
    
    return {
        "overall_quality_score": round(avg_score, 1),
        "total_profiles": total_recruiters,
        "missing_breakdown": {
            "email": missing_emails,
            "phone": missing_phones,
            "linkedin": missing_linkedin,
            "location": missing_location,
            "company": missing_company
        }
    }

@router.get("/queue")
def get_sentinel_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    state = db.query(SentinelState).first()
    if not state:
        return {"status": "Idle", "profiles_analyzed": 0, "profiles_repaired": 0, "total_profiles": 0, "current_task_description": "Engine not initialized"}
        
    total = db.query(func.count(Recruiter.recruiter_id)).scalar() or 0
    
    return {
        "status": state.status,
        "total_profiles": total,
        "profiles_analyzed": state.profiles_analyzed,
        "profiles_repaired": state.profiles_repaired,
        "current_task_description": state.current_task_description,
        "last_processed_id": state.last_processed_id,
        "updated_at": state.updated_at
    }

@router.get("/audit")
def get_sentinel_audit(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    logs = db.query(SentinelAuditLog, Recruiter.recruiter_name)\
        .join(Recruiter, SentinelAuditLog.recruiter_id == Recruiter.recruiter_id)\
        .order_by(SentinelAuditLog.timestamp.desc())\
        .limit(limit).all()
        
    return [
        {
            "id": log.SentinelAuditLog.id,
            "recruiter_id": log.SentinelAuditLog.recruiter_id,
            "recruiter_name": log.recruiter_name,
            "field_changed": log.SentinelAuditLog.field_changed,
            "previous_value": log.SentinelAuditLog.previous_value,
            "new_value": log.SentinelAuditLog.new_value,
            "reason": log.SentinelAuditLog.reason,
            "timestamp": log.SentinelAuditLog.timestamp
        }
        for log in logs
    ]

@router.post("/toggle")
def toggle_sentinel(
    action: str = Query(..., description="start or stop"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    state = db.query(SentinelState).first()
    if not state:
        state = SentinelState(status="Idle")
        db.add(state)
    
    if action == "start":
        state.status = "Running"
    elif action == "stop":
        state.status = "Paused"
    
    db.commit()
    return {"status": state.status}
