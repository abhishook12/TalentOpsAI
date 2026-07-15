from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from user_agents import parse
from ..database import get_db
from ..models.models import VisitorSession

router = APIRouter()

class SessionStartPayload(BaseModel):
    anonymous_id: str
    session_id: str
    user_email: Optional[str] = None
    screen_size: Optional[str] = None
    timezone: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    current_page: Optional[str] = None

@router.post("/start")
def start_session(payload: SessionStartPayload, request: Request, db: Session = Depends(get_db)):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host
    
    browser, os, device = "Unknown", "Unknown", "Unknown"
    ua = payload.user_agent or request.headers.get("user-agent", "")
    if ua:
        try:
            parsed = parse(ua)
            browser = f"{parsed.browser.family} {parsed.browser.version_string}".strip()
            os = f"{parsed.os.family} {parsed.os.version_string}".strip()
            device = parsed.device.family
        except Exception:
            pass

    session = db.query(VisitorSession).filter(VisitorSession.session_id == payload.session_id).first()
    if not session:
        session = VisitorSession(
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_email=payload.user_email,
            ip_address=ip,
            browser=browser,
            os=os,
            device=device,
            screen_size=payload.screen_size,
            timezone=payload.timezone,
            referrer=payload.referrer,
            user_agent=ua,
            current_page=payload.current_page,
            status="Active"
        )
        db.add(session)
    else:
        session.status = "Active"
        session.last_activity = datetime.utcnow()
        if payload.user_email:
            session.user_email = payload.user_email
            
    db.commit()
    return {"ok": True}

class SessionEventPayload(BaseModel):
    anonymous_id: str
    session_id: str
    event_type: str
    current_page: Optional[str] = None
    previous_page: Optional[str] = None
    user_email: Optional[str] = None

@router.post("/event")
def log_event(payload: SessionEventPayload, db: Session = Depends(get_db)):
    session = db.query(VisitorSession).filter(VisitorSession.session_id == payload.session_id).first()
    if not session:
        return {"ok": False, "error": "session not found"}
        
    session.last_activity = datetime.utcnow()
    
    if payload.event_type == "page_view":
        session.total_page_views = (session.total_page_views or 0) + 1
        session.current_page = payload.current_page
        session.previous_page = payload.previous_page
        session.status = "Active"
    elif payload.event_type == "idle":
        session.status = "Idle"
    elif payload.event_type == "active":
        session.status = "Active"
        
    if payload.user_email:
        session.user_email = payload.user_email
        
    db.commit()
    return {"ok": True}

class SessionHeartbeatPayload(BaseModel):
    anonymous_id: str
    session_id: str
    status: str
    clicks_since_last: int = 0
    current_page: Optional[str] = None
    user_email: Optional[str] = None

@router.post("/heartbeat")
def heartbeat(payload: SessionHeartbeatPayload, db: Session = Depends(get_db)):
    session = db.query(VisitorSession).filter(VisitorSession.session_id == payload.session_id).first()
    if not session:
        return {"ok": False, "error": "session not found"}
        
    session.last_activity = datetime.utcnow()
    session.status = payload.status
    if payload.clicks_since_last > 0:
        session.total_clicks = (session.total_clicks or 0) + payload.clicks_since_last
    if payload.current_page:
        session.current_page = payload.current_page
    if payload.user_email:
        session.user_email = payload.user_email
        
    # Calculate idle time difference
    if payload.status == "Active":
        # We assume heartbeat is every 30s
        duration = (datetime.utcnow() - session.started_at).total_seconds()
        # Keep ended_at moving forward
        session.ended_at = datetime.utcnow()
        
    db.commit()
    return {"ok": True}

class SessionEndPayload(BaseModel):
    session_id: str

@router.post("/end")
def end_session(payload: SessionEndPayload, db: Session = Depends(get_db)):
    session = db.query(VisitorSession).filter(VisitorSession.session_id == payload.session_id).first()
    if session:
        session.status = "Ended"
        session.ended_at = datetime.utcnow()
        db.commit()
    return {"ok": True}
