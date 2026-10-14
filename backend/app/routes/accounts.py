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
        last_verified_at=datetime.now(timezone.utc)
    )
    db.add(account)
    db.flush()
    # Promote to default if no default sender or if current default is missing/shadow alias
    if not current_user.default_sender_id:
        current_user.default_sender_id = account.account_id
    else:
        curr_def = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == current_user.default_sender_id).first()
        if not curr_def or curr_def.email_address.lower().startswith("outlook_"):
            current_user.default_sender_id = account.account_id
    db.commit()
    db.refresh(account)
    return {"status": "success", "account_id": account.account_id}

@router.get("")
@router.get("/")
def list_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    accounts = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.user_id == current_user.id).all()
    user_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip()
    res = []
    for acc in accounts:
        email_str = acc.email_address or ""
        is_shadow = email_str.lower().startswith("outlook_")
        effective_display_name = acc.display_name or (user_name if user_name else None) or email_str.split("@")[0].replace(".", " ").title()
        res.append({
            "account_id": acc.account_id,
            "provider": acc.provider,
            "email_address": acc.email_address,
            "display_name": effective_display_name,
            "status": acc.status,
            "health_status": acc.health_status,
            "last_verified_at": acc.last_verified_at.isoformat() if acc.last_verified_at else None,
            "is_default": current_user.default_sender_id == acc.account_id,
            "is_shadow_alias": is_shadow
        })
    return {"items": res}

class UpdateAccountRequest(BaseModel):
    display_name: Optional[str] = None

@router.put("/{account_id}")
def update_account(account_id: int, req: UpdateAccountRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == account_id, ConnectedEmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if req.display_name is not None:
        account.display_name = req.display_name.strip() or None
    db.commit()
    return {"status": "success", "display_name": account.display_name}

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
    elif account.provider in ("microsoft", "outlook"):
        if account.access_token and account.access_token != "local_outlook_com":
            # Check token via graph api
            import requests
            headers = {"Authorization": f"Bearer {account.access_token}"}
            try:
                r = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=5)
                if r.ok:
                    account.health_status = "healthy"
                    account.status = "connected"
                else:
                    from ..services.send_engine import _refresh_msal_token
                    new_token = _refresh_msal_token(account)
                    if new_token:
                        account.health_status = "healthy"
                        account.status = "connected"
                    else:
                        account.health_status = "error"
                        account.status = "expired"
            except Exception:
                account.health_status = "error"
                account.status = "disconnected"
        else:
            # Check local Outlook COM
            try:
                import pythoncom, win32com.client
                pythoncom.CoInitialize()
                try:
                    outlook = win32com.client.Dispatch("Outlook.Application")
                    ns = outlook.GetNamespace("MAPI")
                    found = False
                    for i in range(1, ns.Accounts.Count + 1):
                        acc = ns.Accounts.Item(i)
                        if acc.SmtpAddress and acc.SmtpAddress.lower() == account.email_address.lower():
                            found = True
                            break
                    if found:
                        account.health_status = "healthy"
                        account.status = "connected"
                    else:
                        account.health_status = "error"
                        account.status = "disconnected"
                finally:
                    pythoncom.CoUninitialize()
            except Exception:
                account.health_status = "error"
                account.status = "disconnected"
    elif account.provider == "google":
        import requests
        headers = {"Authorization": f"Bearer {account.access_token}"}
        try:
            r = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers, timeout=5)
            if r.ok:
                account.health_status = "healthy"
                account.status = "connected"
            else:
                from ..services.send_engine import _refresh_google_token
                new_token = _refresh_google_token(account)
                if new_token:
                    account.health_status = "healthy"
                    account.status = "connected"
                else:
                    account.health_status = "error"
                    account.status = "expired"
        except Exception:
            account.health_status = "error"
            account.status = "disconnected"
    else:
        account.health_status = "healthy"
        account.status = "connected"
        
    account.last_verified_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"status": "success", "health_status": account.health_status}

