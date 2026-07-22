from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from .auth import get_db
from ..models.auth_models import User
from ..services.auth_service import create_access_token
import os

router = APIRouter()

@router.get("/impersonate/{email}")
def impersonate(email: str, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, first_name="Test", last_name="User")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    token = create_access_token({"sub": str(user.id)})
    
    res = RedirectResponse(url="http://localhost:5173/")
    res.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=3600,
        samesite="lax",
        secure=False
    )
    return res
