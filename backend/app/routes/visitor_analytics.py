from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional

from ..database import get_db
from ..models.models import VisitorSession, PageVisit, ActionLog
from ..services.auth_service import require_role
from ..routes.admin import cached_route

router = APIRouter()

@router.get("/overview")
@cached_route(ttl=60)
def visitor_overview(days: int = 30, db: Session = Depends(get_db), _ = Depends(require_role(['admin', 'superadmin']))):
    """KPIs for Overview Tab"""
    since = datetime.utcnow() - timedelta(days=days)
    today = datetime.utcnow().date()
    
    # Visitors Today
    visitors_today = db.query(func.count(VisitorSession.session_id)).filter(
        func.date(VisitorSession.started_at) == today
    ).scalar() or 0
    
    # Active Now (Active within last 10 minutes)
    active_cutoff = datetime.utcnow() - timedelta(minutes=10)
    active_now = db.query(func.count(VisitorSession.session_id)).filter(
        VisitorSession.ended_at >= active_cutoff
    ).scalar() or 0
    
    # Unique Users (with emails)
    unique_users = db.query(func.count(func.distinct(VisitorSession.user_email))).filter(
        VisitorSession.started_at >= since,
        VisitorSession.user_email.isnot(None)
    ).scalar() or 0
    
    # Returning Users (users with more than 1 session)
    returning_query = db.query(VisitorSession.user_email).filter(
        VisitorSession.started_at >= since,
        VisitorSession.user_email.isnot(None)
    ).group_by(VisitorSession.user_email).having(func.count(VisitorSession.session_id) > 1)
    returning_users = returning_query.count()
    
    # Total Sessions
    total_sessions = db.query(func.count(VisitorSession.session_id)).filter(
        VisitorSession.started_at >= since
    ).scalar() or 0
    
    # Averages
    avg_session_seconds = db.query(func.avg(VisitorSession.idle_time_seconds)).filter(
        VisitorSession.started_at >= since
    ).scalar() or 0
    
    avg_pages = db.query(func.avg(VisitorSession.total_page_views)).filter(
        VisitorSession.started_at >= since
    ).scalar() or 0
    
    # Bounce Rate (Sessions with exactly 1 page view)
    bounces = db.query(func.count(VisitorSession.session_id)).filter(
        VisitorSession.started_at >= since,
        VisitorSession.total_page_views == 1
    ).scalar() or 0
    bounce_rate = round((bounces / total_sessions * 100) if total_sessions > 0 else 0, 1)
    
    return {
        "visitors_today": visitors_today,
        "active_now": active_now,
        "unique_users": unique_users,
        "returning_users": returning_users,
        "total_sessions": total_sessions,
        "avg_session_duration_sec": round(avg_session_seconds),
        "avg_pages_per_session": round(avg_pages, 1),
        "bounce_rate": bounce_rate
    }

@router.get("/live")
def visitor_live(db: Session = Depends(get_db), _ = Depends(require_role(['admin', 'superadmin']))):
    """Live Visitors Tab (Active in last 10 mins)"""
    active_cutoff = datetime.utcnow() - timedelta(minutes=10)
    live_sessions = db.query(VisitorSession).filter(
        VisitorSession.last_activity >= active_cutoff
    ).order_by(VisitorSession.last_activity.desc()).limit(100).all()
    
    return [
        {
            "session_id": s.session_id,
            "user_email": s.user_email,
            "ip_address": s.ip_address,
            "city": s.city,
            "country": s.country,
            "browser": s.browser,
            "os": s.os,
            "device": s.device,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "last_activity": s.last_activity,
            "status": s.status,
            "current_page": s.current_page,
            "timezone": s.timezone,
            "screen_size": s.screen_size,
            "session_score": s.session_score or "Normal",
            "total_page_views": s.total_page_views,
            "duration": (s.last_activity - s.started_at).total_seconds() if s.last_activity and s.started_at else 0
        }
        for s in live_sessions
    ]

@router.get("/sessions")
def visitor_sessions(limit: int = 100, offset: int = 0, db: Session = Depends(get_db), _ = Depends(require_role(['admin', 'superadmin']))):
    """Paginated list of sessions for the Sessions Tab"""
    sessions = db.query(VisitorSession).order_by(VisitorSession.started_at.desc()).offset(offset).limit(limit).all()
    total = db.query(func.count(VisitorSession.session_id)).scalar()
    
    return {
        "items": [
            {
                "session_id": s.session_id,
                "user_email": s.user_email,
                "ip_address": s.ip_address,
                "city": s.city,
                "country": s.country,
                "browser": s.browser,
                "os": s.os,
                "device": s.device,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "total_page_views": s.total_page_views,
                "total_actions": s.total_actions,
                "total_errors": s.total_errors,
                "duration": (s.ended_at - s.started_at).total_seconds() if s.ended_at and s.started_at else 0
            }
            for s in sessions
        ],
        "total": total
    }

@router.get("/sessions/{session_id}")
def visitor_session_detail(session_id: str, db: Session = Depends(get_db), _ = Depends(require_role(['admin', 'superadmin']))):
    """Timeline and detailed profile for a specific session"""
    session = db.query(VisitorSession).filter(VisitorSession.session_id == session_id).first()
    if not session:
        return {"error": "Session not found"}
        
    visits = db.query(PageVisit).filter(PageVisit.session_id == session_id).order_by(PageVisit.visited_at.asc()).all()
    actions = db.query(ActionLog).filter(ActionLog.session_id == session_id).order_by(ActionLog.created_at.asc()).all()
    
    # Merge into a single timeline
    timeline = []
    for v in visits:
        timeline.append({
            "type": "page_view",
            "page": v.page,
            "path": v.path,
            "timestamp": v.visited_at
        })
    for a in actions:
        timeline.append({
            "type": "action",
            "action_type": a.action_type,
            "details": a.details,
            "status": a.status,
            "timestamp": a.created_at
        })
        
    timeline.sort(key=lambda x: x["timestamp"])
    
    return {
        "profile": {
            "session_id": session.session_id,
            "user_email": session.user_email,
            "ip_address": session.ip_address,
            "location": f"{session.city}, {session.country}",
            "system": f"{session.browser} on {session.os} ({session.device})",
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "idle_time_seconds": session.idle_time_seconds,
            "total_page_views": session.total_page_views,
            "total_actions": session.total_actions,
            "total_errors": session.total_errors
        },
        "timeline": timeline
    }
