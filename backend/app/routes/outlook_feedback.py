from fastapi import APIRouter, Depends, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from ..database import get_db
from ..models.outlook_feedback import OutlookFeedbackLog
from ..models.auth_models import User
from ..services.outlook_feedback_service import outlook_feedback_watcher

router = APIRouter(prefix="/outlook/feedback", tags=["Outlook Delivery Feedback"])

def get_optional_current_user(
    request: Request, 
    db: Session = Depends(get_db)
) -> Optional[User]:
    try:
        from ..services.auth_service import get_current_user_from_request
        return get_current_user_from_request(request, db)
    except Exception:
        return None

class SyncRequest(BaseModel):
    folders: Optional[List[str]] = None
    limit: Optional[int] = 100

@router.get("/status")
def get_feedback_status(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Returns the current synchronization status and stats of Outlook feedback listener."""
    total_bounces = db.query(OutlookFeedbackLog).filter(
        OutlookFeedbackLog.event_type.in_(["hard_bounce", "soft_bounce"])
    ).count()
    total_delivered = db.query(OutlookFeedbackLog).filter(
        OutlookFeedbackLog.event_type == "delivered"
    ).count()

    return {
        "status": "active" if outlook_feedback_watcher._running else "idle",
        "last_scan_time": outlook_feedback_watcher.last_scan_time,
        "last_stats": outlook_feedback_watcher.last_stats,
        "total_bounces_recorded": total_bounces,
        "total_delivered_recorded": total_delivered,
        "monitored_folders": ["Undilevered mail", "Psotmaster", "Inbox"]
    }

@router.post("/sync")
def trigger_sync(
    payload: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Triggers an immediate scan of Outlook feedback folders."""
    folders = payload.folders or ["Undilevered mail", "Psotmaster"]
    limit = min(payload.limit or 50, 1000)
    
    # Run scan asynchronously in background task to avoid client HTTP timeouts
    background_tasks.add_task(outlook_feedback_watcher.scan_folders, folder_names=folders, limit_per_folder=limit)
    return {
        "status": "started",
        "message": f"Scan initiated in background for {len(folders)} folders.",
        "folders": folders,
        "limit": limit
    }

@router.get("/bounces")
def list_bounces(
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Lists recent detected bounces from Outlook with diagnostic reasons."""
    q = db.query(OutlookFeedbackLog).filter(
        OutlookFeedbackLog.event_type.in_(["hard_bounce", "soft_bounce"])
    )
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            (OutlookFeedbackLog.recipient_email.ilike(s)) |
            (OutlookFeedbackLog.diagnostic_reason.ilike(s)) |
            (OutlookFeedbackLog.subject.ilike(s))
        )
    
    total = q.count()
    items = q.order_by(OutlookFeedbackLog.received_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": it.id,
                "recipient_email": it.recipient_email,
                "event_type": it.event_type,
                "smtp_code": it.smtp_code,
                "diagnostic_reason": it.diagnostic_reason,
                "folder_name": it.folder_name,
                "subject": it.subject,
                "campaign_id": it.campaign_id,
                "recruiter_id": it.recruiter_id,
                "received_at": it.received_at.isoformat() if it.received_at else None,
                "processed_at": it.processed_at.isoformat() if it.processed_at else None
            }
            for it in items
        ]
    }
