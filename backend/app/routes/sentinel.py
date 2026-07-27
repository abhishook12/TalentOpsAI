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

import time
from sqlalchemy import text

_health_cache = {"data": None, "expires": 0}

@router.get("/health")
def get_sentinel_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    now = time.time()
    if _health_cache["data"] and now < _health_cache["expires"]:
        return _health_cache["data"]
        
    try:
        row = db.execute(text("""
            SELECT 
                AVG(quality_score) as avg_score,
                COUNT(*) as total,
                SUM(CASE WHEN email LIKE '%missing.local%' THEN 1 ELSE 0 END) as m_email,
                SUM(CASE WHEN phone IS NULL OR phone = '' THEN 1 ELSE 0 END) as m_phone,
                SUM(CASE WHEN linkedin IS NULL OR linkedin = '' THEN 1 ELSE 0 END) as m_linkedin,
                SUM(CASE WHEN location IS NULL OR location = '' THEN 1 ELSE 0 END) as m_location,
                SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END) as m_company
            FROM recruiters
        """)).mappings().one()
        
        result = {
            "overall_quality_score": round(row["avg_score"] or 0, 1),
            "total_profiles": row["total"] or 0,
            "missing_breakdown": {
                "email": row["m_email"] or 0,
                "phone": row["m_phone"] or 0,
                "linkedin": row["m_linkedin"] or 0,
                "location": row["m_location"] or 0,
                "company": row["m_company"] or 0
            }
        }
        
        _health_cache["data"] = result
        _health_cache["expires"] = now + 60
        return result
    except Exception:
        db.rollback()
        return {
            "overall_quality_score": 0,
            "total_profiles": 0,
            "missing_breakdown": {"email": 0, "phone": 0, "linkedin": 0, "location": 0, "company": 0}
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