@router.post("/connect-local-outlook")
def connect_local_outlook(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Automatically detect and connect the local desktop Outlook profile."""
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        raise HTTPException(status_code=500, detail="pywin32 not installed on server host")

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        ns = outlook.GetNamespace("MAPI")
        if ns.Accounts.Count == 0:
            raise HTTPException(status_code=400, detail="No Outlook accounts configured in local Microsoft Outlook")

        # Pick primary account (prefer technovion or first account)
        primary_acc = None
        for i in range(1, ns.Accounts.Count + 1):
            acc = ns.Accounts.Item(i)
            addr = getattr(acc, "SmtpAddress", "") or ""
            if "technovion" in addr.lower():
                primary_acc = acc
                break
        if not primary_acc:
            primary_acc = ns.Accounts.Item(1)

        email_addr = getattr(primary_acc, "SmtpAddress", "") or getattr(primary_acc, "DisplayName", "")
        display_name = getattr(primary_acc, "DisplayName", "") or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or email_addr.split("@")[0].title()

        account = db.query(ConnectedEmailAccount).filter(
            ConnectedEmailAccount.user_id == current_user.id,
            ConnectedEmailAccount.email_address == email_addr
        ).first()

        if not account:
            account = ConnectedEmailAccount(
                user_id=current_user.id,
                provider="microsoft",
                email_address=email_addr,
                display_name=display_name,
                access_token="local_outlook_com",
                status="connected",
                health_status="healthy",
                last_verified_at=datetime.now(timezone.utc)
            )
            db.add(account)
        else:
            account.status = "connected"
            account.health_status = "healthy"
            account.access_token = "local_outlook_com"
            account.display_name = display_name
            account.last_verified_at = datetime.now(timezone.utc)

        db.flush()
        # Always promote as default sender
        current_user.default_sender_id = account.account_id
        db.commit()
        db.refresh(account)

        return {
            "status": "success",
            "account_id": account.account_id,
            "email_address": account.email_address,
            "display_name": account.display_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect local Outlook: {str(e)}")
    finally:
        pythoncom.CoUninitialize()

class TestSendRequest(BaseModel):
    to_email: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    subject: Optional[str] = "TalentOps Test Verification Email"
    body: Optional[str] = "<p>This is a live test email sent from TalentOps AI to verify genuine sender delivery.</p>"

@router.post("/{account_id}/test-send")
async def send_test_email(account_id: int, req: TestSendRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Send an immediate real test email through the specified connected account to verify clean sender headers and CC support."""
    from ..services.send_engine import _send_email_via_provider
    account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == account_id, ConnectedEmailAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    payload = {
        "campaign_id": 0,
        "from_email": account.email_address,
        "to_email": req.to_email,
        "cc": req.cc,
        "bcc": req.bcc,
        "subject": req.subject or "TalentOps Test Verification Email",
        "html_body": req.body or "<p>This is a live test email sent from TalentOps AI to verify genuine sender delivery.</p>"
    }
    success, error, err_type = await _send_email_via_provider(account_id, current_user.id, payload)
    if not success:
        raise HTTPException(status_code=400, detail=f"Send failed: {error}")
    return {
        "status": "success",
        "message": f"Test email sent successfully from {account.email_address} to {req.to_email}",
        "cc": req.cc,
        "bcc": req.bcc
    }

class QuickSendRequest(BaseModel):
    account_id: Optional[int] = None
    to_email: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    subject: str
    body: str

@router.post("/quick-send")
async def quick_send_email(req: QuickSendRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Quick direct email dispatch with CC/BCC support via connected email account (e.g. from Outlook overlay or recruiter directory)."""
    from ..services.send_engine import _send_email_via_provider
    account = None
    if req.account_id:
        account = db.query(ConnectedEmailAccount).filter(
            ConnectedEmailAccount.account_id == req.account_id,
            ConnectedEmailAccount.user_id == current_user.id
        ).first()
    if not account and current_user.default_sender_id:
        account = db.query(ConnectedEmailAccount).filter(
            ConnectedEmailAccount.account_id == current_user.default_sender_id,
            ConnectedEmailAccount.user_id == current_user.id
        ).first()
    if not account:
        account = db.query(ConnectedEmailAccount).filter(
            ConnectedEmailAccount.user_id == current_user.id,
            ConnectedEmailAccount.status == "connected"
        ).first()
    if not account:
        raise HTTPException(status_code=400, detail="No connected sending account available. Connect your Outlook or Gmail in Settings.")

    payload = {
        "campaign_id": 0,
        "from_email": account.email_address,
        "to_email": req.to_email,
        "cc": req.cc,
        "bcc": req.bcc,
        "subject": req.subject,
        "html_body": req.body
    }
    success, error, err_type = await _send_email_via_provider(account.account_id, current_user.id, payload)
    if not success:
        raise HTTPException(status_code=400, detail=f"Send failed: {error}")
    return {
        "status": "success",
        "message": f"Email sent successfully from {account.email_address} to {req.to_email}",
        "from_email": account.email_address,
        "to_email": req.to_email,
        "cc": req.cc,
        "bcc": req.bcc
    }
