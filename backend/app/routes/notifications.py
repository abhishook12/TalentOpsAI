from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from ..database import get_db
from ..models.models import Notification
from ..services.auth_service import get_current_user_from_request as get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/")
def get_notifications(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(Notification).filter(
        (Notification.user_id == current_user.id) | (Notification.user_id == None)
    ).order_by(desc(Notification.created_at)).limit(50).all()

@router.post("/read")
def mark_all_read(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db.query(Notification).filter(
        ((Notification.user_id == current_user.id) | (Notification.user_id == None)) & (Notification.read == False)
    ).update({"read": True}, synchronize_session=False)
    db.commit()
    return {"status": "success"}

@router.post("/test")
def create_test_notification(db: Session = Depends(get_db)):
    n = Notification(
        title="Welcome to TalentOps AI",
        message="System fully updated to Enterprise Polish Sprint v1.3",
        type="success"
    )
    db.add(n)
    db.commit()
    return {"status": "success"}
