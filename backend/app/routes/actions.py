from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
import json

from ..database import get_db
from ..models.models import ActionLog

router = APIRouter()


class ActionLogPayload(BaseModel):
    action_type: str
    details: Optional[Dict[str, Any]] = None
    status: str = "success"


@router.post("/log")
def log_action(payload: ActionLogPayload, request: Request, db: Session = Depends(get_db)):
    action_type = (payload.action_type or "").strip()
    if not action_type or len(action_type) > 100:
        raise HTTPException(status_code=400, detail="Invalid action_type")
    if payload.status not in ("success", "failed", "warning"):
        raise HTTPException(status_code=400, detail="Invalid status")

    user_email = request.headers.get("X-User-Email", "Anonymous")
    session_id = request.headers.get("X-Session-ID")
    ip_address = request.client.host if request.client else None

    details_json = None
    if payload.details is not None:
        try:
            details_json = json.dumps(payload.details)[:5000]
        except Exception:
            raise HTTPException(status_code=400, detail="details must be JSON-serializable")

    db.add(
        ActionLog(
            user_email=user_email,
            session_id=session_id,
            action_type=action_type,
            details=details_json,
            status=payload.status,
            ip_address=ip_address,
        )
    )
    db.commit()
    return {"ok": True}

