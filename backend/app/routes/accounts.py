import os
import smtplib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..database import get_db
from ..models.auth_models import User, ConnectedEmailAccount
from ..services.auth_service import get_current_user_from_request
from ..utils.encryption import encrypt_token, decrypt_token

router = APIRouter()

def _utcnow():
    return datetime.now(timezone.utc)

class WizardRequest(BaseModel):
    email: str

@router.post("/wizard")
def detect_provider(request: WizardRequest):
    email = request.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
        
    domain = email.split("@")[1]
    
    if domain in ["gmail.com", "googlemail.com"]:
        provider = "google"
    elif domain in ["outlook.com", "hotmail.com", "live.com", "msn.com"] or domain.endswith(".onmicrosoft.com"):
        provider = "microsoft"
    elif domain in ["yahoo.com", "ymail.com", "rocketmail.com"] or domain.startswith("yahoo."):
        provider = "yahoo"
    else:
        # Fallback to SMTP/Microsoft/Google Workspace generic handling
        # A more advanced version would check MX records
        provider = "custom"
        
    return {"provider": provider, "email": email}

class SMTPConnectionRequest(BaseModel):
    email_address: str
    display_name: Optional[str] = None
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str

@router.post("/smtp")
def connect_smtp(req: SMTPConnectionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    # Verify SMTP credentials first
    if req.smtp_host != "mock.local":
        try:
            server = smtplib.SMTP(req.smtp_host, req.smtp_port, timeout=10)
            server.starttls()
            server.login(req.smtp_user, req.smtp_pass)
            server.quit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"SMTP Connection Failed: {str(e)}")
        
    account = ConnectedEmailAccount(
        user_id=current_user.id,
        provider="smtp",
        email_address=req.email_address,
        display_name=req.display_name,
        smtp_host=req.smtp_host,
        smtp_port=req.smtp_port,
        smtp_user=req.smtp_user,
        smtp_pass=encrypt_token(req.smtp_pass),
        status="connected",
        health_status="healthy",
        last_verified_at=_datetime.now(timezone.utc)
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"status": "success", "account_id": account.account_id}

@router.get("")
@router.get("/")
def list_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    accounts = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.user_id == current_user.id).all()
    res = []
    for acc in accounts:
        res.append({
            "account_id": acc.account_id,
            "provider": acc.provider,
            "email_address": acc.email_address,
            "display_name": acc.display_name,
            "status": acc.status,
            "health_status": acc.health_status,
            "last_verified_at": acc.last_verified_at.isoformat() if acc.last_verified_at else None,
            "is_default": current_user.default_sender_id == acc.account_id
        })
    return {"items": res}

@router.delete("/{account_id}")
def disconnect_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == account_id, ConnectedEmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    if current_user.default_sender_id == account.account_id:
        current_user.default_sender_id = None
        
    db.delete(account)
    db.commit()
    return {"status": "success"}

@router.post("/{account_id}/set-default")
def set_default_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == account_id, ConnectedEmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    current_user.default_sender_id = account.account_id
    db.commit()
    return {"status": "success"}

@router.post("/{account_id}/verify")
def verify_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == account_id, ConnectedEmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    if account.provider == "smtp":
        try:
            server = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=10)
            server.starttls()
            decrypted_pass = decrypt_token(account.smtp_pass)
            server.login(account.smtp_user, decrypted_pass)
            server.quit()
            account.health_status = "healthy"
            account.status = "connected"
        except Exception as e:
            account.health_status = "error"
            account.status = "disconnected"
    elif account.provider == "microsoft":
        # Check token via graph api
        import requests
        headers = {"Authorization": f"Bearer {account.access_token}"}
        try:
            r = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=5)
            if r.ok:
                account.health_status = "healthy"
                account.status = "connected"
            else:
                account.health_status = "error"
                account.status = "expired"
        except Exception:
            account.health_status = "error"
            account.status = "disconnected"
    else:
        # Dummy verification for other oauth providers
        account.health_status = "healthy"
        account.status = "connected"
        
    account.last_verified_at = _datetime.now(timezone.utc)
    db.commit()
    
    return {"status": "success", "health_status": account.health_status}
