from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models.models import Notification
from ..models.auth_models import User
from ..services.auth_service import (
    get_current_user_from_request as get_current_user,
    get_optional_current_user,
    require_admin
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "info"  # info, success, warning, error, update
    user_id: Optional[int] = None


@router.get("/")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Returns notifications:
    - If user is authenticated: User's personal notifications + Global broadcasts (user_id IS NULL)
    - If user is unauthenticated / Desktop Scout telemetry: Global broadcasts only
    """
    if current_user:
        query = db.query(Notification).filter(
            (Notification.user_id == current_user.id) | (Notification.user_id == None)
        )
    else:
        query = db.query(Notification).filter(Notification.user_id == None)

    return query.order_by(desc(Notification.created_at)).limit(50).all()


@router.post("/")
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Admin dispatches a general notification or global fleet broadcast.
    If user_id is None, it broadcasts to all users and desktop scout nodes.
    """
    n = Notification(
        title=payload.title,
        message=payload.message,
        type=payload.type,
        user_id=payload.user_id,
        read=False
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return {
        "status": "success",
        "notification": {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "user_id": n.user_id,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
    }


@router.post("/read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    if current_user:
        db.query(Notification).filter(
            ((Notification.user_id == current_user.id) | (Notification.user_id == None)) & (Notification.read == False)
        ).update({"read": True}, synchronize_session=False)
    else:
        db.query(Notification).filter(
            (Notification.user_id == None) & (Notification.read == False)
        ).update({"read": True}, synchronize_session=False)
    db.commit()
    return {"status": "success"}


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    query = db.query(Notification).filter(Notification.id == notification_id)
    if current_user:
        query = query.filter((Notification.user_id == current_user.id) | (Notification.user_id == None))
    else:
        query = query.filter(Notification.user_id == None)
    
    n = query.first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read = True
    db.commit()
    return {"status": "success", "id": notification_id}


@router.post("/test")
def create_test_notification(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    n = Notification(
        title="Welcome to TalentOps AI",
        message="System fully updated to Enterprise Polish Sprint v1.3",
        type="success"
    )
    db.add(n)
    db.commit()
    return {"status": "success"}
